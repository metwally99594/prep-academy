from fastapi import APIRouter, HTTPException, Depends, File, UploadFile
from typing import Optional
import uuid, json, os, re as _re, httpx, time as _time, openai
from datetime import datetime, timezone
from auth import get_current_user

router = APIRouter(prefix="/api", tags=["fsp"])

OR_KEY = os.environ.get("OPENROUTER_API_KEY")
OR_HEADERS = {
    "Authorization": f"Bearer {OR_KEY}",
    "Content-Type": "application/json",
    "HTTP-Referer": "https://mcq-medical-prep.academy",
    "X-Title": "PrepAcademy",
}
OR_URL = "https://openrouter.ai/api/v1/chat/completions"
OR_MODEL = "openai/gpt-4o"

SPECIALTIES = {
    "Kardiologie": ["Brustschmerz", "Herzrasen", "Luftnot", "Ödeme", "Synkope"],
    "Gastroenterologie": ["Bauchschmerzen", "Übelkeit", "Durchfall", "Sodbrennen", "Gelbsucht"],
    "Pneumologie": ["Husten", "Luftnot", "Fieber", "Auswurf", "Brustschmerz"],
    "Neurologie": ["Kopfschmerzen", "Schwindel", "Taubheitsgefühl", "Sehstörungen", "Lähmung"],
    "Orthopädie": ["Rückenschmerzen", "Knieschmerzen", "Schulterprobleme", "Hüftschmerzen", "Nackenschmerzen"],
    "Innere Medizin": ["Müdigkeit", "Gewichtsverlust", "Fieber unklarer Genese", "Nachtschweiß", "Gelenkschmerzen"],
}

DIFFICULTY_PROMPTS = {
    "leicht": "Der Patient hat typische, eindeutige Symptome einer häufigen Erkrankung.",
    "mittel": "Der Patient hat mehrere Symptome, die auf verschiedene Erkrankungen hinweisen könnten.",
    "schwer": "Der Patient hat komplexe, unspezifische Symptome. Die Diagnose ist nicht offensichtlich.",
}

async def _call_or(system: str, user: str, max_tokens: int = 500, temp: float = 0.4) -> str:
    if not OR_KEY:
        raise HTTPException(503, "AI nicht verfügbar — OPENROUTER_API_KEY fehlt")
    async with httpx.AsyncClient(timeout=30.0) as cl:
        r = await cl.post(OR_URL, headers=OR_HEADERS, json={
            "model": OR_MODEL,
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": user}],
            "max_tokens": max_tokens,
            "temperature": temp,
        })
        d = r.json()
        if "choices" in d and d["choices"]:
            content = d["choices"][0]["message"]["content"] or ""
            return _re.sub(r"<think>.*?</think>", "", content, flags=_re.DOTALL).strip()
        raise HTTPException(503, f"FSP-AI fehlgeschlagen: {str(d)[:200]}")


@router.post("/fsp/start")
async def fsp_start(body: dict, user: dict = Depends(get_current_user)):
    from database import db
    specialty = body.get("specialty", "Innere Medizin")
    difficulty = body.get("difficulty", "mittel")
    if specialty not in SPECIALTIES:
        raise HTTPException(400, f"Unbekanntes Fach: {specialty}")
    if difficulty not in DIFFICULTY_PROMPTS:
        raise HTTPException(400, f"Unbekannter Schwierigkeitsgrad: {difficulty}")

    complaints = SPECIALTIES[specialty]
    complaint = complaints[_time.__dict__.get("hash", hash)(str(user["id"]) + str(_time.time())) % len(complaints)]

    system_prompt = f"""Du bist ein Patient in Deutschland, der eine Arztpraxis aufsucht.
Deine Hauptbeschwerde: {complaint}.
Fachgebiet: {specialty}.
{DIFFICULTY_PROMPTS[difficulty]}

Regeln:
- Antworte realistisch wie ein echter Patient auf Deutsch
- Kurze Antworten (2-3 Sätze)
- Kein medizinischer Fachjargon — sprich wie ein Laie
- Antworte nur auf das, was der Arzt fragt
- Erfinde passende Details zu deiner Krankengeschichte wenn der Arzt fragt
- Sei höflich aber besorgt"""
    opening = await _call_or(system_prompt,
        "Der Arzt betritt das Behandlungszimmer und begrüßt dich. Wie reagierst du? Stelle dich kurz vor und beschreibe deine Symptome.",
        200, 0.5)

    session_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    session = {
        "session_id": session_id,
        "user_id": user["id"],
        "specialty": specialty,
        "difficulty": difficulty,
        "complaint": complaint,
        "phase": "patient",
        "history": [
            {"role": "patient", "message": opening, "phase": "patient", "ts": now},
        ],
        "evaluation": None,
        "created_at": now,
        "updated_at": now,
    }
    await db.fsp_sessions.insert_one(session)
    return {"session_id": session_id, "opening_message": opening, "phase": "patient"}


