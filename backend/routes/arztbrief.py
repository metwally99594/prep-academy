from datetime import datetime, timezone
import base64
import os

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from auth import get_current_user

router = APIRouter(prefix="/api", tags=["arztbrief"])

ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_PDF_BYTES = 20 * 1024 * 1024
MAX_EXTRACTED_TEXT_CHARS = 28000

ARZT_PROMPT = """Du bist Experte fuer deutsche Arztbriefe und medizinische Pruefungsvorbereitung.
Analysiere den hochgeladenen Arztbrief auf Deutsch. Gib kein endgueltiges medizinisches Urteil,
sondern Lern- und Korrekturfeedback.

Pruefe strukturiert nach diesen Standardbereichen:
1. Kopf/Adressierung: Absender, Empfaenger, Datum, Betreff, Patientendaten, Behandlungszeitraum.
2. Diagnosen: Haupt- und Nebendiagnosen, ICD falls vorhanden, Relevanz und Reihenfolge.
3. Aufnahmegrund/Anamnese: aktuelle Beschwerden, Vorerkrankungen, Risikofaktoren, Allergien.
4. Befunde/Diagnostik: koerperlicher Status, Vitalwerte, Labor, Bildgebung, Funktionsdiagnostik.
5. Verlauf/Epikrise: klinischer Verlauf, Interpretation, Komplikationen, OP/Intervention falls zutreffend.
6. Therapie/Medikation: Massnahmen, Entlassmedikation, Dosierung, Aenderungen, Wechselwirkungen.
7. Procedere/Empfehlungen: Nachsorge, Kontrollen, Warnzeichen, Arbeits-/Belastungshinweise.
8. Sprache/Form: Praezision, Verstaendlichkeit, Fachterminologie, Abkuerzungen, Grammatik.

Antwortformat:
- Kurzurteil mit Score 0-100.
- Fehlende Pflichtpunkte.
- Konkrete Korrekturvorschlaege mit Beispielen.
- Priorisierte To-do-Liste.
- Datenschutz-Hinweis, falls unnoetige personenbezogene Daten sichtbar sind."""


def _openrouter_headers() -> dict:
    or_key = os.environ.get("OPENROUTER_API_KEY")
    if not or_key:
        raise HTTPException(503, "AI nicht verfuegbar - OPENROUTER_API_KEY fehlt")
    return {
        "Authorization": f"Bearer {or_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://prepacademy-med.com",
        "X-Title": "PrepAcademy Arztbrief",
    }


async def _chat_completion(messages: list, max_tokens: int = 2200) -> str:
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=_openrouter_headers(),
                json={
                    "model": "openai/gpt-4o",
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": 0.3,
                },
            )
            data = response.json()
            if "choices" in data and data["choices"]:
                return data["choices"][0]["message"]["content"] or ""
            raise HTTPException(503, f"OpenRouter fehlgeschlagen: {str(data)[:200]}")
    except httpx.TimeoutException:
        raise HTTPException(504, "KI-Analyse Zeitueberschreitung - bitte versuche es erneut")


async def _vision_call(image_b64: str, mime_type: str) -> str:
    return await _chat_completion([
        {"role": "system", "content": ARZT_PROMPT},
        {"role": "user", "content": [
            {"type": "text", "text": "Analysiere diesen Arztbrief als Bild/Scan."},
            {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{image_b64}"}},
        ]},
    ])


async def _pdf_vision_call(images_b64: list[str]) -> str:
    content = [{"type": "text", "text": "Analysiere diesen Arztbrief als gerenderten PDF-Scan."}]
    content.extend(
        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}}
        for image_b64 in images_b64
    )
    return await _chat_completion([
        {"role": "system", "content": ARZT_PROMPT},
        {"role": "user", "content": content},
    ])


