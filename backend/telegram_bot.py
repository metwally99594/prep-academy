"""Telegram Bot for Prep Academy - Daily MCQ Questions + Web App"""
import os
import random
import asyncio
import logging
from datetime import datetime, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, MenuButtonWebApp
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

logger = logging.getLogger("telegram-bot")


# Silence telegram's polling Conflict spam (expected when prod bot is already polling)
class _TelegramConflictFilter(logging.Filter):
    def filter(self, record):
        msg = record.getMessage()
        if "Conflict: terminated by other getUpdates" in msg:
            return False
        if "Exception happened while polling for updates" in msg:
            return False
        return True

for _name in ("telegram.ext.Updater", "telegram.ext._updater", "telegram.ext._utils.networkloop"):
    logging.getLogger(_name).addFilter(_TelegramConflictFilter())

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
APP_URL = os.environ.get("APP_URL", "https://mcq-medical-prep.academy")


def get_token():
    """Get token - check env again in case it was loaded late"""
    global TELEGRAM_BOT_TOKEN
    if not TELEGRAM_BOT_TOKEN:
        TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    return TELEGRAM_BOT_TOKEN

# Will be set when bot starts
db = None


def get_db():
    global db
    if db is None:
        from database import db as _db
        db = _db
    return db


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command - show Web App button like MedPrüf"""
    welcome = "Tap the button to open Prep Academy and sign in:"
    
    keyboard = [[
        InlineKeyboardButton(
            text="Open Prep Academy",
            web_app=WebAppInfo(url=APP_URL)
        )
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(welcome, reply_markup=reply_markup)

    # Save user
    _db = get_db()
    chat_id = str(update.effective_chat.id)
    await _db.telegram_users.update_one(
        {"chat_id": chat_id},
        {"$set": {"chat_id": chat_id, "username": update.effective_user.username or "",
                  "first_name": update.effective_user.first_name or "",
                  "joined_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True
    )


async def send_question(update_or_chat_id, context, chat_id=None):
    """Send a random MCQ question"""
    _db = get_db()
    if chat_id is None:
        chat_id = update_or_chat_id.effective_chat.id

    pipeline = [
        {"$sample": {"size": 1}},
        {"$project": {"_id": 0, "id": 1, "question_text_de": 1, "question_text": 1,
                      "choices": 1, "explanation_de": 1, "specialty_id": 1}}
    ]
    questions = await _db.questions.aggregate(pipeline).to_list(1)
    if not questions:
        await context.bot.send_message(chat_id=chat_id, text="Keine Fragen verfügbar.")
        return

    q = questions[0]
    text = q.get("question_text_de") or q.get("question_text", "")
    choices = q.get("choices", [])

    # Build message
    msg = f"📋 *Frage:*\n{text}\n\n"
    labels = ["A", "B", "C", "D", "E"]
    keyboard = []
    for i, c in enumerate(choices[:5]):
        label = labels[i] if i < len(labels) else str(i + 1)
        choice_text = c.get("text_de") or c.get("text", "")
        msg += f"*{label})* {choice_text}\n"
        is_correct = "1" if c.get("is_correct") else "0"
        keyboard.append([InlineKeyboardButton(
            f"{label}", callback_data=f"ans:{q['id']}:{c.get('id', i)}:{is_correct}"
        )])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode="Markdown", reply_markup=reply_markup)


async def frage_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /frage command"""
    await send_question(update, context)


