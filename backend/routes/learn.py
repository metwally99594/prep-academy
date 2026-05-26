"""Learning Tools Routes: Study Guide, Flashcards, Mind Maps, Audio Overview, Citations, Source-Grounded Chat"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional
import uuid, os, json
from datetime import datetime, timezone
import asyncio
try:
    from emergentintegrations.llm.chat import LlmChat, UserMessage
except ImportError:
    from openai import AsyncOpenAI as _OAI

    class UserMessage:
        def __init__(self, text: str):
            self.text = text

    class _Chat:
        def __init__(self, api_key, session_id, system_message):
            self._client = _OAI(api_key=api_key)
            self._system = system_message
            self._model = "gpt-4o"

        def with_model(self, provider, model):
            self._model = model
            return self

        async def send_message(self, msg):
            r = await self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "system", "content": self._system},
                          {"role": "user", "content": msg.text}],
            )
            return r.choices[0].message.content

    def LlmChat(api_key, session_id, system_message):  # noqa: N802
        return _Chat(api_key=api_key, session_id=session_id, system_message=system_message)

from database import db, logger
from auth import get_current_user

router = APIRouter(prefix="/api/learn", tags=["learn"])

# ── Edge TTS voice mappings ──
EDGE_VOICES = {
    "nova":     "de-DE-KatjaNeural",
    "shimmer":  "de-DE-AmalaNeural",
    "alloy":    "de-DE-SeraphinaMultilingualNeural",
    "echo":     "de-DE-ConradNeural",
    "fable":    "de-AT-JonasNeural",
    "onyx":     "de-DE-KillianNeural",
    "de-AT-IngridNeural": "de-AT-IngridNeural",
    "de-AT-JonasNeural":  "de-AT-JonasNeural",
    "de-DE-KatjaNeural":  "de-DE-KatjaNeural",
    "de-DE-ConradNeural": "de-DE-ConradNeural",
}

PODCAST_SPEAKERS = {
    "austrian": ("de-AT-IngridNeural", "de-AT-JonasNeural"),
    "german":   ("de-DE-KatjaNeural",  "de-DE-ConradNeural"),
    "warm":     ("de-DE-AmalaNeural",  "de-DE-KillianNeural"),
    "english":     ("en-US-AvaNeural",  "en-US-AndrewNeural"),
    "british":     ("en-GB-SoniaNeural","en-GB-RyanNeural"),
    "arabic":      ("ar-EG-SalmaNeural","ar-EG-ShakirNeural"),
    "arabic_gulf": ("ar-SA-ZariyahNeural","ar-SA-HamedNeural"),
    "russian":     ("ru-RU-SvetlanaNeural","ru-RU-DmitryNeural"),
    "ukrainian":   ("uk-UA-PolinaNeural","uk-UA-OstapNeural"),
}

LANG_PRESET_DEFAULT = {
    "de": "austrian",
    "en": "english",
    "ar": "arabic",
    "ru": "russian",
    "uk": "ukrainian",
}

SPEAKER_TAGS = {
    "de": {"moderator": ["moderator", "sprecher 1", "speaker 1"], "experte": ["experte", "expertin", "sprecher 2", "speaker 2"]},
    "en": {"moderator": ["host", "moderator", "speaker 1", "interviewer"], "experte": ["expert", "guest", "speaker 2", "doctor"]},
    "ar": {"moderator": ["مقدم", "المقدم", "المذيع", "moderator"], "experte": ["خبير", "الخبير", "الطبيب", "expert"]},
    "ru": {"moderator": ["ведущий", "ведущая", "модератор", "moderator"], "experte": ["эксперт", "врач", "expert"]},
    "uk": {"moderator": ["ведучий", "ведуча", "модератор"], "experte": ["експерт", "лікар"]},
}

LANG_DEFAULT_VOICE = {
    "de": "de-AT-IngridNeural",
    "en": "en-US-AvaNeural",
    "ar": "ar-EG-SalmaNeural",
    "ru": "ru-RU-SvetlanaNeural",
    "uk": "uk-UA-PolinaNeural",
}

LANG_MAP = {
    "de": "Antworte auf Deutsch. Verwende medizinische Fachbegriffe auf Deutsch.",
    "en": "Answer in English. Use medical terminology.",
    "ar": "أجب بالعربية مع ذكر المصطلحات الألمانية بين قوسين.",
    "ru": "Отвечайте на русском. Используйте немецкую терминологию в скобках.",
    "uk": "Відповідайте українською. Вказуйте німецьку термінологію в дужках.",
}

async def _llm_text(system_msg: str, user_msg: str, max_tokens: int = 1500, model_key: str = None) -> str:
    """Text-only LLM call via OpenRouter — respects model_key for model selection."""
    import re as _re, httpx
    or_key = os.environ.get("OPENROUTER_API_KEY")
    if not or_key:
        return ""

    if model_key == "metsu":
        async def _call_model(m: str) -> tuple:
            try:
                async with httpx.AsyncClient(timeout=60.0) as cl:
                    r = await cl.post(
                        "https://openrouter.ai/api/v1/chat/completions",
                        headers={"Authorization": f"Bearer {or_key}", "Content-Type": "application/json",
                                 "HTTP-Referer": "https://mcq-medical-prep.academy", "X-Title": "PrepAcademy Learn"},
                        json={"model": m, "messages": [{"role": "system", "content": system_msg}, {"role": "user", "content": user_msg}],
                              "max_tokens": max_tokens, "temperature": 0.4},
                    )
                    d = r.json()
                    if "choices" in d and d["choices"]:
                        c = _re.sub(r"<think>.*?</think>", "", (d["choices"][0]["message"]["content"] or ""), flags=_re.DOTALL).strip()
                        return (m, c)
            except Exception:
                pass
            return (m, "")
        results = await asyncio.gather(*[_call_model(m) for m in METSU_MODELS], return_exceptions=True)
        scored = []
        for r in results:
            if isinstance(r, tuple) and r[1]:
                model_name, text = r
                score = len(text)
                refusals = ["i cannot", "i'm sorry", "i don't have", "unable to", "i am an ai", "cannot answer", "i apologize", "not appropriate"]
                for rf in refusals:
                    if rf in text.lower():
                        score -= 200
                if len(text) < 50:
                    score -= 100
                scored.append((score, model_name, text))
        scored.sort(key=lambda x: x[0], reverse=True)
        if scored:
            logger.info(f"metsu ensemble: best={scored[0][1]} score={scored[0][0]} total={len(scored)}")
            return scored[0][2]
        return ""
        for m in ["deepseek/deepseek-v4-flash:free", "meta-llama/llama-3.3-70b-instruct:free"]:
            try:
                async with httpx.AsyncClient(timeout=90.0) as cl:
                    r = await cl.post(
                        "https://openrouter.ai/api/v1/chat/completions",
                        headers={"Authorization": f"Bearer {or_key}", "Content-Type": "application/json",
                                 "HTTP-Referer": "https://mcq-medical-prep.academy", "X-Title": "PrepAcademy Learn"},
                        json={"model": m, "messages": [{"role": "system", "content": system_msg}, {"role": "user", "content": user_msg}],
                              "max_tokens": max_tokens, "temperature": 0.4},
                    )
                    d = r.json()
                    if "choices" in d and d["choices"]:
                        return _re.sub(r"<think>.*?</think>", "", (d["choices"][0]["message"]["content"] or ""), flags=_re.DOTALL).strip()
            except Exception:
                continue
        return ""

    models = {
        "gpt-4o": "openai/gpt-4o",
        "claude-sonnet": "anthropic/claude-sonnet-4-5-20250929",
        "gemini-flash": "google/gemma-4-31b-it:free",
    }
    or_model = models.get(model_key, "meta-llama/llama-3.3-70b-instruct:free")
    try:
        async with httpx.AsyncClient(timeout=55.0) as client:
            r = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {or_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://mcq-medical-prep.academy",
                    "X-Title": "PrepAcademy Learn",
                },
                json={
                    "model": or_model,
                    "messages": [
                        {"role": "system", "content": system_msg},
                        {"role": "user", "content": user_msg},
                    ],
                    "max_tokens": max_tokens,
                    "temperature": 0.4,
                },
            )
            d = r.json()
            if "error" in d:
                logger.warning(f"OpenRouter error: {d['error']}")
            elif "choices" in d and d["choices"]:
                content = d["choices"][0]["message"]["content"] or ""
                return _re.sub(r"<think>.*?</think>", "", content, flags=_re.DOTALL).strip()
    except Exception as e:
        logger.error(f"OpenRouter LLM call failed: {e}")
    logger.error("OpenRouter LLM call failed — no response")
    return ""

async def _synthesize_edge_tts(text: str, voice: str) -> str:
    import base64, edge_tts
    edge_voice = EDGE_VOICES.get(voice, voice if voice.startswith("de-") else "de-DE-KatjaNeural")
    communicate = edge_tts.Communicate(text=text[:8000], voice=edge_voice, rate="-5%", pitch="+0Hz")
    chunks = []
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            chunks.append(chunk["data"])
    return base64.b64encode(b"".join(chunks)).decode("ascii")


def _split_podcast_script(script: str, language: str = "de"):
    """Parse a Moderator/Experte script into ordered (speaker, text) parts. Language-aware."""
    import re
    tags = SPEAKER_TAGS.get(language, SPEAKER_TAGS["de"])
    mod_words = tags["moderator"]
    exp_words = tags["experte"]
    # Build a regex that matches any speaker tag from any language (be tolerant)
    all_tags = list(set(mod_words + exp_words + sum([t["moderator"] + t["experte"] for t in SPEAKER_TAGS.values()], [])))
    tag_pattern = "|".join(re.escape(t) for t in sorted(all_tags, key=len, reverse=True))

    parts = []
    current_speaker = None
    current_text = []
    for line in script.splitlines():
        line = line.strip()
        if not line:
            continue
        m = re.match(rf"\[?\s*({tag_pattern})\s*\]?\s*[:\-–—]?\s*(.*)", line, re.IGNORECASE)
        if m:
            if current_speaker and current_text:
                parts.append((current_speaker, " ".join(current_text).strip()))
            tag = m.group(1).lower()
            # Determine role based on tag word lists across all languages
            is_moderator = any(w in tag for langtags in SPEAKER_TAGS.values() for w in langtags["moderator"])
            current_speaker = "moderator" if is_moderator else "experte"
            current_text = [m.group(2)] if m.group(2) else []
        else:
            current_text.append(line)
    if current_speaker and current_text:
        parts.append((current_speaker, " ".join(current_text).strip()))
    if not parts and script.strip():
        parts = [("moderator", script.strip())]
    return parts


async def _synthesize_podcast(script: str, preset: str = "austrian", language: str = "de") -> str:
    """Generate a real 2-speaker podcast by alternating voices and concatenating MP3 chunks."""
    import base64, edge_tts
    mod_voice, exp_voice = PODCAST_SPEAKERS.get(preset, PODCAST_SPEAKERS["austrian"])
    parts = _split_podcast_script(script, language=language)
    audio_chunks = []
    for speaker, text in parts:
        if not text:
            continue
        voice = mod_voice if speaker == "moderator" else exp_voice
        comm = edge_tts.Communicate(text=text[:2500], voice=voice, rate="-5%")
        async for ck in comm.stream():
            if ck["type"] == "audio":
                audio_chunks.append(ck["data"])
    return base64.b64encode(b"".join(audio_chunks)).decode("ascii") if audio_chunks else ""


class MindMapRequest(BaseModel):
    notebook_id: Optional[str] = None
    chunk_index: Optional[int] = None
    specialty_id: Optional[str] = None
    topic: Optional[str] = None
    language: str = "de"
    model: str = "gpt-4o"

class AudioRequest(BaseModel):
    notebook_id: Optional[str] = None
    chunk_index: Optional[int] = None
    specialty_id: Optional[str] = None
    topic: Optional[str] = None
    language: str = "de"
    voice: str = "nova"

class SourceChatRequest(BaseModel):
    notebook_id: str
    message: str
    language: str = "de"
    model: str = "gpt-4o"


MODEL_MAP = {
    "gpt-4o": ("openai", "gpt-4o"),
    "claude-sonnet": ("anthropic", "claude-sonnet-4-5-20250929"),
    "gemini-flash": ("gemini", "gemini-3-flash-preview"),
    "metsu": ("openrouter", "metsu"),
}

METSU_MODELS = [
    "deepseek/deepseek-v4-flash:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "nousresearch/hermes-3-llama-3.1-405b:free",
    "qwen/qwen3-next-80b-a3b-instruct:free",
]


class AudioTTSRequest(BaseModel):
    audio_id: Optional[str] = ""
    script: Optional[str] = ""
    voice: str = "nova"
    notebook_id: Optional[str] = ""
    podcast_mode: bool = True
    podcast_preset: Optional[str] = None  # auto-chosen from language if None
    language: str = "de"

@router.post("/audio-tts")
async def generate_audio_tts(req: AudioTTSRequest, user: dict = Depends(get_current_user)):
    """Convert script to speech using Microsoft Edge TTS (free, no key needed). Multi-language."""
    script = req.script or ""
    voice = req.voice
    language = (req.language or "de").lower()

    # If audio_id provided, get script from DB
    if req.audio_id and not script:
        doc = await db.audio_overviews.find_one({"id": req.audio_id, "user_id": user["id"]}, {"_id": 0})
        if doc:
            script = doc.get("script", "")
            voice = doc.get("voice", voice)
            language = doc.get("language", language)

    if not script:
        raise HTTPException(status_code=400, detail="Kein Skript vorhanden")

    # Auto-pick preset based on language if not provided
    preset = req.podcast_preset or LANG_PRESET_DEFAULT.get(language, "austrian")

    try:
        # Detect if script has speaker tags → use podcast mode automatically
        all_tag_words = sum([t["moderator"] + t["experte"] for t in SPEAKER_TAGS.values()], [])
        has_tags = any(f"[{w.title()}]" in script or f"[{w.lower()}]" in script.lower() or f"{w.title()}:" in script for w in all_tag_words)
        # Loose check too — if any tag word appears at start of a line followed by colon
        if not has_tags:
            for w in all_tag_words:
                if any(line.strip().lower().startswith(w.lower() + ":") or line.strip().lower().startswith(f"[{w.lower()}]") for line in script.splitlines()):
                    has_tags = True
                    break

        if req.podcast_mode and has_tags:
            audio_base64 = await _synthesize_podcast(script, preset, language=language)
        else:
            # Single-voice fallback - pick the moderator voice of the preset
            mod_voice, _ = PODCAST_SPEAKERS.get(preset, PODCAST_SPEAKERS["austrian"])
            single_voice = EDGE_VOICES.get(voice, mod_voice)
            audio_base64 = await _synthesize_edge_tts(script, single_voice)

        if not audio_base64:
            raise HTTPException(status_code=500, detail="Audio-Generierung fehlgeschlagen (leer)")

        notebook_id = req.notebook_id or ""
        if not notebook_id and req.audio_id:
            ao = await db.audio_overviews.find_one({"id": req.audio_id}, {"_id": 0, "notebook_id": 1})
            notebook_id = ao.get("notebook_id", "") if ao else ""

        if notebook_id:
            await db.saved_audio.update_one(
                {"notebook_id": notebook_id, "user_id": user["id"], "language": language},
                {"$set": {
                    "notebook_id": notebook_id, "user_id": user["id"],
                    "script": script, "audio_base64": audio_base64,
                    "voice": voice, "language": language, "preset": preset,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }},
                upsert=True
            )

        return {
            "audio_base64": audio_base64,
            "voice": voice,
            "language": language,
            "preset": preset,
            "podcast_mode": req.podcast_mode and has_tags,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Edge-TTS error: {e}")
        raise HTTPException(status_code=500, detail=f"Audio fehlgeschlagen: {str(e)}")


@router.get("/audio-saved/{notebook_id}")
async def get_saved_audio(notebook_id: str, language: str = "de", user: dict = Depends(get_current_user)):
    """Retrieve previously saved audio for a notebook (language-aware)."""
    # Try exact language match first, then fall back to any saved audio
    saved = await db.saved_audio.find_one(
        {"notebook_id": notebook_id, "user_id": user["id"], "language": language},
        {"_id": 0}
    )
    if not saved:
        return {"found": False}
    return {
        "found": True,
        "script": saved.get("script", ""),
        "audio_base64": saved.get("audio_base64", ""),
        "voice": saved.get("voice", "nova"),
        "language": saved.get("language", language),
        "created_at": saved.get("created_at", ""),
    }


@router.post("/audio-overview")
async def generate_audio_overview(req: AudioRequest, user: dict = Depends(get_current_user)):
    """Legacy: Combined script + TTS (may timeout for large files)"""
    context, label, source_type = await _get_context(req, user["id"])
    if not context:
        raise HTTPException(status_code=404, detail="Keine Inhalte gefunden")

    lang = LANG_MAP.get(req.language, LANG_MAP["de"])
    system_msg = f"Du erstellst ein kurzes Audio-Skript (max 2500 Zeichen).\n{lang}\nNatürlicher Sprechstil, keine Markdown-Formatierung."
    prompt = f"""Erstelle ein Audio-Skript für einen kurzen Lernpodcast über: {label}