@router.post("/fsp/chat")
async def fsp_chat(body: dict, user: dict = Depends(get_current_user)):
    from database import db
    session_id = body.get("session_id")
    message = body.get("message", "")
    if not session_id or not message:
        raise HTTPException(400, "session_id und message sind erforderlich")
    session = await db.fsp_sessions.find_one({"session_id": session_id, "user_id": user["id"]})
    if not session:
        raise HTTPException(404, "Session nicht gefunden")
    if session["phase"] not in ("patient", "examiner"):
        raise HTTPException(400, "Simulation ist in einer anderen Phase")

    phase = session["phase"]
    now = datetime.now(timezone.utc).isoformat()

    # Append user message
    session["history"].append({"role": "user", "message": message, "phase": phase, "ts": now})

    if phase == "patient":
        complaints = SPECIALTIES.get(session["specialty"], [session["complaint"]])
        complaint = session["complaint"]
        history_text = "\n".join(
            f"{'Patient' if h['role'] == 'patient' else 'Arzt'}: {h['message']}"
            for h in session["history"][-8:]
        )
        system = f"""Du bist ein Patient in Deutschland.
Hauptbeschwerde: {complaint}.
Fachgebiet: {session["specialty"]}.
{DIFFICULTY_PROMPTS[session["difficulty"]]}

Regeln:
- Antworte auf Deutsch, realistisch wie ein echter Patient
- Bleib bei deiner Rolle — kein Arztwissen zeigen
- Kurze Antworten (2-3 Sätze), Laiensprache
- Der Arzt hat dich bisher untersucht und folgendes besprochen:
{history_text}

- Antworte auf die letzte Frage des Arztes."""
        reply = await _call_or(system, message, 250, 0.5)

    else:  # examiner
        history_text = "\n".join(
            f"{'Prüfer' if h['role'] == 'examiner' else 'Kandidat'}: {h['message']}"
            for h in session["history"][-8:]
        )
        system = f"""Du bist ein FSP-Prüfer in Deutschland.
Fachgebiet: {session["specialty"]}.

Regeln:
- Stelle dem Kandidaten anspruchsvolle Fachfragen zu Diagnostik, Therapie und Differentialdiagnosen
- Korrigiere falsche Antworten freundlich aber deutlich
- Bewerte die Antworten im Stillen — zeig keine Punktzahl an
- Antworte auf Deutsch
- Bisheriger Gesprächsverlauf:
{history_text}"""
        reply = await _call_or(system, message, 300, 0.45)

    session["history"].append({"role": phase, "message": reply, "phase": phase, "ts": now})
    session["updated_at"] = now

    patient_msgs = sum(1 for h in session["history"] if h["role"] == "patient" if h["phase"] == "patient")
    examiner_msgs = sum(1 for h in session["history"] if h["role"] == "examiner" if h["phase"] == "examiner")

    await db.fsp_sessions.update_one(
        {"session_id": session_id},
        {"$set": {"history": session["history"], "updated_at": now}}
    )

    can_switch = phase == "patient" and patient_msgs >= 5
    can_end = phase == "examiner" and examiner_msgs >= 5

    return {
        "reply": reply,
        "phase": phase,
        "can_switch": can_switch,
        "can_end": can_end,
    }


