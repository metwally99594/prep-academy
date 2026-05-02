"""
Daily Podcast — generates a short 5-min medical case podcast each day.

Architecture:
1. A scheduled background job (run on backend startup once daily) creates a podcast
   per supported language using a randomly picked specialty.
2. Audio is stored in MongoDB (collection: `daily_podcasts`).
3. Frontend `GET /api/podcast/daily?language=de` returns the latest podcast for that language.
4. Users can navigate prev/next podcasts via `GET /api/podcast/list`.

This generates value EVERY morning without using the Emergent budget for image AI
(it uses OpenRouter Qwen + Edge TTS — both free/cheap) and creates a steady stream
of fresh content for SEO and re-engagement.
"""
import os
import uuid
import asyncio
import logging
import random
import base64
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import httpx
import edge_tts

logger = logging.getLogger("daily-podcast")

# Same speaker presets as the notebook podcast
PODCAST_SPEAKERS = {
    "de": ("de-AT-IngridNeural", "de-AT-JonasNeural"),
    "en": ("en-US-AvaNeural",    "en-US-AndrewNeural"),
    "ar": ("ar-EG-SalmaNeural",  "ar-EG-ShakirNeural"),
    "ru": ("ru-RU-SvetlanaNeural","ru-RU-DmitryNeural"),
    "uk": ("uk-UA-PolinaNeural", "uk-UA-OstapNeural"),
}

LANG_INSTR = {
    "de": {
        "system": "Du bist ein Podcast-Autor für Medizinstudenten. Schreibe nur auf Deutsch.",
        "tags": "[Moderator] und [Experte]",
        "intro": "Willkommen zum heutigen 5-Minuten-Medical-Case",
    },
    "en": {
        "system": "You are a podcast writer for medical students. Reply only in English.",
        "tags": "[Host] and [Expert]",
        "intro": "Welcome to today's 5-minute medical case",
    },
    "ar": {
        "system": "أنت كاتب بودكاست لطلاب الطب. اكتب باللغة العربية فقط.",
        "tags": "[المقدم] و [الخبير]",
        "intro": "أهلاً بكم في حالة اليوم الطبية في 5 دقائق",
    },
    "ru": {
        "system": "Вы — сценарист подкастов для студентов-медиков. Отвечайте только на русском.",
        "tags": "[Ведущий] и [Эксперт]",
        "intro": "Добро пожаловать в сегодняшний 5-минутный медицинский случай",
    },
    "uk": {
        "system": "Ви — сценарист подкастів для студентів-медиків. Відповідайте тільки українською.",
        "tags": "[Ведучий] та [Експерт]",
        "intro": "Ласкаво просимо до сьогоднішнього 5-хвилинного медичного випадку",
    },
}

SPECIALTIES_POOL = [
    "Kardiologie / Cardiology",
    "Neurologie / Neurology",
    "Chirurgie / Surgery",
    "Innere Medizin / Internal Medicine",
    "Notfallmedizin / Emergency Medicine",
    "Pädiatrie / Pediatrics",
    "Gynäkologie / Gynecology",
    "Psychiatrie / Psychiatry",
    "Endokrinologie / Endocrinology",
    "Pneumologie / Pulmonology",
    "Gastroenterologie / Gastroenterology",
    "Nephrologie / Nephrology",
    "Hämatologie / Hematology",
    "Dermatologie / Dermatology",
    "Orthopädie / Orthopedics",
    "Urologie / Urology",
    "HNO / ENT",
    "Augenheilkunde / Ophthalmology",
    "Infektiologie / Infectious Diseases",
    "Onkologie / Oncology",
]

SUPPORTED_LANGS = ["de", "en", "ar", "ru", "uk"]


# ─────────────────────────────────────────────────────────────────────────────
# Generation pipeline
# ─────────────────────────────────────────────────────────────────────────────

