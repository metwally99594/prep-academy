"""
Community Service — validators, ranking, trending, duplicate detection.

Pure functions with no DB calls.
"""
import html
import re
import time
from typing import Optional


# ── Content validation ──

MAX_TITLE_LENGTH = 200
MAX_CONTENT_LENGTH = 10000
MAX_COMMENT_LENGTH = 5000

VALID_POST_TYPES = {"question", "discussion", "case_study", "resource"}
VALID_REPORT_REASONS = {"spam", "inappropriate", "misinformation", "harassment", "off_topic", "other"}
VALID_REACTIONS = {"upvote", "downvote"}
VALID_TARGET_TYPES = {"post", "comment"}
VALID_SORT_OPTIONS = {"recent", "trending", "top", "discussed"}
VALID_MODERATION_ACTIONS = {"approve", "hide", "delete", "queue"}

KNOWN_SPECIALTIES: set[str] = {
    "cardiology", "radiology", "neurology", "pediatrics", "surgery",
    "internal_medicine", "orthopedics", "dermatology", "ophthalmology",
    "gynecology", "urology", "psychiatry", "emergency_medicine",
    "anesthesiology", "pathology", "pharmacology", "microbiology",
    "public_health", "anatomy", "physiology", "biochemistry",
}

KNOWN_TOPICS: set[str] = {
    "diagnosis", "treatment", "guidelines", "case_report",
    "exam_prep", "study_tips", "research", "clinical_skills",
    "medical_education", "career", "technology", "ethics",
}


def validate_post_content(title: str, content: str) -> list[str]:
    errors: list[str] = []
    stripped_title = title.strip()
    stripped_content = content.strip()
    if not stripped_title:
        errors.append("Title cannot be empty")
    elif len(stripped_title) > MAX_TITLE_LENGTH:
        errors.append(f"Title exceeds {MAX_TITLE_LENGTH} characters")
    if not stripped_content:
        errors.append("Content cannot be empty")
    elif len(stripped_content) > MAX_CONTENT_LENGTH:
        errors.append(f"Content exceeds {MAX_CONTENT_LENGTH} characters")
    return errors


def validate_comment_content(content: str) -> Optional[str]:
    stripped = content.strip()
    if not stripped:
        return "Comment cannot be empty"
    if len(stripped) > MAX_COMMENT_LENGTH:
        return f"Comment exceeds {MAX_COMMENT_LENGTH} characters"
    return None


def validate_post_type(post_type: str) -> Optional[str]:
    if post_type not in VALID_POST_TYPES:
        return f"Invalid post type '{post_type}' — must be one of {', '.join(sorted(VALID_POST_TYPES))}"
    return None


def validate_specialty_tags(tags: list[str]) -> list[str]:
    errors: list[str] = []
    for tag in tags:
        if tag not in KNOWN_SPECIALTIES:
            errors.append(f"Unknown specialty tag '{tag}'")
    return errors


def validate_topic_tags(tags: list[str]) -> list[str]:
    errors: list[str] = []
    for tag in tags:
        if tag not in KNOWN_TOPICS:
            errors.append(f"Unknown topic tag '{tag}'")
    return errors


def validate_reason(reason: str) -> Optional[str]:
    if reason not in VALID_REPORT_REASONS:
        return f"Invalid report reason '{reason}'"
    return None


def validate_reaction(reaction: str) -> Optional[str]:
    if reaction not in VALID_REACTIONS:
        return f"Invalid reaction '{reaction}'"
    return None


def validate_target_type(target_type: str) -> Optional[str]:
    if target_type not in VALID_TARGET_TYPES:
        return f"Invalid target type '{target_type}'"
    return None


def validate_sort_option(sort: str) -> Optional[str]:
    if sort not in VALID_SORT_OPTIONS:
        return f"Invalid sort option '{sort}'"
    return None


def validate_moderation_action(action: str) -> Optional[str]:
    if action not in VALID_MODERATION_ACTIONS:
        return f"Invalid moderation action '{action}'"
    return None


# ── HTML / safety sanitization ──

_HAS_HTML_RE = re.compile(r"<[a-z][\s\S]*>", re.IGNORECASE)


def contains_html(text: str) -> bool:
    return bool(_HAS_HTML_RE.search(text))


def sanitize_html(text: str) -> str:
    return html.escape(text.strip())


# ── Duplicate detection (simple text similarity) ──

