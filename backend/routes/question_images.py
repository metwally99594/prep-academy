"""Admin image upload & bulk import (ZIP + JSON) — additive endpoints.

These endpoints are NEW and do not modify any existing import flow.
Images are stored on local disk under data/uploads/question_images/ and
served via the /uploads static mount in server.py.
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from typing import Optional
import uuid, json, io, zipfile, os, re
from pathlib import Path
from datetime import datetime, timezone

from database import db, logger
from auth import get_admin_user
from services.question_metadata import normalize_question_metadata

router = APIRouter(prefix="/api/admin", tags=["admin-images"])

# Storage paths
_BACKEND_DIR = Path(__file__).resolve().parent.parent
UPLOAD_ROOT = Path(os.environ.get("QUESTION_IMAGE_UPLOAD_DIR", str(_BACKEND_DIR / "data" / "uploads" / "question_images")))
UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)

URL_PREFIX = "/uploads/question_images"
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10 MB per image
MAX_ARCHIVE_SIZE = 200 * 1024 * 1024
MAX_ARCHIVE_UNCOMPRESSED_SIZE = 200 * 1024 * 1024
MAX_ARCHIVE_FILE_SIZE = 50 * 1024 * 1024
# SVG is deliberately rejected: storing user-controlled SVG as a public static
# asset creates a stored-XSS sink unless it is fully sanitized or rasterized.
ALLOWED_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}


def _safe_ext(filename: str) -> str:
    ext = Path(filename or "").suffix.lower()
    return ext if ext in ALLOWED_EXT else ""


def _save_bytes(data: bytes, original_name: str) -> str:
    """Persist bytes to disk under a UUID name; return the public URL."""
    ext = _safe_ext(original_name) or ".png"
    fname = f"{uuid.uuid4().hex}{ext}"
    path = UPLOAD_ROOT / fname
    path.write_bytes(data)
    return f"{URL_PREFIX}/{fname}"


@router.post("/upload-image")
async def upload_image(file: UploadFile = File(...), admin: dict = Depends(get_admin_user)):
    """Upload a single image and return its public URL."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Datei ohne Namen")
    ext = _safe_ext(file.filename)
    if not ext:
        raise HTTPException(status_code=400, detail=f"Bildformat nicht unterstützt. Erlaubt: {sorted(ALLOWED_EXT)}")
    data = await file.read()
    if len(data) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=413, detail=f"Bild zu groß (max {MAX_IMAGE_SIZE // (1024*1024)} MB)")
    if not data:
        raise HTTPException(status_code=400, detail="Leere Datei")
    url = _save_bytes(data, file.filename)
    return {"url": url, "filename": file.filename, "size_bytes": len(data)}