async def _text_call(text: str) -> str:
    return await _chat_completion([
        {"role": "system", "content": ARZT_PROMPT},
        {"role": "user", "content": (
            "Analysiere diesen aus einem PDF extrahierten Arztbrieftext. "
            "Wenn durch OCR/Textauszug offensichtliche Luecken entstehen, markiere sie als moegliche Extraktionsluecken.\n\n"
            f"{text[:MAX_EXTRACTED_TEXT_CHARS]}"
        )},
    ])


def _open_pdf(raw: bytes):
    try:
        import fitz
    except Exception:
        raise HTTPException(503, "PDF-Verarbeitung ist nicht verfuegbar")

    try:
        doc = fitz.open(stream=raw, filetype="pdf")
    except Exception:
        raise HTTPException(400, "PDF konnte nicht gelesen werden")

    if doc.page_count == 0:
        doc.close()
        raise HTTPException(400, "PDF enthaelt keine Seiten")
    return doc


def _extract_pdf_text(raw: bytes) -> str:
    doc = _open_pdf(raw)

    try:
        return "\n\n".join(page.get_text("text") for page in doc).strip()
    finally:
        doc.close()


def _render_pdf_pages(raw: bytes, max_pages: int = 3) -> list[str]:
    doc = _open_pdf(raw)
    try:
        import fitz

        rendered = []
        matrix = fitz.Matrix(1.5, 1.5)
        for page_index in range(min(max_pages, doc.page_count)):
            page = doc.load_page(page_index)
            pixmap = page.get_pixmap(matrix=matrix, alpha=False)
            rendered.append(base64.b64encode(pixmap.tobytes("png")).decode("ascii"))
        return rendered
    finally:
        doc.close()


@router.post("/arztbrief/analyze")
async def analyze_arztbrief(
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    from database import db

    filename = file.filename or "arztbrief"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_IMAGE_EXTENSIONS and ext != "pdf":
        raise HTTPException(400, "Nur PDF, JPG, PNG und WebP sind erlaubt")

    raw = await file.read()
    if len(raw) == 0:
        raise HTTPException(400, "Leere Datei")

    if ext == "pdf":
        if len(raw) > MAX_PDF_BYTES:
            raise HTTPException(400, "PDF zu gross (max 20MB)")
        extracted_text = _extract_pdf_text(raw)
        if len(extracted_text) >= 80:
            feedback = await _text_call(extracted_text)
            analysis_mode = "pdf_text"
        else:
            rendered_pages = _render_pdf_pages(raw)
            feedback = await _pdf_vision_call(rendered_pages)
            analysis_mode = "pdf_vision"
        file_type = "pdf"
        extracted_chars = min(len(extracted_text), MAX_EXTRACTED_TEXT_CHARS)
    else:
        if len(raw) > MAX_IMAGE_BYTES:
            raise HTTPException(400, "Bild zu gross (max 10MB)")
        mime_type = {
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "png": "image/png",
            "webp": "image/webp",
        }[ext]
        image_b64 = base64.b64encode(raw).decode("ascii")
        feedback = await _vision_call(image_b64, mime_type)
        file_type = "image"
        extracted_chars = 0

    doc = {
        "user_id": user["id"],
        "filename": filename,
        "file_type": file_type,
        "analysis_mode": analysis_mode if ext == "pdf" else "image_vision",
        "file_size": len(raw),
        "extracted_chars": extracted_chars,
        "feedback": feedback,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.arztbrief_analyses.insert_one(doc)

    return {
        "feedback": feedback,
        "filename": filename,
        "file_type": file_type,
        "analysis_mode": analysis_mode if ext == "pdf" else "image_vision",
        "extracted_chars": extracted_chars,
    }


@router.get("/arztbrief/history")
async def arztbrief_history(user: dict = Depends(get_current_user)):
    from database import db

    docs = await db.arztbrief_analyses.find(
        {"user_id": user["id"]},
        {"_id": 0, "feedback": 1, "filename": 1, "file_type": 1, "analysis_mode": 1, "created_at": 1},
    ).sort("created_at", -1).limit(10).to_list(10)
    return {"history": docs}