def compute_text_similarity(a: str, b: str) -> float:
    """Jaccard similarity on word sets."""
    words_a = set(a.lower().split())
    words_b = set(b.lower().split())
    if not words_a or not words_b:
        return 0.0
    intersection = words_a & words_b
    union = words_a | words_b
    return len(intersection) / len(union)


def is_duplicate(new_title: str, new_content: str, existing_title: str, existing_content: str) -> bool:
    title_sim = compute_text_similarity(new_title, existing_title)
    content_sim = compute_text_similarity(
        (new_title + " " + new_content)[:500],
        (existing_title + " " + existing_content)[:500],
    )
    return title_sim > 0.8 or content_sim > 0.6


# ── Ranking / trending logic ──

def compute_hot_score(upvotes: int, downvotes: int, created_at_epoch: float) -> float:
    """Reddit-style hot score: log(score) + age_decay."""
    score = upvotes - downvotes
    if score <= 0:
        return 0.0
    import math
    age_hours = (time.time() - created_at_epoch) / 3600
    return round(math.log10(max(score, 1)) + (score / (age_hours + 2)), 4)


def compute_trending_score(
    recent_views: int,
    recent_upvotes: int,
    recent_comments: int,
    hours_since_post: float,
) -> float:
    """Velocity-based trending: engagement per hour, decaying with age."""
    if hours_since_post < 0.01:
        hours_since_post = 0.01
    engagement = (recent_views * 0.01) + (recent_upvotes * 2) + (recent_comments * 3)
    return round(engagement / hours_since_post, 4)


# ── Medical safety checks ──

_PHI_PATTERNS: list[re.Pattern] = [
    re.compile(r"\b\d{3}\s*-\s*\d{2}\s*-\s*\d{4}\b"),            # SSN
    re.compile(r"\b(?:patient(?:en)?(?:name|id|nummer)|fall(?:nummer)?)\s*:?\s*\w+\b", re.IGNORECASE),
    re.compile(r"\b(?:geb(?:urtsdatum)?|date\s*of\s*birth|dob)\s*:?\s*\d{1,2}[./]\d{1,2}[./]\d{2,4}\b", re.IGNORECASE),
]

_DANGEROUS_ADVICE_PATTERNS: list[re.Pattern] = [
    re.compile(r"(?:empfehle|raten?\s*zu|sollten?\s*sie)[,\s]*(?:kein(?:en?|e)\s*)?(?:arzt|behandlung|therapie|medikament)\s*(?:aufzusuchen|zu\s*konsultieren)?", re.IGNORECASE),
]


def check_phi(text: str) -> list[str]:
    findings: list[str] = []
    for pattern in _PHI_PATTERNS:
        match = pattern.search(text)
        if match:
            findings.append(f"Possible PHI detected: '{match.group()[:40]}'")
    return findings


def check_dangerous_advice(text: str) -> list[str]:
    findings: list[str] = []
    for pattern in _DANGEROUS_ADVICE_PATTERNS:
        match = pattern.search(text)
        if match:
            findings.append(f"Potentially dangerous advice: '{match.group()[:60]}'")
    return findings


# ── In-memory rate limiting (per-user post frequency) ──

_post_rate_store: dict[str, list[float]] = {}
POST_RATE_LIMIT = 5
POST_RATE_WINDOW = 300  # 5 minutes
COMMENT_RATE_LIMIT = 20
COMMENT_RATE_WINDOW = 300


def check_post_rate(user_id: str) -> Optional[str]:
    now = time.time()
    start = now - POST_RATE_WINDOW
    timestamps = _post_rate_store.get(user_id, [])
    timestamps = [t for t in timestamps if t > start]
    if len(timestamps) >= POST_RATE_LIMIT:
        return "Post rate limit exceeded — max 5 posts per 5 minutes"
    timestamps.append(now)
    _post_rate_store[user_id] = timestamps
    return None


def check_comment_rate(user_id: str) -> Optional[str]:
    now = time.time()
    start = now - COMMENT_RATE_WINDOW
    timestamps = _post_rate_store.get(f"comment:{user_id}", [])
    timestamps = [t for t in timestamps if t > start]
    if len(timestamps) >= COMMENT_RATE_LIMIT:
        return "Comment rate limit exceeded — max 20 comments per 5 minutes"
    timestamps.append(now)
    _post_rate_store[f"comment:{user_id}"] = timestamps
    return None
