"""Learning Tools Routes: Study Guide, Flashcards, Mind Maps, Audio Overview, Citations, Source-Grounded Chat"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from pydantic import BaseModel
from typing import List, Optional
import uuid, os, json
from datetime import datetime, timezone
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


async def _llm_text(system_msg: str, user_msg: str, max_tokens: int = 1500) -> str:
    """Robust text-only LLM call. Tries Emergent (gpt-4o) first, falls back to OpenRouter (Qwen) if budget exhausted."""
    em_key = os.environ.get("EMERGENT_LLM_KEY")
    if em_key:
        try:
            chat = LlmChat(
                api_key=em_key,
                session_id=f"llm-{uuid.uuid4().hex[:8]}",
                system_message=system_msg,
            ).with_model("openai", "gpt-4o")
            return await chat.send_message(UserMessage(text=user_msg))
        except Exception as e:
            err = str(e).lower()
            if "budget" in err or "exceeded" in err or "rate" in err or "401" in err:
                logger.info(f"Emergent LLM exhausted, falling back to OpenRouter: {e}")
            else:
                logger.warning(f"Emergent LLM error, trying OpenRouter: {e}")

    # OpenRouter fallback (Qwen3 235B — text-only, very cheap)
    or_key = os.environ.get("OPENROUTER_API_KEY")
    if or_key:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=60.0) as client:
                r = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {or_key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "https://mcq-medical-prep.academy",
                        "X-Title": "PrepAcademy Learn",
                    },
                    json={
                        "model": "qwen/qwen3-235b-a22b-2507",
                        "messages": [
                            {"role": "system", "content": system_msg},
                            {"role": "user", "content": user_msg},
                        ],
                        "max_tokens": max_tokens,
                        "temperature": 0.4,
                    },
                )
                d = r.json()
                if "choices" in d and d["choices"]:
                    return d["choices"][0]["message"]["content"]
                logger.warning(f"OpenRouter no choices: {str(d)[:200]}")
        except Exception as e:
            logger.warning(f"OpenRouter fallback failed: {e}")

    raise HTTPException(status_code=503, detail="AI nicht verfügbar (Budget aufgebraucht — bitte Profile → Universal Key → Add Balance)")


# ═══════ MODELS ═══════

class StudyGuideRequest(BaseModel):
    notebook_id: Optional[str] = None
    chunk_index: Optional[int] = None
    specialty_id: Optional[str] = None
    topic: Optional[str] = None
    language: str = "de"
    model: str = "gpt-4o"

class FlashcardRequest(BaseModel):
    notebook_id: Optional[str] = None
    chunk_index: Optional[int] = None
    specialty_id: Optional[str] = None
    topic: Optional[str] = None
    count: int = 10
    language: str = "de"
    model: str = "gpt-4o"

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
}

LANG_MAP = {
    "de": "Antworte auf Deutsch. Verwende medizinische Fachbegriffe auf Deutsch.",
    "en": "Answer in English. Use medical terminology.",
    "ar": "أجب بالعربية مع ذكر المصطلحات الألمانية بين قوسين.",
    "ru": "Отвечайте на русском. Используйте немецкую терминологию в скобках.",
    "uk": "Відповідайте українською. Вказуйте німецьку термінологію в дужках.",
}


async def _get_questions_context(specialty_id: str = None, topic: str = None, limit: int = 30):
    """Get questions as context for AI"""
    query = {}
    if specialty_id:
        query["specialty_id"] = specialty_id
    if topic:
        query["$or"] = [
            {"question_text_de": {"$regex": topic, "$options": "i"}},
            {"question_text": {"$regex": topic, "$options": "i"}},
        ]
    
    questions = []
    cursor = db.questions.find(query, {"_id": 0, "question_text_de": 1, "question_text": 1, "choices": 1, "choices_de": 1, "explanation_de": 1, "explanation": 1, "year": 1})
    async for q in cursor:
        questions.append(q)
        if len(questions) >= limit:
            break
    
    # Format context
    ctx_parts = []
    for i, q in enumerate(questions):
        text = q.get("question_text_de") or q.get("question_text", "")
        choices = q.get("choices") or q.get("choices_de") or []
        correct = [c.get("text_de") or c.get("text", "") for c in choices if c.get("is_correct")]
        expl = q.get("explanation_de") or q.get("explanation", "")
        ctx_parts.append(f"Q{i+1}: {text}\nAntwort: {', '.join(correct)}\n{f'Erklärung: {expl}' if expl else ''}")
    
    return "\n\n".join(ctx_parts), len(questions)


async def _get_notebook_context(notebook_id: str, user_id: str, chunk_index: int = None) -> tuple:
    """Get notebook PDF text content, optionally a specific chunk"""
    nb = await db.pdf_notebooks.find_one({"id": notebook_id, "user_id": user_id}, {"_id": 0, "text": 1, "filename": 1, "chunks": 1})
    if not nb:
        return "", ""
    if chunk_index is not None and "chunks" in nb:
        chunks = nb.get("chunks", [])
        if 0 <= chunk_index < len(chunks):
            return chunks[chunk_index]["text"][:40000], f"{nb.get('filename', 'Dokument')} - {chunks[chunk_index].get('title', f'Abschnitt {chunk_index+1}')}"
    return nb.get("text", "")[:40000], nb.get("filename", "Dokument")


async def _get_context(req, user_id: str):
    """Get context from notebook (with chunk support) or questions"""
    if hasattr(req, 'notebook_id') and req.notebook_id:
        chunk_idx = getattr(req, 'chunk_index', None)
        text, filename = await _get_notebook_context(req.notebook_id, user_id, chunk_idx)
        if text:
            return text, filename, "notebook"
    if req.specialty_id or req.topic:
        ctx, count = await _get_questions_context(req.specialty_id, req.topic)
        label = req.topic or req.specialty_id or "Medizin"
        if count > 0:
            return ctx, label, "questions"
    ctx, count = await _get_questions_context(limit=15)
    return ctx, "Medizin", "questions"


# ═══════ 1. STUDY GUIDE ═══════

@router.post("/study-guide")
async def generate_study_guide(req: StudyGuideRequest, user: dict = Depends(get_current_user)):
    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="AI not configured")
    
    context, label, source_type = await _get_context(req, user["id"])
    if not context:
        raise HTTPException(status_code=404, detail="Keine Inhalte gefunden")
    
    provider, model = MODEL_MAP.get(req.model, MODEL_MAP["gpt-4o"])
    lang = LANG_MAP.get(req.language, LANG_MAP["de"])
    
    chat = LlmChat(
        api_key=api_key,
        session_id=f"sg-{user['id']}-{uuid.uuid4().hex[:6]}",
        system_message=f"""Du bist ein medizinischer Dozent. Erstelle einen strukturierten Lernleitfaden.
{lang}"""
    ).with_model(provider, model)
    
    prompt = f"""Erstelle einen umfassenden Lernleitfaden für: {label}