Basierend auf:
{context[:8000]}

Halte es unter 2500 Zeichen. Kein Markdown."""

    script = await _llm_text(system_msg, prompt, max_tokens=1500)

    try:
        audio_base64 = await _synthesize_edge_tts(script[:4000], req.voice)
        return {"id": str(uuid.uuid4()), "script": script, "audio_base64": audio_base64, "voice": req.voice}
    except Exception as e:
        logger.error(f"TTS error: {e}")
        return {"id": str(uuid.uuid4()), "script": script, "audio_base64": None, "voice": req.voice, "error": "Audio konnte nicht generiert werden."}


# ═══════ 4. MIND MAP ═══════

async def _bg_mind_map(job_id: str, context: str, label: str, language: str, model_key: str = None):
    try:
        lang = LANG_MAP.get(language, LANG_MAP["de"])
        system_msg = f"Du erstellst eine Mind Map als JSON-Struktur.\n{lang}\nAntworte NUR als valides JSON."
        prompt = f"""Erstelle eine Mind Map für: {label}

Inhalt:
{context}

JSON-Format:
{{
  "title": "Hauptthema",
  "children": [
    {{
      "title": "Unterthema 1",
      "color": "#c9a84c",
      "children": [
        {{"title": "Detail 1", "children": []}},
        {{"title": "Detail 2", "children": []}}
      ]
    }}
  ]
}}

