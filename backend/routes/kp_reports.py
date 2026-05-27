from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
import uuid
from auth import get_current_user


router = APIRouter(prefix="/api", tags=["kp_reports"])


@router.get("/kp-reports")
async def get_kp_reports(
    state: Optional[str] = Query(None),
    year: Optional[int] = Query(None),
    case: Optional[str] = Query(None),
    passed: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
):
    from database import db
    query = {}
    if state:
        query["state"] = state
    if year:
        query["year"] = year
    if case:
        query["main_case"] = {"$regex": case, "$options": "i"}
    if passed:
        query["passed"] = passed

    total = await db.kp_reports.count_documents(query)
    reports = await db.kp_reports.find(
        query, {"_id": 0}
    ).sort("date", -1).skip(offset).limit(limit).to_list(limit)

    return {"total": total, "reports": reports}


@router.get("/kp-reports/{report_id}")
async def get_kp_report(report_id: str):
    from database import db
    report = await db.kp_reports.find_one({"id": report_id}, {"_id": 0})
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@router.get("/kp-reports/filters/aggregated")
async def get_kp_report_filters():
    from database import db
    pipeline = [
        {"$group": {
            "_id": None,
            "states": {"$addToSet": "$state"},
            "years": {"$addToSet": "$year"},
            "cases": {"$addToSet": "$main_case"},
        }}
    ]
    result = await db.kp_reports.aggregate(pipeline).to_list(1)
    if not result:
        return {"states": [], "years": [], "cases": []}
    r = result[0]
    return {
        "states": sorted(r.get("states", [])),
        "years": sorted(r.get("years", []), reverse=True),
        "cases": sorted(r.get("cases", [])),
    }


_httpbearer = HTTPBearer(auto_error=False)

async def _get_admin_user(credentials: HTTPAuthorizationCredentials = Depends(_httpbearer)):
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user = await get_current_user(credentials)
    if not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin only")
    return user


@router.post("/admin/kp-reports/seed")
async def seed_kp_reports(admin=Depends(_get_admin_user)):
    from database import db
    reports = _SEED_DATA
    count = 0
    for r in reports:
        existing = await db.kp_reports.find_one({"id": r["id"]})
        if not existing:
            await db.kp_reports.insert_one(r)
            count += 1
    return {"seeded": count, "total": len(reports)}


@router.post("/admin/kp-reports/import-json")
async def import_kp_reports_json(data: dict, admin=Depends(_get_admin_user)):

    from database import db
    reports = data.get("reports", data.get("protokolle", []))
    if not isinstance(reports, list) or len(reports) == 0:
        raise HTTPException(status_code=400, detail="JSON muss ein Array 'reports' oder 'protokolle' enthalten")

    imported = 0
    skipped = 0
    errors = []
    for i, r in enumerate(reports):
        rid = r.get("id") or r.get("protocol_id") or str(uuid.uuid4())
        if not r.get("state") or not r.get("main_case"):
            errors.append(f"Eintrag {i+1}: 'state' und 'main_case' sind erforderlich")
            skipped += 1
            continue
        existing = await db.kp_reports.find_one({"id": rid})
        if existing:
            skipped += 1
            continue
        doc = {
            "id": rid,
            "state": r["state"],
            "date": r.get("date", ""),
            "year": r.get("year", 2024),
            "passed": r.get("passed", ""),
            "main_case": r["main_case"],
            "author": r.get("author", ""),
            "topics_asked": r.get("topics_asked", r.get("topics", r.get("themen", []))),
            "questions_highlighted": r.get("questions_highlighted", r.get("highlights", r.get("fragen", []))),
            "difficulty": r.get("difficulty", ""),
            "examiner_notes": r.get("examiner_notes", r.get("notes", r.get("notizen", ""))),
            "full_text": r.get("full_text", r.get("text", r.get("bericht", ""))),
        }
        await db.kp_reports.insert_one(doc)
        imported += 1

    total = await db.kp_reports.count_documents({})
    return {"imported": imported, "skipped": skipped, "errors": errors[:10], "total_in_db": total}