@router.post("/fsp/switch-examiner")
async def fsp_switch_examiner(body: dict, user: dict = Depends(get_current_user)):
    from database import db
    session_id = body.get("session_id")
    if not session_id:
        raise HTTPException(400, "session_id erforderlich")
    session = await db.fsp_sessions.find_one({"session_id": session_id, "user_id": user["id"]})
    if not session:
        raise HTTPException(404, "Session nicht gefunden")
    if session["phase"] != "patient":
        raise HTTPException(400, "Nicht in der Patient-Phase")

    now = datetime.now(timezone.utc).isoformat()
    system = f"""Du bist ein FSP-Prüfer in Deutschland.
Fachgebiet: {session["specialty"]}.

Regeln:
- Beginne das Prüfungsgespräch mit einer freundlichen Vorstellung
- Erkläre kurz den Ablauf (5-7 Fragen zu Diagnose, Therapie, Differentialdiagnosen)
- Stelle dann die erste Frage
- Antworte auf Deutsch"""
    opening = await _call_or(system,
        "Der Patient hat den Raum verlassen. Jetzt beginnt das Prüfungsgespräch.", 250, 0.5)

    session["phase"] = "examiner"
    session["history"].append({"role": "examiner", "message": opening, "phase": "examiner", "ts": now})
    session["updated_at"] = now
    await db.fsp_sessions.update_one(
        {"session_id": session_id},
        {"$set": {"phase": "examiner", "history": session["history"], "updated_at": now}}
    )
    return {"examiner_opening": opening, "phase": "examiner"}


@router.post("/fsp/evaluate")
async def fsp_evaluate(body: dict, user: dict = Depends(get_current_user)):
    from database import db
    session_id = body.get("session_id")
    if not session_id:
        raise HTTPException(400, "session_id erforderlich")
    session = await db.fsp_sessions.find_one({"session_id": session_id, "user_id": user["id"]})
    if not session:
        raise HTTPException(404, "Session nicht gefunden")

    conversation = "\n".join(
        f"{h['role'].upper()}: {h['message']}" for h in session["history"]
    )
    system = f"""Du bist ein FSP-Prüfer und bewertest die Leistung eines Kandidaten in einer Fachsprachprüfung (FSP) in Deutschland.
Fachgebiet: {session["specialty"]}.

Bewerte den Kandidaten in 5 Kategorien von 0-100:
1. language — Sprachkompetenz (Grammatik, Wortschatz, Ausdruck)
2. communication — Kommunikationsfähigkeit (Nachfragen, Gesprächsführung)
3. medical_knowledge — Medizinisches Fachwissen
4. structure — Struktur und Systematik
5. terminology — Fachsprachliche Korrektheit

Antworte NUR mit einem gültigen JSON-Objekt, keinem anderen Text:
{{
    "language": 85,
    "communication": 70,
    "medical_knowledge": 80,
    "structure": 75,
    "terminology": 90,
    "overall": 80,
    "feedback": "Zusammenfassende Rückmeldung auf Deutsch (2-3 Sätze)",
    "strengths": ["Stärke 1", "Stärke 2", "Stärke 3"],
    "improvements": ["Verbesserung 1", "Verbesserung 2"]
}}"""
    raw = await _call_or(system, conversation, 400, 0.3)
    # Parse JSON from response
    try:
        evaluation = json.loads(raw)
    except json.JSONDecodeError:
        # Try to extract JSON from markdown code blocks
        m = _re.search(r"```(?:json)?\s*\n?([\s\S]*?)\n?```", raw)
        if m:
            try:
                evaluation = json.loads(m.group(1))
            except json.JSONDecodeError:
                evaluation = None
        else:
            evaluation = None
    if not evaluation or not isinstance(evaluation, dict):
        raise HTTPException(500, f"Konnte Bewertung nicht parsen: {raw[:200]}")

    now = datetime.now(timezone.utc).isoformat()
    session["phase"] = "results"
    session["evaluation"] = evaluation
    session["updated_at"] = now
    await db.fsp_sessions.update_one(
        {"session_id": session_id},
        {"$set": {"phase": "results", "evaluation": evaluation, "updated_at": now}}
    )
    return evaluation


@router.post("/fsp/transcribe")
async def fsp_transcribe(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise HTTPException(503, "Transkription nicht verfügbar — OPENAI_API_KEY oder OPENROUTER_API_KEY fehlt")
    raw = await file.read()
    if not raw:
        raise HTTPException(400, "Leere Audio-Datei")
    try:
        client = openai.OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=("audio.webm", raw, "audio/webm"),
            language="de",
        )
        text = transcript.text or ""
        if not text:
            raise HTTPException(502, "Transkription fehlgeschlagen — kein Text erhalten")
        return {"transcript": text}
    except Exception as e:
        print(f"TRANSCRIBE ERROR: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