4-6 Hauptzweige, je 2-4 Unterpunkte. Farben: #c9a84c, #3b82f6, #10b981, #f59e0b, #ef4444, #8b5cf6.
Nur JSON."""
        response = await _llm_text(system_msg, prompt, max_tokens=800, model_key=model_key)
        try:
            clean = response.strip()
            if clean.startswith("```"):
                clean = clean.split("\n", 1)[1].rsplit("```", 1)[0]
            mind_map = json.loads(clean)
        except (json.JSONDecodeError, IndexError):
            mind_map = {"title": label, "children": [{"title": "Fehler beim Generieren", "children": []}]}
        await _finish_job(job_id, {"mind_map": mind_map})
    except Exception as e:
        await _fail_job(job_id, str(e))

@router.post("/mind-map")
async def generate_mind_map(req: MindMapRequest, background_tasks: BackgroundTasks, user: dict = Depends(get_current_user)):
    context, label, _ = await _get_context(req, user["id"])
    if not context:
        raise HTTPException(status_code=404, detail="Keine Inhalte gefunden")
    job_id = await _start_job(user["id"], "mind-map")
    background_tasks.add_task(_bg_mind_map, job_id, context[:4000], label, req.language, model_key=req.model)
    return {"job_id": job_id, "status": "pending"}


# ═══════ 5. CITATIONS (enhance existing chat) ═══════

@router.post("/chat-with-citations")
async def chat_with_citations(req: SourceChatRequest, user: dict = Depends(get_current_user)):
    """AI chat grounded in user's notebook sources with citations"""
    notebook = await db.notebooks.find_one({"id": req.notebook_id, "user_id": user["id"]}, {"_id": 0})
    if not notebook:
        raise HTTPException(status_code=404, detail="Notebook nicht gefunden")

    sources = notebook.get("sources", [])
    if not sources:
        raise HTTPException(status_code=400, detail="Keine Quellen im Notebook")

    source_ctx = []
    for i, src in enumerate(sources):
        src_label = f"[Quelle {i+1}: {src.get('name', 'Unbenannt')}]"
        content = src.get("content", src.get("summary", ""))[:2000]
        source_ctx.append(f"{src_label}\n{content}")

    sources_text = "\n\n---\n\n".join(source_ctx)
    lang = LANG_MAP.get(req.language, LANG_MAP["de"])
    system_msg = f"""Du bist ein medizinischer Forschungsassistent. Beantworte Fragen NUR basierend auf den gegebenen Quellen.
{lang}
WICHTIG: Zitiere IMMER deine Quellen mit [Quelle X] am Ende jedes Absatzes.
Wenn die Quellen keine Antwort enthalten, sage das ehrlich.

QUELLEN:
{sources_text}"""

    response = await _llm_text(system_msg, req.message, max_tokens=1500, model_key=req.model)

    import re
    citations = list(set(re.findall(r'\[Quelle \d+[^\]]*\]', response)))

    return {
        "response": response,
        "citations": citations,
        "source_count": len(sources),
        "model": req.model,
    }