async def quiz_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /quiz - send 5 questions"""
    await update.message.reply_text("📝 *Quiz gestartet!* 5 Fragen kommen...\n", parse_mode="Markdown")
    for i in range(5):
        await send_question(update, context)
        if i < 4:
            await asyncio.sleep(1)


async def answer_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle answer button press"""
    query = update.callback_query
    await query.answer()

    data = query.data.split(":")
    if len(data) < 4:
        return

    _, q_id, choice_id, is_correct = data
    correct = is_correct == "1"

    _db = get_db()
    chat_id = str(query.message.chat_id)

    # Track stats
    await _db.telegram_stats.update_one(
        {"chat_id": chat_id},
        {"$inc": {"total": 1, "correct": 1 if correct else 0}},
        upsert=True
    )

    if correct:
        response = "✅ *Richtig!* Gut gemacht!"
    else:
        # Get correct answer
        q = await _db.questions.find_one({"id": q_id}, {"_id": 0, "choices": 1, "explanation_de": 1})
        correct_text = ""
        if q:
            for c in q.get("choices", []):
                if c.get("is_correct"):
                    correct_text = c.get("text_de") or c.get("text", "")
                    break
        response = f"❌ *Falsch!*\n✅ Richtige Antwort: {correct_text}"
        if q and q.get("explanation_de"):
            response += f"\n\n💡 {q['explanation_de'][:300]}"

    await query.edit_message_reply_markup(reply_markup=None)
    await context.bot.send_message(chat_id=query.message.chat_id, text=response, parse_mode="Markdown")


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /stats command"""
    _db = get_db()
    chat_id = str(update.effective_chat.id)
    stats = await _db.telegram_stats.find_one({"chat_id": chat_id}, {"_id": 0})

    if not stats or stats.get("total", 0) == 0:
        await update.message.reply_text("Du hast noch keine Fragen beantwortet. Tippe /frage!")
        return

    total = stats.get("total", 0)
    correct = stats.get("correct", 0)
    accuracy = round(correct / total * 100, 1) if total > 0 else 0

    msg = (
        f"📊 *Deine Statistiken:*\n\n"
        f"Gesamt: {total} Fragen\n"
        f"Richtig: {correct} ✅\n"
        f"Falsch: {total - correct} ❌\n"
        f"Genauigkeit: {accuracy}%\n\n"
        f"Weiter so! Tippe /frage für mehr."
    )
    await update.message.reply_text(msg, parse_mode="Markdown")


async def hilfe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /hilfe command"""
    msg = (
        "🎓 *Prep Academy Bot - Befehle:*\n\n"
        "/start - Bot starten\n"
        "/frage - Eine zufällige Frage\n"
        "/quiz - 5 Fragen Quiz\n"
        "/stats - Deine Statistiken\n"
        "/hilfe - Diese Hilfe\n\n"
        "Drücke einfach auf A/B/C/D/E um zu antworten!"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")


async def _error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Swallow Conflict and common polling errors silently."""
    err = context.error
    if err is None:
        return
    msg = str(err)
    if "Conflict" in msg or "getUpdates" in msg:
        return  # expected when another instance is polling
    logger.warning(f"Telegram bot error: {err}")


def create_bot_app():
    """Create and configure the bot application"""
    token = get_token()
    if not token:
        logger.warning("TELEGRAM_BOT_TOKEN not set - bot disabled")
        return None

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("frage", frage_command))
    app.add_handler(CommandHandler("quiz", quiz_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("hilfe", hilfe_command))
    app.add_handler(CallbackQueryHandler(answer_callback, pattern=r"^ans:"))
    app.add_error_handler(_error_handler)
    return app


async def start_bot():
    """Start the Telegram bot in polling mode with lock to prevent duplicates"""
    import asyncio as _asyncio
    import fcntl
    
    # File lock to prevent duplicate bot instances (uvicorn reloader spawns 2 processes)
    lock_file = "/tmp/telegram_bot.lock"
    try:
        lock_fd = open(lock_file, "w")
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except (IOError, OSError):
        logger.info("Another bot instance already running, skipping...")
        return
    
    await _asyncio.sleep(2)
    
    bot_app = create_bot_app()
    if bot_app is None:
        return
    
    try:
        logger.info("Starting Telegram bot...")
        await bot_app.initialize()
        await bot_app.start()
        await bot_app.updater.start_polling(drop_pending_updates=True)
        logger.info("Telegram bot started successfully")
    except Exception as e:
        logger.warning(f"Telegram bot start failed: {e}")


async def stop_bot():
    """Stop the Telegram bot"""
    bot_app = create_bot_app()
    if bot_app:
        await bot_app.updater.stop()
        await bot_app.stop()
        await bot_app.shutdown()