async def _llm_qwen(system: str, user: str, max_tokens: int = 1500) -> Optional[str]:
    """Call Qwen3-235B via OpenRouter. Returns text or None."""
    or_key = os.environ.get("OPENROUTER_API_KEY")
    if not or_key:
        return None
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {or_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://mcq-medical-prep.academy",
                    "X-Title": "PrepAcademy Daily Podcast",
                },
                json={
                    "model": "qwen/qwen3-235b-a22b-2507",
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    "max_tokens": max_tokens,
                    "temperature": 0.7,
                },
            )
            data = r.json()
            if "choices" in data and data["choices"]:
                return data["choices"][0]["message"]["content"]
    except Exception as e:
        logger.warning(f"Qwen call failed: {e}")
    return None


def _split_speaker_parts(script: str):
    import re
    all_words = ["moderator", "experte", "host", "expert", "ведущий", "ведущая", "эксперт",
                 "ведучий", "ведуча", "експерт", "المقدم", "الخبير", "doctor"]
    pattern = "|".join(re.escape(w) for w in sorted(all_words, key=len, reverse=True))
    parts = []
    speaker = None
    buffer = []
    mod_words = {"moderator", "host", "ведущий", "ведущая", "ведучий", "ведуча", "المقدم"}
    for line in script.splitlines():
        line = line.strip()
        if not line:
            continue
        m = re.match(rf"\[?\s*({pattern})\s*\]?\s*[:\-]?\s*(.*)", line, re.IGNORECASE)
        if m:
            if speaker and buffer:
                parts.append((speaker, " ".join(buffer).strip()))
            tag = m.group(1).lower()
            speaker = "moderator" if tag in mod_words else "experte"
            buffer = [m.group(2)] if m.group(2) else []
        else:
            buffer.append(line)
    if speaker and buffer:
        parts.append((speaker, " ".join(buffer).strip()))
    if not parts and script.strip():
        parts = [("moderator", script.strip())]
    return parts


async def _synthesize_podcast(script: str, language: str) -> str:
    """Generate base64 MP3 with alternating voices."""
    mod_voice, exp_voice = PODCAST_SPEAKERS.get(language, PODCAST_SPEAKERS["de"])
    parts = _split_speaker_parts(script)
    audio_chunks = []
    for speaker, text in parts:
        if not text:
            continue
        voice = mod_voice if speaker == "moderator" else exp_voice
        comm = edge_tts.Communicate(text=text[:2500], voice=voice, rate="-3%")
        async for ck in comm.stream():
            if ck["type"] == "audio":
                audio_chunks.append(ck["data"])
    return base64.b64encode(b"".join(audio_chunks)).decode("ascii") if audio_chunks else ""


async def _get_random_mcq(db) -> Optional[dict]:
    """Pick a random unused MCQ from the database. Avoids re-using questions used in the last 30 days."""
    # Get questions used in last 30 days to skip them
    thirty_days_ago = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    used = set()
    async for d in db.daily_podcasts.find(
        {"created_at": {"$gte": thirty_days_ago}, "source_question_id": {"$exists": True}},
        {"_id": 0, "source_question_id": 1},
    ):
        if d.get("source_question_id"):
            used.add(d["source_question_id"])

    # Random sample from questions collection (use $sample aggregation)
    pipeline = [
        {"$match": {
            "choices": {"$exists": True, "$ne": []},
            "question_text": {"$exists": True, "$ne": ""},
            "id": {"$nin": list(used)},
        }},
        {"$sample": {"size": 1}},
        {"$project": {"_id": 0}},
    ]
    cursor = db.questions.aggregate(pipeline)
    async for q in cursor:
        return q
    return None


async def _format_mcq_for_prompt(q: dict, db) -> dict:
    """Build a textual representation of the MCQ + lookup specialty name."""
    spec_id = q.get("specialty_id", "")
    spec = await db.specialties.find_one({"id": spec_id}, {"_id": 0, "name_de": 1, "name": 1})
    spec_name = (spec or {}).get("name_de") or (spec or {}).get("name") or spec_id or "Allgemeinmedizin"

    q_text = q.get("question_text_de") or q.get("question_text") or ""
    choices = q.get("choices") or []
    choice_lines = []
    correct_idx = -1
    for i, c in enumerate(choices):
        text = c.get("text_de") or c.get("text") or ""
        marker = " ✓ KORREKT" if c.get("is_correct") else ""
        choice_lines.append(f"  {chr(65+i)}) {text}{marker}")
        if c.get("is_correct"):
            correct_idx = i

    return {
        "specialty": spec_name,
        "year": q.get("year"),
        "city": q.get("exam_location", "").title(),
        "id": q.get("id"),
        "question_text": q_text,
        "choices_block": "\n".join(choice_lines),
        "correct_letter": chr(65 + correct_idx) if correct_idx >= 0 else "?",
        "correct_text": (choices[correct_idx].get("text_de") or choices[correct_idx].get("text", "")) if correct_idx >= 0 else "",
        "explanation": q.get("explanation_de") or q.get("explanation") or "",
    }