Basierend auf folgendem Inhalt:
{context[:15000]}

Struktur:
1. **Übersicht** - Wichtigste Konzepte
2. **Kernthemen** - Detaillierte Erklärungen
3. **Häufige Fallstricke** - Was oft falsch gemacht wird
4. **Zusammenfassung** - Wichtigste Punkte
5. **Prüfungstipps** - Strategien"""

    response = await chat.send_message(UserMessage(text=prompt))
    return {"id": str(uuid.uuid4()), "content": response, "model": req.model}


# ═══════ 2. FLASHCARDS ═══════

@router.post("/flashcards")
async def generate_flashcards(req: FlashcardRequest, user: dict = Depends(get_current_user)):
    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="AI not configured")
    
    context, label, source_type = await _get_context(req, user["id"])
    if not context:
        raise HTTPException(status_code=404, detail="Keine Inhalte gefunden")
    
    provider, model = MODEL_MAP.get(req.model, MODEL_MAP["gpt-4o"])
    lang = LANG_MAP.get(req.language, LANG_MAP["de"])
    
    chat = LlmChat(
        api_key=api_key,
        session_id=f"fc-{user['id']}-{uuid.uuid4().hex[:6]}",
        system_message=f"""Du erstellst Lernkarten (Flashcards) aus medizinischen Inhalten.
{lang}
Antworte NUR als valides JSON-Array."""
    ).with_model(provider, model)
    
    prompt = f"""Erstelle genau {req.count} Lernkarten basierend auf: {label}