# ═══════ 6. SOURCE-GROUNDED UPLOAD ═══════

@router.post("/source-upload")
async def upload_source(
    notebook_id: str = Form(...),
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    """Upload a source (PDF/text) to a learning notebook"""
    content = await file.read()
    text = ""
    
    if file.filename.endswith('.txt'):
        text = content.decode('utf-8-sig')
    elif file.filename.endswith('.pdf'):
        try:
            import io
            try:
                import PyPDF2
                reader = PyPDF2.PdfReader(io.BytesIO(content))
                text = "\n".join(page.extract_text() or "" for page in reader.pages)
            except ImportError:
                text = content.decode('utf-8', errors='replace')[:5000]
        except Exception as e:
            logger.error(f"PDF parse error: {e}")
            text = "PDF konnte nicht gelesen werden"
    else:
        text = content.decode('utf-8', errors='replace')[:10000]
    
    summary = await _llm_text(
        "Erstelle eine kurze Zusammenfassung (max 500 Wörter) dieses medizinischen Textes auf Deutsch.",
        text[:8000],
        max_tokens=800,
    )
    
    # Get or create notebook
    notebook = await db.notebooks.find_one({"id": notebook_id, "user_id": user["id"]})
    
    source = {
        "id": str(uuid.uuid4()),
        "name": file.filename,
        "content": text[:15000],
        "summary": summary,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
    }
    
    if notebook:
        await db.notebooks.update_one(
            {"id": notebook_id},
            {"$push": {"sources": source}}
        )
    else:
        await db.notebooks.insert_one({
            "id": notebook_id, "user_id": user["id"], "name": "Lern-Notebook",
            "sources": [source], "created_at": datetime.now(timezone.utc).isoformat(),
        })
    
    return {"source_id": source["id"], "name": file.filename, "summary": summary}


@router.get("/notebooks")
async def get_notebooks(user: dict = Depends(get_current_user)):
    notebooks = []
    async for nb in db.notebooks.find({"user_id": user["id"]}, {"_id": 0, "sources.content": 0}).sort("created_at", -1).limit(20):
        notebooks.append(nb)
    return notebooks
