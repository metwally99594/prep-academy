from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from typing import List
import os, json, base64, httpx, re as _re
from datetime import datetime, timezone
from auth import get_current_user

router = APIRouter(prefix="/api", tags=["arztbrief"])

ARZT_PROMPT = """Du bist Experte für deutsche Arztbriefe.
Analysiere diesen Arztbrief und gib strukturiertes Feedback auf Deutsch.

1. STRUKTUR: Ist der Aufbau korrekt?
   (Briefkopf → Diagnosen → Anamnese → Befunde → Therapie → Procedere → Grußformel)
2. SPRACHE: Grammatikfehler und Stilverbesserungen
3. TERMINOLOGIE: Falsche oder fehlende Fachbegriffe
4. VOLLSTÄNDIGKEIT: Was fehlt?

Sei konkret — zeige Beispiele aus dem Brief. Verwende Absätze und Aufzählungen für Lesbarkeit."""


async def _vision_call(image_b64: str) -> str:
    or_key = os.environ.get("OPENROUTER_API_KEY")
    if not or_key:
        raise HTTPException(503, "AI nicht verfügbar — OPENROUTER_API_KEY fehlt")
    try:
        async with httpx.AsyncClient(timeout=60.0) as cl:
            r = await cl.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {or_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://prepacademy-med.com",
                    "X-Title": "PrepAcademy Arztbrief",
                },
                json={
                    "model": "openai/gpt-4o",
                    "messages": [
                        {"role": "system", "content": ARZT_PROMPT},
                        {"role": "user", "content": [
                            {"type": "text", "text": "Analysiere diesen Arztbrief."},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
                        ]},
                    ],
                    "max_tokens": 2000,
                    "temperature": 0.3,
                },
            )
            data = r.json()
            if "choices" in data and data["choices"]:
                return data["choices"][0]["message"]["content"] or ""
            raise HTTPException(503, f"OpenRouter fehlgeschlagen: {str(data)[:200]}")
    except httpx.TimeoutException:
        raise HTTPException(504, "KI-Analyse zeitüberschreitung — bitte versuche es erneut")


@router.post("/arztbrief/analyze")
async def analyze_arztbrief(
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    from database import db

    ext = (file.filename or "").rsplit(".", 1)[-1].lower()
    if ext not in ("jpg", "jpeg", "png", "webp"):
        raise HTTPException(400, "Nur JPG, PNG und WebP sind erlaubt")

    raw = await file.read()
    if len(raw) == 0:
        raise HTTPException(400, "Leere Datei")
    if len(raw) > 10 * 1024 * 1024:
        raise HTTPException(400, "Datei zu groß (max 10MB)")

    b64 = base64.b64encode(raw).decode("ascii")
    feedback = await _vision_call(b64)

    doc = {
        "user_id": user["id"],
        "filename": file.filename or "arztbrief.jpg",
        "feedback": feedback,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.arztbrief_analyses.insert_one(doc)

    return {"feedback": feedback, "filename": file.filename}


@router.get("/arztbrief/history")
async def arztbrief_history(user: dict = Depends(get_current_user)):
    from database import db
    docs = await db.arztbrief_analyses.find(
        {"user_id": user["id"]},
        {"_id": 0, "feedback": 1, "filename": 1, "created_at": 1},
    ).sort("created_at", -1).limit(10).to_list(10)
    return {"history": docs}