Inhalt:
{context[:12000]}

Format als JSON-Array:
[
  {{"front": "Frage/Begriff", "back": "Antwort/Erklärung", "difficulty": "easy|medium|hard"}},
  ...
]

Nur das JSON-Array ausgeben, nichts anderes."""

    response = await chat.send_message(UserMessage(text=prompt))
    
    try:
        clean = response.strip()
        if clean.startswith("```"):
            clean = clean.split("\n", 1)[1].rsplit("```", 1)[0]
        cards = json.loads(clean)
    except (json.JSONDecodeError, IndexError):
        cards = [{"front": "Fehler beim Generieren", "back": response[:200], "difficulty": "medium"}]
    
    return {"id": str(uuid.uuid4()), "cards": cards, "count": len(cards), "model": req.model}


@router.get("/flashcards")
async def get_flashcard_decks(user: dict = Depends(get_current_user)):
    decks = []
    async for d in db.flashcard_decks.find({"user_id": user["id"]}, {"_id": 0}).sort("created_at", -1).limit(20):
        decks.append(d)
    return decks


# ═══════ 3. AUDIO OVERVIEW (2 steps to avoid timeout) ═══════

@router.post("/audio-script")
async def generate_audio_script(req: AudioRequest, user: dict = Depends(get_current_user)):
    """Step 1: Smart Audio Script - Summarize key points from ALL chunks, then build podcast"""
    lang = LANG_MAP.get(req.language, LANG_MAP["de"])
    nb_id = req.notebook_id or ""

    # Get ALL chunks from notebook for smart summarization
    all_key_points = ""
    label = "Medizin"

    # Per-language prompts (CRITICAL — LLM mirrors the prompt language)
    LANG_PROMPTS = {
        "de": {
            "summary_system": "Du bist ein medizinischer Zusammenfasser. Antworte NUR auf Deutsch. Extrahiere prägnante Kernpunkte.",
            "summary_user": lambda title, text: f"Abschnitt: \"{title}\"\n\n{text}\n\nExtrahiere die 3-5 WICHTIGSTEN prüfungsrelevanten Kernpunkte als Stichpunkte (max 200 Wörter). Antworte auf Deutsch.",
            "podcast_system": "Du bist ein professioneller Podcast-Autor für medizinische Bildung. Antworte NUR auf Deutsch. Erstelle ein Zwei-Sprecher-Podcast-Skript zwischen [Moderator] und [Experte]. Min 6 Wechsel, max 4000 Zeichen, kein Markdown.",
            "podcast_user": lambda label, kp: f"Thema: \"{label}\"\n\nWichtigste Punkte:\n\n{kp}\n\nErstelle einen lebendigen Podcast-Dialog auf Deutsch. Format:\n[Moderator] ...\n[Experte] ...\n[Moderator] ...\n... (mindestens 6 Wechsel)\nKlinische Beispiele und Merkhilfen einbauen. Max 4000 Zeichen.",
        },
        "en": {
            "summary_system": "You are a medical content summarizer. Reply ONLY in English. Extract concise key points.",
            "summary_user": lambda title, text: f"Section: \"{title}\"\n\n{text}\n\nExtract the 3-5 MOST IMPORTANT exam-relevant key points as bullet points (max 200 words). Reply in English only.",
            "podcast_system": "You are a professional podcast writer for medical education. Reply ONLY in English. Create a two-speaker podcast script between [Host] and [Expert]. Min 6 turns, max 4000 chars, no markdown.",
            "podcast_user": lambda label, kp: f"Topic: \"{label}\"\n\nKey points:\n\n{kp}\n\nCreate a lively podcast dialogue in English. Format:\n[Host] ...\n[Expert] ...\n[Host] ...\n... (at least 6 turns)\nInclude clinical examples and memory aids. Max 4000 chars.",
        },
        "ar": {
            "summary_system": "أنت ملخص محتوى طبي. اكتب فقط باللغة العربية. استخرج النقاط الأساسية بإيجاز.",
            "summary_user": lambda title, text: f"القسم: \"{title}\"\n\n{text}\n\nاستخرج 3-5 نقاط أساسية مهمة (200 كلمة حد أقصى). اكتب باللغة العربية فقط.",
            "podcast_system": "أنت كاتب بودكاست محترف للتعليم الطبي. اكتب فقط باللغة العربية. أنشئ سيناريو بودكاست بمتحدثين [المقدم] و [الخبير]. على الأقل 6 تبادلات، 4000 حرف كحد أقصى، بدون تنسيق Markdown.",
            "podcast_user": lambda label, kp: f"الموضوع: \"{label}\"\n\nالنقاط الأساسية:\n\n{kp}\n\nأنشئ حواراً حياً بالعربية. التنسيق:\n[المقدم] ...\n[الخبير] ...\n[المقدم] ...\n... (على الأقل 6 تبادلات)\nأدخل أمثلة سريرية وحيل للحفظ. 4000 حرف كحد أقصى.",
        },
        "ru": {
            "summary_system": "Вы — медицинский редактор. Отвечайте ТОЛЬКО на русском. Извлекайте краткие ключевые моменты.",
            "summary_user": lambda title, text: f"Раздел: \"{title}\"\n\n{text}\n\nИзвлеките 3-5 САМЫХ ВАЖНЫХ ключевых моментов в виде списка (макс 200 слов). Отвечайте только на русском.",
            "podcast_system": "Вы — профессиональный сценарист медицинского подкаста. Отвечайте ТОЛЬКО на русском. Создайте сценарий подкаста с двумя спикерами [Ведущий] и [Эксперт]. Минимум 6 обменов, макс 4000 символов, без Markdown.",
            "podcast_user": lambda label, kp: f"Тема: \"{label}\"\n\nКлючевые моменты:\n\n{kp}\n\nСоздайте живой диалог на русском. Формат:\n[Ведущий] ...\n[Эксперт] ...\n[Ведущий] ...\n... (минимум 6 обменов)\nВключите клинические примеры. Макс 4000 символов.",
        },
        "uk": {
            "summary_system": "Ви — медичний редактор. Відповідайте ТІЛЬКИ українською. Витягуйте стислі ключові моменти.",
            "summary_user": lambda title, text: f"Розділ: \"{title}\"\n\n{text}\n\nВитягніть 3-5 НАЙВАЖЛИВІШИХ ключових моментів у вигляді списку (макс 200 слів). Відповідайте тільки українською.",
            "podcast_system": "Ви — професійний сценарист медичного подкасту. Відповідайте ТІЛЬКИ українською. Створіть сценарій подкасту з двома спікерами [Ведучий] та [Експерт]. Мінімум 6 обмінів, макс 4000 символів, без Markdown.",
            "podcast_user": lambda label, kp: f"Тема: \"{label}\"\n\nКлючові моменти:\n\n{kp}\n\nСтворіть живий діалог українською. Формат:\n[Ведучий] ...\n[Експерт] ...\n[Ведучий] ...\n... (мінімум 6 обмінів)\nВключіть клінічні приклади. Макс 4000 символів.",
        },
    }
    plang = (req.language or "de").lower()
    prompts = LANG_PROMPTS.get(plang, LANG_PROMPTS["de"])

    if nb_id:
        nb = await db.pdf_notebooks.find_one({"id": nb_id, "user_id": user["id"]}, {"_id": 0})
        if nb:
            label = nb.get("filename", "Dokument")
            chunks = nb.get("chunks", [])

            if chunks and len(chunks) > 1:
                # Step A: Extract key points from EACH section in the TARGET language
                chunk_summaries = []
                for i, chunk in enumerate(chunks[:8]):
                    title = chunk.get("title", f"Abschnitt {i+1}")
                    text = chunk.get("text", "")[:5000]
                    try:
                        summary = await _llm_text(prompts["summary_system"], prompts["summary_user"](title, text), max_tokens=800)
                        chunk_summaries.append(f"### {title}\n{summary}")
                    except Exception as e:
                        logger.warning(f"Chunk {i} summary failed: {e}")
                        chunk_summaries.append(f"### {title}\n{text[:500]}")

                all_key_points = "\n\n".join(chunk_summaries)
                logger.info(f"Smart audio [{plang}]: Summarized {len(chunk_summaries)} sections for podcast")
            else:
                all_key_points = nb.get("text", "")[:12000]

    if not all_key_points:
        context, label, _ = await _get_context(req, user["id"])
        all_key_points = context[:12000]

    if not all_key_points:
        raise HTTPException(status_code=404, detail="Keine Inhalte gefunden")

    # Step B: Build professional 2-speaker podcast in the TARGET language
    script = await _llm_text(prompts["podcast_system"], prompts["podcast_user"](label, all_key_points), max_tokens=2000)

    audio_id = str(uuid.uuid4())
    await db.audio_overviews.insert_one({
        "id": audio_id, "user_id": user["id"], "script": script,
        "language": req.language, "voice": req.voice,
        "notebook_id": nb_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    return {"id": audio_id, "script": script, "voice": req.voice}


# ═══════ Quick TTS (for Quiz "read aloud" feature) ═══════

class QuickTTSRequest(BaseModel):
    text: str
    language: str = "de"
    voice: Optional[str] = None  # e.g. "de-AT-IngridNeural", or None to auto-pick

# Per-language single-voice default (warm female)
LANG_DEFAULT_VOICE = {
    "de": "de-AT-IngridNeural",     # Austrian female
    "en": "en-US-AvaNeural",
    "ar": "ar-EG-SalmaNeural",
    "ru": "ru-RU-SvetlanaNeural",
    "uk": "uk-UA-PolinaNeural",
}

@router.post("/tts/speak")
async def quick_tts(req: QuickTTSRequest, user: dict = Depends(get_current_user)):
    """Fast single-voice TTS for short text (quiz questions, explanations). FREE via Edge TTS."""
    text = (req.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Kein Text")
    if len(text) > 4000:
        text = text[:4000]
    voice = req.voice or LANG_DEFAULT_VOICE.get((req.language or "de").lower(), "de-AT-IngridNeural")
    try:
        import base64, edge_tts
        comm = edge_tts.Communicate(text=text, voice=voice, rate="-3%")
        chunks = []
        async for ck in comm.stream():
            if ck["type"] == "audio":
                chunks.append(ck["data"])
        if not chunks:
            raise HTTPException(status_code=500, detail="TTS leer")
        return {"audio_base64": base64.b64encode(b"".join(chunks)).decode("ascii"), "voice": voice}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Quick TTS error: {e}")
        raise HTTPException(status_code=500, detail=f"TTS fehlgeschlagen: {str(e)}")


# ═══════ Edge TTS (Microsoft Neural Voices) — FREE, no API key needed ═══════

# Map of voice presets — uses Microsoft Edge TTS for German speakers
# 2-speaker presets for podcast: Moderator (female) + Experte (male)
EDGE_VOICES = {
    # Direct mapping for legacy "voice" param
    "nova":     "de-DE-KatjaNeural",       # warm female (was OpenAI nova)
    "shimmer":  "de-DE-AmalaNeural",       # young female
    "alloy":    "de-DE-SeraphinaMultilingualNeural",  # multilingual female
    "echo":     "de-DE-ConradNeural",      # mature male
    "fable":    "de-AT-JonasNeural",       # Austrian male (PERFECT for Prep Academy!)
    "onyx":     "de-DE-KillianNeural",     # deep male
    # Also accept locale codes directly
    "de-AT-IngridNeural": "de-AT-IngridNeural",
    "de-AT-JonasNeural":  "de-AT-JonasNeural",
    "de-DE-KatjaNeural":  "de-DE-KatjaNeural",
    "de-DE-ConradNeural": "de-DE-ConradNeural",
}

# 2-speaker presets — (moderator_voice, experte_voice) per language
# Default to Austrian voices for German (PrepAcademy is Austrian-focused)
PODCAST_SPEAKERS = {
    # German variants (default for "de")
    "austrian": ("de-AT-IngridNeural", "de-AT-JonasNeural"),       # 🇦🇹
    "german":   ("de-DE-KatjaNeural",  "de-DE-ConradNeural"),      # 🇩🇪
    "warm":     ("de-DE-AmalaNeural",  "de-DE-KillianNeural"),
    # English
    "english":     ("en-US-AvaNeural",  "en-US-AndrewNeural"),     # 🇺🇸
    "british":     ("en-GB-SoniaNeural","en-GB-RyanNeural"),       # 🇬🇧
    # Arabic
    "arabic":      ("ar-EG-SalmaNeural","ar-EG-ShakirNeural"),     # 🇪🇬
    "arabic_gulf": ("ar-SA-ZariyahNeural","ar-SA-HamedNeural"),    # 🇸🇦
    # Russian
    "russian":     ("ru-RU-SvetlanaNeural","ru-RU-DmitryNeural"),  # 🇷🇺
    # Ukrainian
    "ukrainian":   ("uk-UA-PolinaNeural","uk-UA-OstapNeural"),     # 🇺🇦
}

# Default preset for each language
LANG_PRESET_DEFAULT = {
    "de": "austrian",
    "en": "english",
    "ar": "arabic",
    "ru": "russian",
    "uk": "ukrainian",
}

# Speaker tag patterns per language — used when LLM responds in that language
SPEAKER_TAGS = {
    "de": {"moderator": ["moderator", "sprecher 1", "speaker 1"], "experte": ["experte", "expertin", "sprecher 2", "speaker 2"]},
    "en": {"moderator": ["host", "moderator", "speaker 1", "interviewer"], "experte": ["expert", "guest", "speaker 2", "doctor"]},
    "ar": {"moderator": ["مقدم", "المقدم", "المذيع", "moderator"], "experte": ["خبير", "الخبير", "الطبيب", "expert"]},
    "ru": {"moderator": ["ведущий", "ведущая", "модератор", "moderator"], "experte": ["эксперт", "врач", "expert"]},
    "uk": {"moderator": ["ведучий", "ведуча", "модератор"], "experte": ["експерт", "лікар"]},
}


async def _synthesize_edge_tts(text: str, voice: str) -> str:
    """Generate base64-encoded MP3 audio using Microsoft Edge TTS (free)."""
    import edge_tts, base64
    if not text.strip():
        return ""
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
    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="AI not configured")
    
    context, label, source_type = await _get_context(req, user["id"])
    if not context:
        raise HTTPException(status_code=404, detail="Keine Inhalte gefunden")
    
    lang = LANG_MAP.get(req.language, LANG_MAP["de"])
    
    chat = LlmChat(
        api_key=api_key,
        session_id=f"audio-{user['id']}-{uuid.uuid4().hex[:6]}",
        system_message=f"""Du erstellst ein kurzes Audio-Skript (max 2500 Zeichen).
{lang}
Natürlicher Sprechstil, keine Markdown-Formatierung."""
    ).with_model("openai", "gpt-4o")
    
    prompt = f"""Erstelle ein Audio-Skript für einen kurzen Lernpodcast über: {label}