@router.post("/bulk-import-with-images")
async def bulk_import_with_images(
    archive: UploadFile = File(..., description="ZIP file containing images referenced by the JSON"),
    questions_json: UploadFile = File(..., description="JSON array of question objects"),
    admin: dict = Depends(get_admin_user),
):
    """Bulk-import questions where image fields reference filenames inside an attached ZIP.

    The JSON's `question_image_url`, `explanation_image_url`, and `choice_images[id]`
    may be raw filenames (e.g. "EKG_2024_04.png"). Filenames matching entries in the
    ZIP get extracted, saved to the uploads dir, and the JSON is rewritten to point
    at the public `/uploads/...` URL before insert. Values that already look like
    URLs (http://, https://, /uploads/...) are passed through unchanged.

    Returns a summary identical in shape to /admin/import-questions.
    """
    if not archive.filename or not archive.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="archive muss eine .zip-Datei sein")
    if not questions_json.filename or not questions_json.filename.lower().endswith(".json"):
        raise HTTPException(status_code=400, detail="questions_json muss eine .json-Datei sein")

    # 1) Parse JSON
    try:
        raw_json = (await questions_json.read()).decode("utf-8-sig")
        questions = json.loads(raw_json)
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise HTTPException(status_code=400, detail=f"Ungültige JSON-Datei: {e}")
    if not isinstance(questions, list) or not questions:
        raise HTTPException(status_code=400, detail="JSON muss eine nicht-leere Liste sein")

    # 2) Extract images from ZIP into uploads dir; build filename → URL map
    try:
        zip_bytes = await archive.read()
        if len(zip_bytes) > MAX_ARCHIVE_SIZE:
            raise HTTPException(status_code=413, detail="archive zu groß (max 200 MB)")
        zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="archive ist kein gültiges ZIP")

    filename_to_url: dict[str, str] = {}
    extracted = 0
    total_uncompressed = 0
    for info in zf.infolist():
        if info.is_dir():
            continue
        # Strip any directory components to use bare filename as the lookup key
        base = Path(info.filename).name
        if not base or base.startswith("."):
            continue
        ext = _safe_ext(base)
        if not ext:
            continue
        if info.file_size > MAX_ARCHIVE_FILE_SIZE:
            raise HTTPException(status_code=413, detail="Ein Bild im archive ist zu groß (max 50 MB)")
        total_uncompressed += info.file_size
        if total_uncompressed > MAX_ARCHIVE_UNCOMPRESSED_SIZE:
            raise HTTPException(status_code=413, detail="archive ist nach Dekomprimierung zu groß (max 200 MB)")
        with zf.open(info) as fh:
            data = fh.read()
        if len(data) > MAX_IMAGE_SIZE or not data:
            continue
        url = _save_bytes(data, base)
        filename_to_url[base] = url
        extracted += 1
    zf.close()

    def _resolve(ref: Optional[str]) -> Optional[str]:
        if not ref or not isinstance(ref, str):
            return ref
        if ref.startswith(("http://", "https://", "/uploads/", "data:")):
            return ref
        # Bare filename — look it up in the ZIP-extracted map
        return filename_to_url.get(Path(ref).name, ref)

    # 3) Insert questions using same shape as /admin/import-questions
    imported = 0
    skipped = 0
    errors: list[str] = []
    existing_ids: set[str] = set()
    async for q in db.questions.find({}, {"id": 1, "_id": 0}):
        existing_ids.add(q.get("id"))

    batch: list[dict] = []
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

        # Resolve image references
        choice_images_in = q.get("choice_images") or {}
        resolved_choice_images = {
            cid: _resolve(ref) for cid, ref in choice_images_in.items() if ref
        }

        metadata = normalize_question_metadata(q)
        normalized = {
            "id": q.get("id", str(uuid.uuid4())),
            "question_text": question_text_de,
            "question_text_de": question_text_de,
            "question_type": q.get("question_type", "mcq"),
            "choices": unified_choices,
            "explanation": explanation_de,
            "explanation_de": explanation_de,
            "year": q.get("year", q.get("jahr", 2024)),
            "image_base64": q.get("image_base64", q.get("image", None)),
            "question_image_url": _resolve(q.get("question_image_url")),
            "explanation_image_url": _resolve(q.get("explanation_image_url")),
            "choice_images": resolved_choice_images or None,
            "status": q.get("status", "published"),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        normalized.update(metadata)
        normalized.setdefault("specialty_id", "unknown")
        normalized.setdefault("subject_id", normalized["specialty_id"])
        normalized.setdefault("exam_location", "vienna")
        normalized.setdefault("city", normalized["exam_location"])
        if not normalized["question_text_de"]:
            errors.append(f"Frage {i+1}: Kein Fragetext")
            skipped += 1
            continue
        if normalized["id"] in existing_ids:
            skipped += 1
            continue
        existing_ids.add(normalized["id"])
        for key in ("image_base64", "question_image_url", "explanation_image_url", "choice_images"):
            if not normalized.get(key):
                normalized.pop(key, None)
        batch.append(normalized)
        if len(batch) >= 100:
            await db.questions.insert_many(batch)
            imported += len(batch)
            batch = []
    if batch:
        await db.questions.insert_many(batch)
        imported += len(batch)

    total = await db.questions.count_documents({})
    return {
        "imported": imported,
        "skipped": skipped,
        "extracted_images": extracted,
        "errors": errors[:10],
        "total_in_db": total,
    }