_SEED_DATA = [
    {
        "id": "nds-2022-01-30-1",
        "state": "Niedersachsen",
        "date": "2022-01-26",
        "year": 2022,
        "passed": "1/3",
        "main_case": "Divertikulitis",
        "author": "Dr. Parvin",
        "topics_asked": ["Divertikulitis", "Bluttransfusion", "Laparoskopie", "MRGN", "Lungenembolie", "Sepsis", "Pneumonie", "Hyperthyreose", "Hypertonie"],
        "questions_highlighted": ["qSOFA", "CRUB 65", "Legionellen Urin Antigen", "RAAS System", "Merseburger Trias"],
        "difficulty": "mittel",
        "examiner_notes": "Anästhesist war stressiger, stellte viele logische Fragen. Gastroenterologin sehr nett.",
        "full_text": "Kenntnisprüfung am 26.01.2022: bestanden! 1/3 bestanden. Mein Fall war Divertikulitis.\n\n1. Teil Chirurgie: Stadien, OP-Indikationen, Komplikationen. Bluttransfusion (Hb-Wert, Bedside Test). Laparoskopie (Kontraindikationen). MRGN.\n\n2. Teil Anästhesie: Lungenembolie (Risikofaktoren, Virchow Trias). Pneumothorax (Röntgen, Drainagen). Sepsis.\n\n3. Teil Gastroenterologie: Pneumonie (nosokomial, CRUB 65, Antibiotika). Legionellen (Urin Antigen, Levofloxacin). Hyperthyreose (Merseburger Trias). Hypertonie (primär/sekundär, RAAS)."
    },
    {
        "id": "nds-2022-01-30-2",
        "state": "Niedersachsen",
        "date": "2022-01-26",
        "year": 2022,
        "passed": "3/3",
        "main_case": "Pyelonephritis",
        "author": "Dr. Melsa",
        "topics_asked": ["Pyelonephritis", "Cholezystitis", "Schenkelhalsfraktur", "DM Typ 1", "Aortendissektion", "Herzinsuffizienz", "EKG"],
        "questions_highlighted": ["qSOFA", "SGLT2 Inhibitoren", "Garden Klassifikation", "Pauwels Klassifikation"],
        "difficulty": "schwer",
        "examiner_notes": "Patientin war sehr aufgeregt. Fragen waren nicht oberflächlich.",
        "full_text": "3/3 bestanden. Fall: Pyelonephritis.\n\n1. Runde: Pyelonephritis, Komplikationen, Sepsis, qSOFA. Ultraschall bei rezidivierender Infektion (Schrumpfnieren).\n\n2. Runde: Cholezystitis, ERCP, Steine. Röntgen: Schenkelhalsfraktur (Garden/Pauwels). DHB vs Endoprothese.\n\n3. Runde: DM Typ 1. EKG: Vorderwandinfarkt. Aortendissektion. Herzinsuffizienz (EF Einteilung). 4 Medikamente: ACE, Aldosteronantagonist, Betablocker, SGLT2.\n\nQuelle: Amboss M3, 99 Seiten Protokolle."
    },
    {
        "id": "nds-2022-01-30-3",
        "state": "Niedersachsen",
        "date": "2022-01-26",
        "year": 2022,
        "passed": "1/3",
        "main_case": "Magenkarzinom",
        "author": "Dastan Nurmaganbetov",
        "topics_asked": ["Magenkarzinom", "Vorhofflimmern", "Ventrikuläre Tachykardie", "Vorderwandinfarkt", "Pneumothorax", "LAE", "Sepsis", "Endokarditis"],
        "questions_highlighted": ["Lauren Klassifikation", "Forest Klassifikation", "Dukes Kriterien", "S3-Leitlinien"],
        "difficulty": "schwer",
        "examiner_notes": "Prüfer halfen bei richtiger Richtung. Atmosphäre freundlich.",
        "full_text": "1/3 bestanden. Fall: Magenkarzinom.\n\n1. Runde: DD Magenkarzinom. Lauren/Forest Klassifikation. B-Symptomatik. Pankreaskarzinom.\n\n2. Runde: Vorhofflimmern. Ventrikuläre Tachykardie (Kardioversion). Vorderwandinfarkt (PCI). Pneumothorax (Bülau). LAE.\n\n3. Runde: Sepsis (Piperacillin/Tazobactam). Endokarditis (Dukes Kriterien). Hyperkalzämie.\n\nQuelle: FIA-Kurs, Amboss, MEX, Anki."
    },
]
