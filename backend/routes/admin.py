"""Admin Routes: Import/Export, User Management, Bulk Operations, Stats"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, Response, Request
from typing import Optional
import uuid, json, re as _re, io, base64 as _b64, os as _os, asyncio, httpx
from datetime import datetime, timezone

from database import db, logger
from models import BulkCityUpdate, BulkDeleteRequest
from auth import get_current_user, get_admin_user

router = APIRouter(prefix="/api", tags=["admin"])


@router.post("/admin/import-questions")
async def import_questions(file: UploadFile, user: dict = Depends(get_current_user)):
    """Import questions from a JSON file"""
    if not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin only")
    if not file.filename.endswith('.json'):
        raise HTTPException(status_code=400, detail="Nur JSON-Dateien sind erlaubt")
    try:
        content = await file.read()
        raw_text = content.decode('utf-8-sig')
        try:
            questions = json.loads(raw_text)
        except json.JSONDecodeError:
            fixed = _re.sub(r'\u201E([^"\u201E]*)"', r'\1', raw_text)
            fixed = _re.sub(r'\\([^"\\\/bfnrtu])', r'\1', fixed)
            fixed = fixed.replace('\u201c', '').replace('\u201d', '')
            try:
                questions = json.loads(fixed)
                logger.info("JSON fixed and parsed successfully")
            except json.JSONDecodeError as e2:
                raise HTTPException(status_code=400, detail=f"Ungültige JSON-Datei (Zeile {e2.lineno}): {e2.msg}")
        if not isinstance(questions, list):
            raise HTTPException(status_code=400, detail="JSON muss eine Liste von Fragen sein")
        if len(questions) == 0:
            raise HTTPException(status_code=400, detail="Keine Fragen in der Datei")

        imported = 0
        skipped = 0
        errors = []
        existing_ids = set()
        async for q in db.questions.find({}, {"id": 1, "_id": 0}):
            existing_ids.add(q.get("id"))
        batch = []
        for i, q in enumerate(questions):
            question_text_de = q.get("question_text_de", q.get("question", q.get("frage", q.get("text", ""))))
            raw_choices = q.get("choices_de", q.get("choices", q.get("antworten", [])))
            correct_answers = q.get("correct_answers", q.get("correct", q.get("richtig", [])))
            explanation_de = q.get("explanation_de", q.get("explanation", q.get("erklärung", "")))
            unified_choices = []
            for c in raw_choices:
                cid = c.get("id", str(uuid.uuid4())[:8])
                text = c.get("text_de") or c.get("text", "")
                is_correct = c.get("is_correct", cid in correct_answers)
                unified_choices.append({"id": cid, "text": text, "text_de": text, "is_correct": is_correct})
            normalized = {
                "id": q.get("id", str(uuid.uuid4())),
                "specialty_id": q.get("specialty_id", q.get("fach", q.get("specialty", ""))).lower().strip(),
                "question_text": question_text_de, "question_text_de": question_text_de,
                "question_type": q.get("question_type", "mcq"),
                "choices": unified_choices, "explanation": explanation_de, "explanation_de": explanation_de,
                "year": q.get("year", q.get("jahr", 2024)),
                "exam_location": q.get("exam_location", q.get("ort", "vienna")),
                "country": q.get("country", None),
                "image_base64": q.get("image_base64", q.get("image", None)),
                "interactive_data": q.get("interactive_data", None),
                "tags": q.get("tags", []),
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            if not normalized["question_text_de"]:
                errors.append(f"Frage {i+1}: Kein Fragetext")
                skipped += 1
                continue
            if normalized["id"] in existing_ids:
                skipped += 1
                continue
            existing_ids.add(normalized["id"])
            if not normalized["image_base64"]:
                del normalized["image_base64"]
            if not normalized["interactive_data"]:
                del normalized["interactive_data"]
            batch.append(normalized)
            if len(batch) >= 100:
                await db.questions.insert_many(batch)
                imported += len(batch)
                batch = []
        if batch:
            await db.questions.insert_many(batch)
            imported += len(batch)
        spec_counts = {}
        for q in questions:
            sid = q.get("specialty_id", q.get("fach", q.get("specialty", "unknown"))).lower().strip()
            spec_counts[sid] = spec_counts.get(sid, 0) + 1
        total = await db.questions.count_documents({})
        return {"imported": imported, "skipped": skipped, "errors": errors[:10], "total_in_db": total, "by_specialty": spec_counts}
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Ungültige JSON-Datei")
    except Exception as e:
        logger.error(f"Import error: {e}")
        raise HTTPException(status_code=500, detail=f"Import fehlgeschlagen: {str(e)}")


@router.post("/admin/import-questions/xlsx")
async def import_questions_xlsx(file: UploadFile, user: dict = Depends(get_current_user)):
    """Import questions from an XLSX/Excel file"""
    if not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin only")
    if not (file.filename.endswith('.xlsx') or file.filename.endswith('.xls')):
        raise HTTPException(status_code=400, detail="Nur Excel-Dateien (.xlsx/.xls) sind erlaubt")
    try:
        content = await file.read()
        import openpyxl
        wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
        wb.close()
        if len(rows) < 2:
            raise HTTPException(status_code=400, detail="Excel-Datei muss eine Kopfzeile und mindestens eine Frage enthalten")
        headers = [str(h).lower().strip() if h else "" for h in rows[0]]

        def col(name_de, name_en):
            for i, h in enumerate(headers):
                if h == name_de.lower().strip() or h == name_en.lower().strip():
                    return i
            return None

        idx_text = col("Fragetext", "Question Text") or col("Frage", "Question") or col("Text", "text")
        idx_spec = col("Fachgebiet", "Specialty") or col("Fach", "subject") or col("specialty_id", "specialty_id")
        idx_a = col("Antwort A", "Answer A") or col("A", "a")
        idx_b = col("Antwort B", "Answer B") or col("B", "b")
        idx_c = col("Antwort C", "Answer C") or col("C", "c")
        idx_d = col("Antwort D", "Answer D") or col("D", "d")
        idx_e = col("Antwort E", "Answer E") or col("E", "e")
        idx_correct = col("Richtige Antwort", "Correct Answer") or col("Richtig", "correct") or col("correct", "correct")
        idx_explanation = col("Erklärung", "Explanation") or col("Erklaerung", "explanation")
        idx_year = col("Jahr", "Year") or col("year", "year")
        idx_location = col("Ort", "Location") or col("Stadt", "City") or col("exam_location", "exam_location")
        idx_country = col("Land", "Country") or col("country", "country")

        if idx_text is None:
            raise HTTPException(status_code=400, detail="Keine Spalte 'Fragetext' oder 'Frage' gefunden. Kopfzeile: " + ", ".join(headers[:10]))

        imported = 0
        skipped = 0
        errors = []
        existing_ids = set()
        async for q in db.questions.find({}, {"id": 1, "_id": 0}):
            existing_ids.add(q.get("id"))
        batch = []

        for i, row in enumerate(rows[1:], start=2):
            try:
                if not row or all(cell is None for cell in row):
                    continue
                question_text = str(row[idx_text]).strip() if idx_text is not None and row[idx_text] else ""
                if not question_text:
                    skipped += 1
                    continue
                choices = []
                letters = [("A", idx_a), ("B", idx_b), ("C", idx_c), ("D", idx_d), ("E", idx_e)]
                correct_val = str(row[idx_correct]).strip().upper() if idx_correct is not None and row[idx_correct] else ""
                for letter, idx in letters:
                    if idx is not None and row[idx] and str(row[idx]).strip():
                        text = str(row[idx]).strip()
                        is_correct = letter == correct_val or correct_val == letter
                        choices.append({"id": str(uuid.uuid4())[:8], "text": text, "text_de": text, "is_correct": is_correct})
                if not choices:
                    skipped += 1
                    continue
                has_correct = any(c["is_correct"] for c in choices)
                if not has_correct:
                    choices[0]["is_correct"] = True

                qid = str(uuid.uuid4())
                specialty_id = str(row[idx_spec]).strip().lower() if idx_spec is not None and row[idx_spec] else "unknown"
                explanation = str(row[idx_explanation]).strip() if idx_explanation is not None and row[idx_explanation] else ""
                year_val = row[idx_year] if idx_year is not None and row[idx_year] else 2024
                if year_val and str(year_val).strip().isdigit():
                    year_val = int(year_val)
                else:
                    year_val = 2024
                location_val = str(row[idx_location]).strip().lower() if idx_location is not None and row[idx_location] else "vienna"

                country_val = str(row[idx_country]).strip().lower() if idx_country is not None and row[idx_country] else None
                if country_val and country_val not in ("austria", "germany", "switzerland"):
                    country_val = None

                normalized = {
                    "id": qid,
                    "specialty_id": specialty_id,
                    "question_text": question_text,
                    "question_text_de": question_text,
                    "question_type": "single_choice",
                    "choices": choices,
                    "explanation": explanation,
                    "explanation_de": explanation,
                    "year": year_val,
                    "exam_location": location_val,
                    "country": country_val,
                    "tags": [],
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
                if qid in existing_ids:
                    skipped += 1
                    continue
                existing_ids.add(qid)
                batch.append(normalized)
                if len(batch) >= 100:
                    await db.questions.insert_many(batch)
                    imported += len(batch)
                    batch = []
            except Exception as e:
                errors.append(f"Zeile {i}: {str(e)}")
                skipped += 1
                continue
        if batch:
            await db.questions.insert_many(batch)
            imported += len(batch)
        total = await db.questions.count_documents({})
        return {"imported": imported, "skipped": skipped, "errors": errors[:10], "total_in_db": total, "filename": file.filename}
    except HTTPException:
        raise
    except ImportError:
        raise HTTPException(status_code=500, detail="openpyxl ist nicht installiert. Bitte 'pip install openpyxl' ausführen.")
    except Exception as e:
        logger.error(f"XLSX import error: {e}")
        raise HTTPException(status_code=500, detail=f"XLSX-Import fehlgeschlagen: {str(e)}")


@router.post("/admin/questions/bulk-update-city")
async def bulk_update_city(request: BulkCityUpdate, admin: dict = Depends(get_admin_user)):
    if request.exam_location not in ["vienna", "innsbruck", "andere"]:
        raise HTTPException(status_code=400, detail="Ungültiger Prüfungsort")
    result = await db.questions.update_many({"id": {"$in": request.question_ids}}, {"$set": {"exam_location": request.exam_location}})
    return {"updated": result.modified_count}


@router.post("/admin/questions/bulk-update-city-by-specialty")
async def bulk_update_city_by_specialty(specialty_id: str = "", exam_location: str = "", admin: dict = Depends(get_admin_user)):
    if exam_location not in ["vienna", "innsbruck", "andere"]:
        raise HTTPException(status_code=400, detail="Ungültiger Prüfungsort")
    query = {}
    if specialty_id:
        query["specialty_id"] = specialty_id
    result = await db.questions.update_many(query, {"$set": {"exam_location": exam_location}})
    return {"updated": result.modified_count}


@router.get("/admin/stats")
async def admin_stats(admin: dict = Depends(get_admin_user)):
    total_users = await db.users.count_documents({})
    total_questions = await db.questions.count_documents({})
    total_favorites = await db.favorites.count_documents({})
    pipeline = [{"$group": {"_id": "$specialty_id", "count": {"$sum": 1}}}]
    by_specialty = await db.questions.aggregate(pipeline).to_list(100)
    return {"total_users": total_users, "total_questions": total_questions, "total_favorites": total_favorites,
            "questions_by_specialty": {item["_id"]: item["count"] for item in by_specialty}}


@router.get("/admin/users")
async def get_all_users(admin: dict = Depends(get_admin_user)):
    return await db.users.find({}, {"_id": 0, "password": 0}).to_list(1000)


@router.delete("/admin/users/{user_id}")
async def delete_user(user_id: str, admin: dict = Depends(get_admin_user)):
    if admin["id"] == user_id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.get("is_admin"):
        raise HTTPException(status_code=400, detail="Cannot delete admin users")
    await db.users.delete_one({"id": user_id})
    await db.user_stats.delete_one({"user_id": user_id})
    await db.favorites.delete_many({"user_id": user_id})
    return {"message": "User deleted successfully"}


@router.post("/admin/questions/bulk-delete")
async def bulk_delete_questions(request: BulkDeleteRequest, admin: dict = Depends(get_admin_user)):
    if not request.question_ids:
        raise HTTPException(status_code=400, detail="No question IDs provided")
    result = await db.questions.delete_many({"id": {"$in": request.question_ids}})
    return {"deleted": result.deleted_count}


@router.post("/admin/questions/smart-merge")
async def smart_merge_duplicates(specialty_id: Optional[str] = None, admin: dict = Depends(get_admin_user)):
    match_stage = {}
    if specialty_id:
        match_stage["specialty_id"] = specialty_id
    projection = {"_id": 0, "id": 1, "specialty_id": 1, "year": 1, "exam_location": 1,
                  "question_text_de": 1, "question_text": 1, "choices": 1, "choices_de": 1,
                  "correct_answers": 1, "explanation": 1, "explanation_de": 1, "image_base64": 1}
    all_questions = await db.questions.find(match_stage, projection).to_list(10000)

    def normalize(text):
        if not text: return ""
        return _re.sub(r'\s+', ' ', text.strip().lower())

    def get_choices_fp(q):
        texts = []
        for c in (q.get("choices") or []):
            t = c.get("text_de") or c.get("text") or ""
            if t.strip(): texts.append(normalize(t))
        for c in (q.get("choices_de") or []):
            t = c.get("text") or ""
            if t.strip(): texts.append(normalize(t))
        texts.sort()
        return "|".join(texts)

    def score_q(q):
        s = 0
        if q.get("explanation_de") and len(q["explanation_de"].strip()) > 3: s += 5
        elif q.get("explanation") and len(q["explanation"].strip()) > 3: s += 4
        if q.get("image_base64"): s += 3
        if any(c.get("is_correct") for c in (q.get("choices") or [])): s += 3
        s += sum(1 for c in (q.get("choices") or []) if (c.get("text_de") or c.get("text", "")).strip())
        if q.get("correct_answers") and len(q["correct_answers"]) > 0: s += 2
        if q.get("year"): s += 1
        return s

    groups = {}
    for q in all_questions:
        text = q.get("question_text_de") or q.get("question_text") or ""
        norm_text = normalize(text)
        if not norm_text or len(norm_text) < 10: continue
        key = f"{norm_text}||{get_choices_fp(q)}"
        groups.setdefault(key, []).append(q)

    merged_count = 0
    deleted_ids = []
    merge_details = []
    for key, questions in groups.items():
        if len(questions) < 2: continue
        scored = sorted(questions, key=score_q, reverse=True)
        best = scored[0]
        copies = scored[1:]
        update_fields = {}
        if not (best.get("explanation_de") or "").strip():
            for c in copies:
                if (c.get("explanation_de") or "").strip():
                    update_fields["explanation_de"] = c["explanation_de"]
                    break
        if not best.get("image_base64"):
            for c in copies:
                if c.get("image_base64"):
                    update_fields["image_base64"] = c["image_base64"]
                    break
        if update_fields:
            await db.questions.update_one({"id": best["id"]}, {"$set": update_fields})
        copy_ids = [c["id"] for c in copies]
        deleted_ids.extend(copy_ids)
        merge_details.append({"kept_id": best["id"], "deleted_count": len(copy_ids),
                             "text_preview": (best.get("question_text_de") or "")[:80]})
        merged_count += 1
    if deleted_ids:
        await db.questions.delete_many({"id": {"$in": deleted_ids}})
    return {"merged_groups": merged_count, "deleted_count": len(deleted_ids), "details": merge_details[:50]}


@router.get("/admin/leaderboard")
async def get_leaderboard(admin: dict = Depends(get_admin_user)):
    pipeline = [
        {"$lookup": {"from": "user_stats", "localField": "id", "foreignField": "user_id", "as": "stats"}},
        {"$unwind": {"path": "$stats", "preserveNullAndEmptyArrays": True}},
        {"$project": {"_id": 0, "id": 1, "name": 1, "email": 1, "picture": 1, "created_at": 1, "is_admin": 1,
                      "total_questions": {"$ifNull": ["$stats.total_questions", 0]},
                      "correct_answers": {"$ifNull": ["$stats.correct_answers", 0]},
                      "wrong_answers": {"$ifNull": ["$stats.wrong_answers", 0]}}},
        {"$addFields": {"accuracy": {"$cond": [{"$gt": ["$total_questions", 0]},
                        {"$multiply": [{"$divide": ["$correct_answers", "$total_questions"]}, 100]}, 0]}}},
        {"$sort": {"correct_answers": -1}}
    ]
    return await db.users.aggregate(pipeline).to_list(1000)


@router.post("/admin/activity/heartbeat")
async def update_activity(user: dict = Depends(get_current_user)):
    await db.user_activity.update_one(
        {"user_id": user["id"]},
        {"$set": {"user_id": user["id"], "last_active": datetime.now(timezone.utc).isoformat(),
                  "name": user.get("name"), "email": user.get("email")}},
        upsert=True
    )
    return {"status": "ok"}


@router.get("/admin/activity/online")
async def get_online_users(admin: dict = Depends(get_admin_user)):
    five_minutes_ago = datetime.now(timezone.utc).timestamp() - 300
    activities = await db.user_activity.find({}, {"_id": 0}).to_list(1000)
    online_users = []
    for activity in activities:
        try:
            last_active = datetime.fromisoformat(activity["last_active"].replace("Z", "+00:00"))
            activity["is_online"] = last_active.timestamp() > five_minutes_ago
            online_users.append(activity)
        except:
            continue
    return online_users


@router.get("/admin/export/questions")
async def export_questions(admin: dict = Depends(get_admin_user), specialty_id: Optional[str] = None, exam_location: Optional[str] = None):
    try:
        query = {}
        if specialty_id:
            query["specialty_id"] = specialty_id
        if exam_location:
            query["exam_location"] = exam_location

        logger.info(f"[PDF export] admin={admin.get('email')} specialty={specialty_id!r} location={exam_location!r}")

        questions = await db.questions.find(query, {"_id": 0}).to_list(10000)
        logger.info(f"[PDF export] fetched {len(questions)} questions from MongoDB")

        specialties = await db.specialties.find({}, {"_id": 0}).to_list(100)
        specialty_names = {s["id"]: s["name_de"] for s in specialties}

        for q in questions:
            q["specialty_name"] = specialty_names.get(q.get("specialty_id"), "Unbekannt")

        total = len(questions)
        logger.info(f"[PDF export] returning {total} questions — request complete")

        return {
            "questions": questions,
            "total": total,
            "exported_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(
            f"[PDF export] FAILED: {type(e).__name__}: {e} | "
            f"specialty={specialty_id!r} location={exam_location!r}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Export fehlgeschlagen ({type(e).__name__}): {str(e)}",
        )


CHAPTER_TOPICS = [
    # Chapter 1 (1-10): Basics
    ["Begrüßung", "Anamnese-Grundstruktur", "Hauptbeschwerde", "Schmerzanamnese",
     "Zeitlicher Verlauf", "Begleitsymptome", "Vorerkrankungen", "Medikamente",
     "Allergien", "Familienanamnese"],
    # Chapter 2 (11-20): Untersuchung
    ["Sozialanamnese", "Vegetative Anamnese", "Körperliche Untersuchung", "Vitalzeichen",
     "Dokumentation", "Diagnose stellen", "Differentialdiagnosen", "Therapiegespräch",
     "Aufklärung", "Einwilligung"],
    # Chapter 3 (21-30): Klinische Grundlagen
    ["Kardiologie Basics", "Pneumologie Basics", "Gastroenterologie Basics",
     "Neurologie Basics", "Orthopädie Basics", "Notaufnahme", "Arztbrief Struktur",
     "Arztbrief Sprache", "Arztbrief Diagnosen", "Arztbrief Befunde"],
    # Chapter 4 (31-40): Kardiologie & Angiologie
    ["Kardiovaskuläre Risikofaktoren", "Herzinsuffizienz", "Koronare Herzkrankheit",
     "Herzrhythmusstörungen", "Hypertonie", "Periphere Arterielle Verschlusskrankheit",
     "Venöse Erkrankungen", "Endokarditis", "Kardiomyopathien", "Notfälle Kardiologie"],
    # Chapter 5 (41-50): Pneumologie & Gastroenterologie
    ["Asthma bronchiale", "COPD", "Pneumonie", "Lungenembolie", "Interstitielle Lungenerkrankungen",
     "Gastroösophageale Refluxkrankheit", "Ulkuskrankheit", "Chronisch-entzündliche Darmerkrankungen",
     "Lebererkrankungen", "Pankreatitis"],
    # Chapter 6 (51-60): Neurologie & Psychiatrie
    ["Schlaganfall", "Epilepsie", "Multiple Sklerose", "Kopfschmerzerkrankungen",
     "Parkinson", "Demenz", "Depression", "Angststörungen", "Psychosomatik",
     "Notfälle Neurologie"],
    # Chapter 7 (61-70): Orthopädie & Rheumatologie
    ["Rückenschmerzen", "Arthrose", "Rheumatoide Arthritis", "Osteoporose",
     "Schultererkrankungen", "Knieerkrankungen", "Hüfterkrankungen", "Sportverletzungen",
     "Gicht", "Fibromyalgie"],
    # Chapter 8 (71-80): Endokrinologie & Nephrologie
    ["Diabetes mellitus", "Schilddrüsenerkrankungen", "Nebennierenerkrankungen",
     "Akutes Nierenversagen", "Chronische Niereninsuffizienz", "Elektrolytstörungen",
     "Säure-Basen-Haushalt", "Glomerulonephritis", "Nephrotisches Syndrom",
     "Notfälle Nephrologie"],
    # Chapter 9 (81-90): Prüfungsvorbereitung
    ["FSP-Gesprächsführung", "Komplexe Anamnese", "Schwierige Patientengespräche",
     "Interkulturelle Kommunikation", "Ethik in der Medizin", "Patientenverfügung",
     "Gutachten", "Qualitätsmanagement", "Prüfungssimulation", "Abschlussprüfung"],
]


@router.post("/admin/masterclass/seed")
async def seed_masterclass(admin: dict = Depends(get_admin_user)):
    from database import db
    existing = await db.masterclass_levels.count_documents({})
    if existing >= 90:
        await db.masterclass_levels.delete_many({})
    created = 0
    for ch_idx, topics in enumerate(CHAPTER_TOPICS):
        chapter = ch_idx + 1
        for t_idx, topic in enumerate(topics):
            level_number = ch_idx * 10 + t_idx + 1
            exists = await db.masterclass_levels.find_one({"level_number": level_number})
            if not exists:
                await db.masterclass_levels.insert_one({
                    "level_number": level_number,
                    "title": f"Level {level_number}: {topic}",
                    "description": f"Lerne {topic} — ein wichtiges Thema für die Kenntnisprüfung.",
                    "content": f"Inhalt für {topic} folgt in Kürze.",
                    "chapter": chapter,
                    "topic": topic,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                })
                created += 1
    total = await db.masterclass_levels.count_documents({})
    return {"created": created, "total_levels": total, "message": f"{created} neue Level erstellt, insgesamt {total}"}


async def _llm_generate(system: str, user: str) -> str:
    """Call OpenRouter free models for masterclass content generation. Returns None if all fail."""
    or_key = _os.environ.get("OPENROUTER_API_KEY")
    if not or_key:
        logger.error("OPENROUTER_API_KEY not set")
        return None
    models = ["openrouter/free", "google/gemini-2.0-flash-exp:free", "meta-llama/llama-4-maverick:free"]
    for model in models:
        try:
            async with httpx.AsyncClient(timeout=40) as client:
                r = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {or_key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "https://mcq-medical-prep.academy",
                        "X-Title": "PrepAcademy Masterclass",
                    },
                    json={
                        "model": model,
                        "messages": [
                            {"role": "system", "content": system},
                            {"role": "user", "content": user},
                        ],
                        "max_tokens": 3000,
                        "temperature": 0.7,
                    },
                )
                if r.status_code != 200:
                    continue
                data = r.json()
                if "choices" in data and data["choices"]:
                    content = data["choices"][0]["message"].get("content") or ""
                    if len(content) > 50:
                        return content
        except Exception:
            continue
    return None


@router.post("/admin/masterclass/generate-content")
async def generate_masterclass_content(admin: dict = Depends(get_admin_user)):
    from database import db
    total = 0
    for ch_idx, topics in enumerate(CHAPTER_TOPICS):
        chapter = ch_idx + 1
        start_lv = chapter * 10 - 9
        end_lv = chapter * 10
        topics_list = "\n".join(f"{i+1}. {t}" for i, t in enumerate(topics))
        system = "Du bist ein erfahrener Medizindozent für die deutsche Kenntnisprüfung (FSP). Antworte NUR auf Deutsch."
        prompt = (
            f"Erstelle für jedes der folgenden 10 Themen eine kurze Lerneinheit (80-120 Wörter pro Thema) "
            f"für Kapitel {chapter} der Masterclass. Jede Lerneinheit soll prüfungsrelevantes Wissen vermitteln.\n\n"
            f"Themen:\n{topics_list}\n\n"
            f"Format: Jede Lerneinheit beginnt mit '### LEVEL X ###' (X = Nummer von {start_lv} bis {end_lv}). "
            f"Dann kommt der Lerntext. Beispiel:\n\n"
            f"### LEVEL {start_lv} ###\n[Lerntext für Thema 1]\n\n"
            f"### LEVEL {start_lv+1} ###\n[Lerntext für Thema 2]"
        )
        try:
            async with asyncio.timeout(45):
                text = await _llm_generate(system, prompt)
            if not text:
                logger.warning("Kapitel %d: _llm_generate returned None", chapter)
                continue
            for lv in range(start_lv, end_lv + 1):
                marker = f"### LEVEL {lv} ###"
                start = text.find(marker)
                if start == -1:
                    continue
                start += len(marker)
                next_lv = lv + 1
                next_marker = f"### LEVEL {next_lv} ###"
                end = text.find(next_marker, start)
                lesson = text[start:end].strip() if end != -1 else text[start:].strip()
                if lesson:
                    await db.masterclass_levels.update_one(
                        {"level_number": lv},
                        {"$set": {"content": lesson}}
                    )
                    total += 1
            await asyncio.sleep(0)
        except asyncio.TimeoutError:
            logger.warning("Kapitel %d timeout nach 10s — überspringe", chapter)
            continue
        except Exception as e:
            logger.warning("Kapitel %d fehlgeschlagen: %s", chapter, str(e))
            continue
    return {"updated": total, "total_levels": 90, "message": f"{total} von 90 Levels mit Inhalt befüllt"}


@router.post("/admin/kp-reports/import-bulk")
async def import_kp_reports_bulk(admin: dict = Depends(get_admin_user), request: Request = None):
    if request is None:
        raise HTTPException(status_code=400, detail="Request body required")
    body = await request.json()
    if isinstance(body, list):
        protocols = body
    else:
        protocols = body.get("reports") or body.get("protokolle") or body.get("protocols") or []
    if not isinstance(protocols, list) or len(protocols) == 0:
        raise HTTPException(status_code=400, detail="JSON array or object with 'reports'/'protokolle'/'protocols' array expected")
    inserted = 0
    BATCH_SIZE = 50
    for i in range(0, len(protocols), BATCH_SIZE):
        batch = protocols[i:i+BATCH_SIZE]
        normalized = []
        for p in batch:
            state = p.get("state") or p.get("bundesland") or "Deutschland"
            main_case = p.get("main_case") or p.get("diagnosis") or "Unbekannt"
            full_text = p.get("full_text") or p.get("text") or p.get("content") or p.get("bericht") or ""
            passed = p.get("passed") or p.get("result") or "unbekannt"
            doc = {
                "id": p.get("id") or p.get("protocol_id") or str(uuid.uuid4()),
                "state": state,
                "date": p.get("date", ""),
                "year": p.get("year", 2024),
                "passed": passed,
                "main_case": main_case,
                "author": p.get("author", ""),
                "topics_asked": p.get("topics_asked") or p.get("topics") or p.get("themen") or [],
                "questions_highlighted": p.get("questions_highlighted") or p.get("highlights") or p.get("fragen") or [],
                "difficulty": p.get("difficulty", ""),
                "examiner_notes": p.get("examiner_notes") or p.get("notes") or p.get("notizen") or "",
                "full_text": full_text,
            }
            normalized.append(doc)
        result = await db.kp_reports.insert_many(normalized, ordered=False)
        inserted += len(result.inserted_ids)
        await asyncio.sleep(0)
    return {"inserted": inserted}