Basierend auf:
{context[:8000]}

Halte es unter 2500 Zeichen. Kein Markdown."""

    script = await chat.send_message(UserMessage(text=prompt))
    
    try:
        from emergentintegrations.llm.openai import OpenAITextToSpeech
        tts = OpenAITextToSpeech(api_key=api_key)
        audio_base64 = await tts.generate_speech_base64(text=script[:4090], model="tts-1", voice=req.voice, speed=0.95)
        return {"id": str(uuid.uuid4()), "script": script, "audio_base64": audio_base64, "voice": req.voice}
    except Exception as e:
        logger.error(f"TTS error: {e}")
        return {"id": str(uuid.uuid4()), "script": script, "audio_base64": None, "voice": req.voice, "error": "Audio konnte nicht generiert werden."}


# ═══════ 4. MIND MAP ═══════

@router.post("/mind-map")
async def generate_mind_map(req: MindMapRequest, user: dict = Depends(get_current_user)):
    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="AI not configured")
    
    context, label, source_type = await _get_context(req, user["id"])
    if not context:
        raise HTTPException(status_code=404, detail="Keine Inhalte gefunden")
    
    provider, model = MODEL_MAP.get(req.model, MODEL_MAP["gpt-4o"])
    lang = LANG_MAP.get(req.language, LANG_MAP["de"])
    
    chat = LlmChat(
        api_key=api_key,
        session_id=f"mm-{user['id']}-{uuid.uuid4().hex[:6]}",
        system_message=f"""Du erstellst eine Mind Map als JSON-Struktur.
{lang}
Antworte NUR als valides JSON."""
    ).with_model(provider, model)
    
    prompt = f"""Erstelle eine Mind Map für: {label}