async def generate_daily_podcast(db, language: str, specialty: str = None, force: bool = False) -> Optional[dict]:
    """
    Generate one daily podcast for a language. Returns the saved doc or None on failure.
    Now sources real MCQ questions from the database and builds a clinical case around them.
    """
    today = datetime.now(timezone.utc).date().isoformat()
    if not force:
        existing = await db.daily_podcasts.find_one(
            {"date": today, "language": language},
            {"_id": 0},
        )
        if existing:
            logger.info(f"Daily podcast already exists for {today}/{language}")
            return existing

    # 1. Get a real MCQ from the database
    mcq = await _get_random_mcq(db)
    if mcq:
        mcq_data = await _format_mcq_for_prompt(mcq, db)
        specialty = mcq_data["specialty"]
        source_mode = "mcq"
    else:
        specialty = specialty or random.choice(SPECIALTIES_POOL)
        mcq_data = None
        source_mode = "random"
        logger.info(f"No MCQ available, falling back to random topic: {specialty}")

    # 2. Build language-specific prompts that turn the MCQ into a podcast case
    LANG_PROMPTS = {
        "de": {
            "system": "Du bist ein erfahrener Mediziner und Podcast-Autor für Prüfungsvorbereitung. Antworte NUR auf Deutsch.",
            "mcq_prompt": lambda d: f"""Erstelle ein 5-Minuten-Lernpodcast-Skript, das diese REALE Prüfungsfrage in eine klinische Fallgeschichte verwandelt:

═══════════════════════════════════════════════
ECHTE PRÜFUNGSFRAGE ({d['city']}, {d['year']}, {d['specialty']}):

{d['question_text']}

Antwortmöglichkeiten:
{d['choices_block']}

Richtige Antwort: {d['correct_letter']}) {d['correct_text']}
═══════════════════════════════════════════════

Format:
- Verwende [Moderator] und [Experte] als Sprecher-Tags
- [Moderator] beginnt mit: "Willkommen zur heutigen 5-Minuten-Prüfungsvorbereitung. Heute ein Fall aus der {d['specialty']}, basierend auf einer {d['year']}er Prüfungsfrage aus {d['city']}."
- [Experte] präsentiert dann einen REALISTISCHEN Patientenfall, der zur obigen Frage passt (Anamnese, Symptome, Befunde)
- [Moderator] stellt die Prüfungsfrage am Ende und nennt die 5 Antworten
- [Experte] erklärt warum {d['correct_letter']} richtig ist und warum die anderen falsch sind
- Schließt mit Take-Home Messages
- Mindestens 8 Sprecher-Wechsel, lebendig, max 3500 Zeichen, kein Markdown""",
            "topic_prompt": lambda spec: f"Schreibe ein 5-Minuten-Podcast-Skript zu **{spec}**. Verwende [Moderator] und [Experte]. Realistischer klinischer Fall mit Differenzialdiagnose, Diagnostik, Therapie. Mindestens 8 Wechsel, max 3500 Zeichen.",
        },
        "en": {
            "system": "You are an experienced physician and exam-prep podcast writer. Reply ONLY in English.",
            "mcq_prompt": lambda d: f"""Create a 5-minute learning podcast script that turns this REAL exam question into a clinical case story:

═══════════════════════════════════════════════
REAL EXAM QUESTION ({d['city']}, {d['year']}, {d['specialty']}):

{d['question_text']}

Choices:
{d['choices_block']}

Correct answer: {d['correct_letter']}) {d['correct_text']}
═══════════════════════════════════════════════

Format:
- Use [Host] and [Expert] as speaker tags
- [Host] starts: "Welcome to today's 5-minute exam prep. A {d['specialty']} case based on a {d['year']} exam question from {d['city']}."
- [Expert] presents a REALISTIC patient case that matches the question (history, symptoms, findings)
- [Host] presents the exam question with all 5 choices at the end
- [Expert] explains why {d['correct_letter']} is correct and why the others are wrong
- End with take-home messages
- Min 8 speaker turns, lively, max 3500 chars, no markdown""",
            "topic_prompt": lambda spec: f"Write a 5-minute podcast script on **{spec}**. Use [Host] and [Expert]. Realistic clinical case with differential, diagnostics, therapy. Min 8 turns, max 3500 chars.",
        },
        "ar": {
            "system": "أنت طبيب خبير وكاتب بودكاست لإعداد الامتحانات. اكتب فقط باللغة العربية.",
            "mcq_prompt": lambda d: f"""أنشئ سيناريو بودكاست تعليمي مدته 5 دقائق يحول هذا السؤال الامتحاني الحقيقي إلى قصة سريرية:

═══════════════════════════════════════════════
سؤال امتحاني حقيقي ({d['city']}, {d['year']}, {d['specialty']}):

{d['question_text']}

الخيارات:
{d['choices_block']}

الإجابة الصحيحة: {d['correct_letter']}) {d['correct_text']}
═══════════════════════════════════════════════

التنسيق:
- استخدم [المقدم] و [الخبير] كعلامات للمتحدثين
- [المقدم] يبدأ: "أهلاً بكم في إعداد امتحان اليوم في 5 دقائق. حالة من {d['specialty']} مبنية على سؤال امتحاني عام {d['year']} من {d['city']}."
- [الخبير] يقدم حالة مريض واقعية تتوافق مع السؤال
- [المقدم] يعرض السؤال الامتحاني والخيارات الخمسة
- [الخبير] يشرح لماذا {d['correct_letter']} صحيح وغيرها خطأ
- نهاية برسائل أساسية
- 8 تبادلات على الأقل، حيوي، 3500 حرف كحد أقصى، بدون Markdown""",
            "topic_prompt": lambda spec: f"اكتب سيناريو بودكاست 5 دقائق عن **{spec}**. استخدم [المقدم] و [الخبير]. حالة سريرية واقعية مع تشخيص تفريقي وعلاج. على الأقل 8 تبادلات، 3500 حرف كحد أقصى.",
        },
        "ru": {
            "system": "Вы — опытный врач и сценарист подкастов для подготовки к экзаменам. Отвечайте ТОЛЬКО на русском.",
            "mcq_prompt": lambda d: f"""Создайте сценарий 5-минутного учебного подкаста, превращающий этот РЕАЛЬНЫЙ экзаменационный вопрос в клинический случай:

═══════════════════════════════════════════════
РЕАЛЬНЫЙ ЭКЗАМЕНАЦИОННЫЙ ВОПРОС ({d['city']}, {d['year']}, {d['specialty']}):

{d['question_text']}

Варианты:
{d['choices_block']}

Правильный ответ: {d['correct_letter']}) {d['correct_text']}
═══════════════════════════════════════════════

Формат:
- Используйте [Ведущий] и [Эксперт] как теги спикеров
- [Ведущий] начинает: "Добро пожаловать в 5-минутную подготовку к экзамену. Сегодня случай из {d['specialty']}, основанный на экзаменационном вопросе {d['year']} года из {d['city']}."
- [Эксперт] представляет реалистичный клинический случай
- [Ведущий] озвучивает экзаменационный вопрос и 5 вариантов
- [Эксперт] объясняет, почему {d['correct_letter']} правильно
- Завершите главными выводами
- Мин 8 обменов, живо, макс 3500 символов, без markdown""",
            "topic_prompt": lambda spec: f"Напишите сценарий 5-минутного подкаста о **{spec}**. Используйте [Ведущий] и [Эксперт]. Реалистический клинический случай с дифдиагнозом, диагностикой и терапией. Мин 8 обменов, макс 3500 символов.",
        },
        "uk": {
            "system": "Ви — досвідчений лікар і сценарист подкастів з підготовки до іспитів. Відповідайте ТІЛЬКИ українською.",
            "mcq_prompt": lambda d: f"""Створіть сценарій 5-хвилинного навчального подкасту, що перетворює це РЕАЛЬНЕ екзаменаційне питання на клінічний випадок:

═══════════════════════════════════════════════
РЕАЛЬНЕ ЕКЗАМЕНАЦІЙНЕ ПИТАННЯ ({d['city']}, {d['year']}, {d['specialty']}):

{d['question_text']}

Варіанти:
{d['choices_block']}

Правильна відповідь: {d['correct_letter']}) {d['correct_text']}
═══════════════════════════════════════════════

Формат:
- Використовуйте [Ведучий] та [Експерт] як теги
- [Ведучий] починає: "Ласкаво просимо до 5-хвилинної підготовки до іспиту. Сьогодні випадок з {d['specialty']}, заснований на питанні {d['year']} року з {d['city']}."
- [Експерт] представляє реалістичний клінічний випадок
- [Ведучий] озвучує екзаменаційне питання та 5 варіантів
- [Експерт] пояснює, чому {d['correct_letter']} правильно
- Завершіть основними висновками
- Мін 8 обмінів, живо, макс 3500 символів, без markdown""",
            "topic_prompt": lambda spec: f"Напишіть сценарій 5-хвилинного подкасту про **{spec}**. Використовуйте [Ведучий] та [Експерт]. Реалістичний клінічний випадок з диференційною діагностикою. Мін 8 обмінів, макс 3500 символів.",
        },
    }
    plang = (language or "de").lower()
    p = LANG_PROMPTS.get(plang, LANG_PROMPTS["de"])

    user_prompt = p["mcq_prompt"](mcq_data) if mcq_data else p["topic_prompt"](specialty)
    script = await _llm_qwen(p["system"], user_prompt, max_tokens=2400)
    if not script:
        logger.error(f"Failed to generate script for {language}/{specialty}")
        return None

    # 3. Generate audio
    audio_b64 = await _synthesize_podcast(script, language)
    if not audio_b64:
        logger.error(f"Failed to synthesize audio for {language}")
        return None

    # 4. Generate title and summary IN THE SAME LANGUAGE
    title_prompts = {
        "de": f"Gib einen prägnanten Titel (max 60 Zeichen) auf Deutsch für diesen medizinischen Podcast über {specialty}. NUR den Titel, keine Anführungszeichen.",
        "en": f"Give a concise title (max 60 chars) in English for this medical podcast about {specialty}. ONLY the title, no quotes.",
        "ar": f"أعطِ عنواناً موجزاً (60 حرفاً كحد أقصى) باللغة العربية لهذا البودكاست الطبي عن {specialty}. العنوان فقط، بدون علامات اقتباس.",
        "ru": f"Дайте лаконичное название (макс 60 символов) на русском для этого медицинского подкаста о {specialty}. ТОЛЬКО название, без кавычек.",
        "uk": f"Дайте лаконічну назву (макс 60 символів) українською для цього медичного подкасту про {specialty}. ТІЛЬКИ назва, без лапок.",
    }
    summary_prompts = {
        "de": f"Schreibe eine 1-2 Satz Zusammenfassung dieses Podcasts auf Deutsch:\n\n{script[:2500]}",
        "en": f"Write a 1-2 sentence summary of this podcast in English:\n\n{script[:2500]}",
        "ar": f"اكتب ملخصاً من جملة أو جملتين باللغة العربية لهذا البودكاست:\n\n{script[:2500]}",
        "ru": f"Напишите 1-2 предложения резюме этого подкаста на русском:\n\n{script[:2500]}",
        "uk": f"Напишіть 1-2 речення резюме цього подкасту українською:\n\n{script[:2500]}",
    }
    title = (await _llm_qwen(p["system"], title_prompts.get(plang, title_prompts["de"]), max_tokens=80)
             or f"Daily Case: {specialty}").strip().strip('"').strip("«»").strip("'")
    summary = (await _llm_qwen(p["system"], summary_prompts.get(plang, summary_prompts["de"]), max_tokens=200) or "").strip()

    doc = {
        "id": str(uuid.uuid4()),
        "date": today,
        "language": language,
        "specialty": specialty,
        "title": title[:120],
        "summary": summary[:500],
        "script": script,
        "audio_base64": audio_b64,
        "audio_size": len(audio_b64),
        "source_mode": source_mode,
        "source_question_id": mcq_data["id"] if mcq_data else None,
        "source_year": mcq_data["year"] if mcq_data else None,
        "source_city": mcq_data["city"] if mcq_data else None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.daily_podcasts.update_one(
        {"date": today, "language": language},
        {"$set": doc},
        upsert=True,
    )
    logger.info(f"✅ Daily podcast [{language}]: {today} — {title} ({len(audio_b64) / 1024:.0f} KB) | source={source_mode}")
    return doc


async def daily_podcast_loop(db):
    """
    Background loop: every 6 hours, ensure each supported language has a podcast for today.
    Runs forever (started in server.py on startup).
    """
    # Wait a bit on startup to let the server settle
    await asyncio.sleep(30)
    while True:
        try:
            for lang in SUPPORTED_LANGS:
                try:
                    await generate_daily_podcast(db, lang)
                except Exception as e:
                    logger.warning(f"Daily podcast {lang} failed: {e}")
                # small gap so we don't hammer OpenRouter
                await asyncio.sleep(2)
        except Exception as e:
            logger.error(f"Daily podcast loop error: {e}")
        # Re-check every 6 hours
        await asyncio.sleep(6 * 60 * 60)


# ─────────────────────────────────────────────────────────────────────────────
# API routes
# ─────────────────────────────────────────────────────────────────────────────

def make_router(db, get_current_user):
    router = APIRouter(prefix="/api/podcast", tags=["podcast"])

    @router.get("/daily")
    async def get_daily_podcast(language: str = "de"):
        """Public endpoint — returns today's podcast for the requested language."""
        if language not in SUPPORTED_LANGS:
            language = "de"
        today = datetime.now(timezone.utc).date().isoformat()
        doc = await db.daily_podcasts.find_one(
            {"date": today, "language": language},
            {"_id": 0},
        )
        if not doc:
            # Fallback: latest available for that language
            doc = await db.daily_podcasts.find_one(
                {"language": language},
                {"_id": 0},
                sort=[("created_at", -1)],
            )
        if not doc:
            raise HTTPException(status_code=404, detail="Heute noch kein Podcast verfügbar")
        return doc

    @router.get("/list")
    async def list_podcasts(language: str = "de", limit: int = 14):
        """Last N days of podcasts for browsing."""
        if language not in SUPPORTED_LANGS:
            language = "de"
        cursor = db.daily_podcasts.find(
            {"language": language},
            {"_id": 0, "audio_base64": 0, "script": 0},  # exclude heavy fields for the list
        ).sort("created_at", -1).limit(min(limit, 30))
        items = []
        async for d in cursor:
            items.append(d)
        return {"items": items}

    @router.get("/{podcast_id}")
    async def get_podcast(podcast_id: str):
        doc = await db.daily_podcasts.find_one({"id": podcast_id}, {"_id": 0})
        if not doc:
            raise HTTPException(status_code=404, detail="Podcast nicht gefunden")
        return doc

    class TriggerRequest(BaseModel):
        language: str = "de"
        force: bool = True

    @router.post("/admin/generate")
    async def admin_trigger(req: TriggerRequest, user: dict = Depends(get_current_user)):
        """Admin manual trigger — useful for testing."""
        if not user.get("is_admin"):
            raise HTTPException(status_code=403, detail="Admin only")
        doc = await generate_daily_podcast(db, req.language, force=req.force)
        if not doc:
            raise HTTPException(status_code=500, detail="Generation failed")
        # Don't return the audio in admin response
        slim = {k: v for k, v in doc.items() if k not in ("audio_base64",)}
        slim["audio_size"] = doc.get("audio_size", 0)
        return slim

    return router
