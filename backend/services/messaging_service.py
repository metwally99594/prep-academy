"""
Messaging Service — validators, rate limiting, spam prevention, helpers.

Pure functions + in-memory rate-limit tracking.
No DB calls — callers own the DB interactions.
"""
import html
import re
import time
from typing import Optional

# ── Attachment validation ──

ALLOWED_MIME_TYPES: set[str] = {
    "image/jpeg", "image/png", "image/gif", "image/webp",
    "video/mp4", "video/webm", "video/quicktime",
    "application/pdf",
}
MAX_ATTACHMENTS_PER_MESSAGE = 5
MAX_ATTACHMENT_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


def validate_attachments(attachments: list[dict]) -> list[str]:
    errors: list[str] = []
    if len(attachments) > MAX_ATTACHMENTS_PER_MESSAGE:
        errors.append(f"Max {MAX_ATTACHMENTS_PER_MESSAGE} attachments per message")
        return errors
    for i, att in enumerate(attachments):
        mime = att.get("mime_type", "")
        size = att.get("size_bytes", 0)
        if mime and mime not in ALLOWED_MIME_TYPES:
            errors.append(f"Attachment {i}: unsupported type '{mime}'")
        if size > MAX_ATTACHMENT_SIZE_BYTES:
            errors.append(f"Attachment {i}: exceeds 10 MB")
    return errors


# ── Content validation ──

MAX_CONTENT_LENGTH = 5000
MIN_CONTENT_LENGTH = 1


def validate_message_content(content: str, has_attachments: bool = False) -> Optional[str]:
    stripped = content.strip()
    if not stripped and not has_attachments:
        return "Message content cannot be empty"
    if len(stripped) > MAX_CONTENT_LENGTH:
        return f"Message content exceeds {MAX_CONTENT_LENGTH} characters"
    return None


def sanitize_message_content(content: str) -> str:
    return html.escape(content.strip())


# ── Rate limiting (in-memory) ──

_rate_limit_store: dict[str, list[float]] = {}
RATE_LIMIT_MAX_MESSAGES = 10
RATE_LIMIT_WINDOW_SECONDS = 60


def check_rate_limit(user_id: str) -> Optional[str]:
    now = time.time()
    window_start = now - RATE_LIMIT_WINDOW_SECONDS
    timestamps = _rate_limit_store.get(user_id, [])
    timestamps = [t for t in timestamps if t > window_start]
    if len(timestamps) >= RATE_LIMIT_MAX_MESSAGES:
        return "Rate limit exceeded — max 10 messages per minute"
    timestamps.append(now)
    _rate_limit_store[user_id] = timestamps
    return None


# ── Spam detection (simple) ──

SPAM_HOUR_LIMIT = 50
SPAM_HOUR_WINDOW = 3600
_spam_store: dict[str, list[float]] = {}


def check_spam_rate(user_id: str) -> Optional[str]:
    now = time.time()
    window_start = now - SPAM_HOUR_WINDOW
    timestamps = _spam_store.get(user_id, [])
    timestamps = [t for t in timestamps if t > window_start]
    if len(timestamps) >= SPAM_HOUR_LIMIT:
        return "Spam limit exceeded — max 50 messages per hour"
    timestamps.append(now)
    _spam_store[user_id] = timestamps
    return None


# ── Duplicate detection (recent same content) ──

_duplicate_store: dict[str, tuple[str, float]] = {}
DUP_WINDOW_SECONDS = 60


def check_duplicate_content(user_id: str, content: str) -> Optional[str]:
    stripped = content.strip().lower()
    now = time.time()
    prev = _duplicate_store.get(user_id)
    if prev and prev[0] == stripped and (now - prev[1]) < DUP_WINDOW_SECONDS:
        return "Duplicate message — same content sent recently"
    _duplicate_store[user_id] = (stripped, now)
    return None


# ── Escalation helpers ──

ESCALATION_LABELS = {
    0: "none",
    1: "attention",
    2: "urgent",
    3: "critical",
}


def validate_escalation_level(level: int) -> Optional[str]:
    if level not in ESCALATION_LABELS:
        return f"Invalid escalation level: {level} (must be 0-3)"
    return None


# ── HTML detection ──

_HAS_HTML_RE = re.compile(r"<[a-z][\s\S]*>", re.IGNORECASE)


def contains_html(text: str) -> bool:
    return bool(_HAS_HTML_RE.search(text))