Inhalt:
{context[:12000]}

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

    response = await chat.send_message(UserMessage(text=prompt))
    
    try:
        clean = response.strip()
        if clean.startswith("```"):
            clean = clean.split("\n", 1)[1].rsplit("```", 1)[0]
        mind_map = json.loads(clean)
    except (json.JSONDecodeError, IndexError):
        mind_map = {"title": label, "children": [{"title": "Fehler beim Generieren", "children": []}]}
    
    return {"mind_map": mind_map, "model": req.model}


# ═══════ 5. CITATIONS (enhance existing chat) ═══════

@router.post("/chat-with-citations")
async def chat_with_citations(req: SourceChatRequest, user: dict = Depends(get_current_user)):
    """AI chat grounded in user's notebook sources with citations"""
    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="AI not configured")
    
    # Get notebook sources
    notebook = await db.notebooks.find_one({"id": req.notebook_id, "user_id": user["id"]}, {"_id": 0})
    if not notebook:
        raise HTTPException(status_code=404, detail="Notebook nicht gefunden")
    
    sources = notebook.get("sources", [])
    if not sources:
        raise HTTPException(status_code=400, detail="Keine Quellen im Notebook")
    
    # Build source context with IDs
    source_ctx = []
    for i, src in enumerate(sources):
        src_label = f"[Quelle {i+1}: {src.get('name', 'Unbenannt')}]"
        content = src.get("content", src.get("summary", ""))[:2000]
        source_ctx.append(f"{src_label}\n{content}")
    
    sources_text = "\n\n---\n\n".join(source_ctx)
    
    provider, model = MODEL_MAP.get(req.model, MODEL_MAP["gpt-4o"])
    lang = LANG_MAP.get(req.language, LANG_MAP["de"])
    
    chat = LlmChat(
        api_key=api_key,
        session_id=f"src-{req.notebook_id}-{user['id']}-{uuid.uuid4().hex[:6]}",
        system_message=f"""Du bist ein medizinischer Forschungsassistent. Beantworte Fragen NUR basierend auf den gegebenen Quellen.
{lang}
WICHTIG: Zitiere IMMER deine Quellen mit [Quelle X] am Ende jedes Absatzes.
Wenn die Quellen keine Antwort enthalten, sage das ehrlich.

QUELLEN:
{sources_text}"""
    ).with_model(provider, model)
    
    response = await chat.send_message(UserMessage(text=req.message))
    
    # Extract citations
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
    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="AI not configured")
    
    # Read file
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
    
    # Summarize with AI
    chat = LlmChat(
        api_key=api_key,
        session_id=f"sum-{uuid.uuid4().hex[:8]}",
        system_message="Erstelle eine kurze Zusammenfassung (max 500 Wörter) dieses medizinischen Textes auf Deutsch."
    ).with_model("openai", "gpt-4o")
    
    summary = await chat.send_message(UserMessage(text=text[:8000]))
    
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
