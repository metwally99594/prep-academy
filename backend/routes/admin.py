"""Admin Routes: Import/Export, User Management, Bulk Operations, Stats"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, Response
from typing import Optional
import uuid, json, re as _re, io, base64 as _b64, os as _os
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
                "choices": unified_choices, "explanation": explanation_de, "explanation_de": explanation_de,
                "year": q.get("year", q.get("jahr", 2024)),
                "exam_location": q.get("exam_location", q.get("ort", "vienna")),
                "image_base64": q.get("image_base64", q.get("image", None)),
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


@router.get("/export/categories")
async def export_categories(admin: dict = Depends(get_admin_user)):
    """Return subjects + universities with question counts for the export UI."""
    try:
        specialties = await db.specialties.find({}, {"_id": 0}).to_list(100)
        pipeline_subj = [
            {"$group": {"_id": "$specialty_id", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
        ]
        pipeline_univ = [
            {"$group": {"_id": "$exam_location", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
        ]
        spec_counts_raw = await db.questions.aggregate(pipeline_subj).to_list(100)
        univ_counts_raw = await db.questions.aggregate(pipeline_univ).to_list(50)
        total = await db.questions.count_documents({})

        spec_name_map = {s["id"]: s.get("name_de") or s.get("name") or s["id"] for s in specialties}
        LOC_LABELS = {"vienna": "Wien", "innsbruck": "Innsbruck", "andere": "Andere"}

        subjects = [
            {"id": r["_id"], "name": spec_name_map.get(r["_id"], r["_id"]), "count": r["count"]}
            for r in spec_counts_raw if r["_id"]
        ]
        universities = [
            {"id": r["_id"], "name": LOC_LABELS.get(r["_id"], r["_id"]), "count": r["count"]}
            for r in univ_counts_raw if r["_id"]
        ]
        return {"subjects": subjects, "universities": universities, "total": total}
    except Exception as e:
        logger.error(f"[export/categories] FAILED: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Kategorien-Fehler: {str(e)}")


@router.get("/export/questions/pdf")
async def export_pdf_stream(
    admin: dict = Depends(get_admin_user),
    subject: Optional[str] = None,
    university: Optional[str] = None,
):
    """
    Server-side PDF export using MongoDB cursor streaming.
    Processes one question at a time — no large list held in RAM.
    subject  = specialty_id  (e.g. "internal", "surgery", "all")
    university = exam_location (e.g. "innsbruck", "vienna", "all")
    """
    try:
        from fpdf import FPDF
    except ImportError:
        raise HTTPException(status_code=500, detail="fpdf2 nicht installiert — pip install fpdf2==2.8.7")

    # ── font setup ────────────────────────────────────────────────────────────
    _font_dir = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "fonts")
    _has_unicode = (
        _os.path.exists(_os.path.join(_font_dir, "DejaVuSans.ttf"))
        and _os.path.exists(_os.path.join(_font_dir, "DejaVuSans-Bold.ttf"))
    )

    def _safe(text: str) -> str:
        """Ensure text is safe for the current font encoding."""
        if not text:
            return ""
        if _has_unicode:
            return text
        subs = {
            "ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss",
            "Ä": "Ae", "Ö": "Oe", "Ü": "Ue",
            "–": "-", "—": "-", "…": "...",
            "“": '"', "”": '"', "„": '"',
            "‘": "'", "’": "'",
            "•": "-", "✓": "[+]", "✔": "[+]",
            "°": " Grad",
        }
        for k, v in subs.items():
            text = text.replace(k, v)
        return text.encode("latin-1", "replace").decode("latin-1")

    CORRECT_MARK = " ✓" if _has_unicode else " [+]"
    BRAND = (102, 126, 234)   # #667eea
    GREEN = (22, 163, 74)
    AMBER_BG = (254, 243, 199)
    AMBER_FG = (120, 80, 0)
    GREY_FG  = (80, 80, 80)
    DARK_FG  = (20, 20, 20)

    # ── query ─────────────────────────────────────────────────────────────────
    query: dict = {}
    if subject:
        query["specialty_id"] = subject
    if university and university != "all":
        query["exam_location"] = university

    logger.info(
        f"[PDF stream] start — admin={admin.get('email')!r} "
        f"subject={subject!r} university={university!r}"
    )

    # Specialties: small lookup table, fine to load upfront
    specialties = await db.specialties.find({}, {"_id": 0}).to_list(100)
    specialty_names = {s["id"]: s.get("name_de") or s.get("name") or s["id"]
                       for s in specialties}

    # ── initialise PDF ────────────────────────────────────────────────────────
    PAGE_W   = 210
    MARGIN   = 15
    USABLE_W = PAGE_W - 2 * MARGIN

    pdf = FPDF("P", "mm", "A4")
    pdf.set_auto_page_break(auto=True, margin=15)

    if _has_unicode:
        pdf.add_font("DejaVu",  "",  _os.path.join(_font_dir, "DejaVuSans.ttf"),      uni=True)
        pdf.add_font("DejaVu",  "B", _os.path.join(_font_dir, "DejaVuSans-Bold.ttf"), uni=True)
        FONT = "DejaVu"
    else:
        FONT = "Helvetica"

    # Cover page
    pdf.add_page()
    pdf.set_font(FONT, "B", 26)
    pdf.set_text_color(*BRAND)
    pdf.ln(25)
    pdf.cell(0, 14, _safe("Prep Academy"), ln=True, align="C")

    subtitle = "Fragenexport"
    if subject:
        subtitle += f" – {specialty_names.get(subject, subject)}"
    if university and university != "all":
        loc_label = ("Wien" if university == "vienna"
                     else "Innsbruck" if university == "innsbruck"
                     else university)
        subtitle += f" / {loc_label}"

    pdf.set_font(FONT, "", 13)
    pdf.set_text_color(*GREY_FG)
    pdf.cell(0, 9, _safe(subtitle), ln=True, align="C")
    pdf.ln(5)
    pdf.set_font(FONT, "", 10)
    date_str = datetime.now(timezone.utc).strftime("%d.%m.%Y %H:%M UTC")
    pdf.cell(0, 7, _safe(f"Erstellt am {date_str}"), ln=True, align="C")

    # ── stream questions via cursor — no to_list() ────────────────────────────
    count            = 0
    current_specialty = None

    cursor = db.questions.find(query, {"_id": 0}).sort(
        [("specialty_id", 1), ("year", 1)]
    )

    async for q in cursor:
        count += 1
        spec_id   = q.get("specialty_id") or ""
        spec_name = specialty_names.get(spec_id, spec_id or "Unbekannt")

        # ── specialty section header (new page per specialty) ──────────────
        if spec_name != current_specialty:
            current_specialty = spec_name
            pdf.add_page()
            pdf.set_font(FONT, "B", 15)
            pdf.set_text_color(*BRAND)
            pdf.cell(0, 9, _safe(spec_name), ln=True)
            pdf.set_draw_color(*BRAND)
            pdf.set_line_width(0.4)
            pdf.line(MARGIN, pdf.get_y(), PAGE_W - MARGIN, pdf.get_y())
            pdf.ln(5)
            pdf.set_text_color(*DARK_FG)

        # ── year / location badges ─────────────────────────────────────────
        year     = str(q.get("year") or "")
        loc      = q.get("exam_location") or ""
        loc_name = ("Wien"      if loc == "vienna"
                    else "Innsbruck" if loc == "innsbruck"
                    else loc)

        pdf.set_font(FONT, "B", 9)
        pdf.set_text_color(255, 255, 255)
        if year:
            pdf.set_fill_color(*BRAND)
            w = pdf.get_string_width(year) + 5
            pdf.cell(w, 6, _safe(year), ln=False, fill=True)
            pdf.cell(2, 6, "")
        if loc_name:
            pdf.set_fill_color(100, 100, 100)
            w = pdf.get_string_width(loc_name) + 5
            pdf.cell(w, 6, _safe(loc_name), ln=False, fill=True)
        pdf.ln(8)

        # ── question text ──────────────────────────────────────────────────
        qtext = q.get("question_text_de") or q.get("question_text") or ""
        pdf.set_font(FONT, "B", 11)
        pdf.set_text_color(*DARK_FG)
        pdf.multi_cell(0, 6, _safe(f"{count}. {qtext}"))
        pdf.ln(2)

        # ── image (processed immediately, bytes freed after) ───────────────
        img_b64 = q.get("image_base64") or ""
        if img_b64:
            try:
                raw       = img_b64.split(",", 1)[-1] if "," in img_b64 else img_b64
                img_bytes = _b64.b64decode(raw)
                img_w     = min(USABLE_W * 0.6, 110)
                pdf.image(io.BytesIO(img_bytes), w=img_w)
                pdf.ln(2)
                del img_bytes   # free immediately — do not hold in RAM
            except Exception as img_err:
                logger.warning(f"[PDF stream] skip image q#{count}: {img_err}")

        # ── choices ────────────────────────────────────────────────────────
        choices         = q.get("choices") or q.get("choices_de") or []
        correct_answers = q.get("correct_answers") or []
        for i, c in enumerate(choices):
            is_correct = c.get("is_correct") or (c.get("id") in correct_answers)
            letter     = chr(65 + i)
            ctext      = c.get("text_de") or c.get("text") or ""
            if is_correct:
                pdf.set_font(FONT, "B", 10)
                pdf.set_text_color(*GREEN)
                pdf.multi_cell(0, 6, _safe(f"  {letter}. {ctext}{CORRECT_MARK}"))
            else:
                pdf.set_font(FONT, "", 10)
                pdf.set_text_color(*GREY_FG)
                pdf.multi_cell(0, 6, _safe(f"  {letter}. {ctext}"))
        pdf.set_text_color(*DARK_FG)

        # ── explanation ────────────────────────────────────────────────────
        expl = q.get("explanation_de") or q.get("explanation") or ""
        if expl:
            pdf.ln(1)
            pdf.set_fill_color(*AMBER_BG)
            pdf.set_font(FONT, "I", 9)
            pdf.set_text_color(*AMBER_FG)
            pdf.multi_cell(0, 6, _safe(f"Erklaerung: {expl}"), fill=True)
            pdf.set_text_color(*DARK_FG)

        pdf.ln(6)

    # ── finalise ──────────────────────────────────────────────────────────────
    logger.info(f"[PDF stream] done — {count} questions, building bytes…")
    pdf_bytes = bytes(pdf.output())
    logger.info(f"[PDF stream] output {len(pdf_bytes):,} bytes")

    date_tag = datetime.now().strftime("%Y%m%d")
    fname    = f"PrepAcademy_Export_{subject or 'all'}_{date_tag}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )
