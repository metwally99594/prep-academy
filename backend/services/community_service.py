"""
Community Service — validators, ranking, trending, duplicate detection,
reaction toggle, DB helpers.

Pure functions with no DB calls except where explicitly noted.
"""
import html
import re
import time
import uuid
from datetime import datetime, timezone
from typing import Optional
from pymongo.errors import DuplicateKeyError


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


async def find_duplicate_post(db, title: str, content: str) -> Optional[str]:
    """Check if content is a duplicate of a recent published post. Returns duplicate ID or None."""
    similar = await db.community_posts.find(
        {"status": "published"}
    ).sort("created_at", -1).limit(20).to_list(length=20)
    for existing in similar:
        if is_duplicate(title, content, existing.get("title", ""), existing.get("content", "")):
            return existing["id"]
    return None


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


# ── Anti-spam burst protection (rapid-fire detection) ──

_burst_store: dict[str, list[float]] = {}
BURST_LIMIT = 5
BURST_WINDOW = 60  # 1 minute


def check_burst_rate(user_id: str, kind: str = "post") -> Optional[str]:
    """Detect rapid-fire spam: more than BURST_LIMIT actions within BURST_WINDOW seconds."""
    now = time.time()
    start = now - BURST_WINDOW
    key = f"burst:{kind}:{user_id}"
    timestamps = _burst_store.get(key, [])
    timestamps = [t for t in timestamps if t > start]
    if len(timestamps) >= BURST_LIMIT:
        return "Burst rate limit exceeded — too many actions in a short period"
    timestamps.append(now)
    _burst_store[key] = timestamps
    return None


# ── @mention extraction ──

_MENTION_RE = re.compile(r"@(\w[\w.-]+)")


def extract_mentions(text: str) -> list[str]:
    """Extract @username mentions from text (without the @)."""
    return _MENTION_RE.findall(text)


# ── Cursor pagination helpers ──

SORT_CONFIG = {
    "recent": {"field": "created_at", "coerce": str},
    "trending": {"field": "created_at", "coerce": str},
    "top": {"field": "stats.score", "coerce": float},
    "discussed": {"field": "stats.comment_count", "coerce": int},
}


def get_sort_config(sort: str) -> dict:
    return SORT_CONFIG.get(sort, SORT_CONFIG["recent"])


def get_sort_spec(sort_field: str) -> list:
    return [(sort_field, -1), ("_id", 1)]


def parse_cursor(cursor: Optional[str], coerce_func) -> Optional[any]:
    if cursor is None or cursor == "":
        return None
    try:
        return coerce_func(cursor)
    except (ValueError, TypeError):
        return None


# ── Feed enrichment helpers ──

FEED_PROJECTION = {
    "_id": 1, "id": 1, "author_id": 1, "title": 1, "content": 1,
    "specialty_tags": 1, "topic_tags": 1, "type": 1, "status": 1,
    "stats": 1, "image_ids": 1, "is_duplicate": 1, "duplicate_of": 1,
    "created_at": 1, "updated_at": 1,
}


async def batch_load_author_names(author_ids: list[str]) -> dict[str, str]:
    """Load author names in batch, returns dict of author_id -> name."""
    from database import db
    author_names: dict[str, str] = {}
    if not author_ids:
        return author_names
    user_cursor = db.users.find({"id": {"$in": author_ids}}, {"name": 1, "id": 1})
    async for user_doc in user_cursor:
        author_names[user_doc["id"]] = user_doc.get("name", "Unknown")
    return author_names


def enrich_post_response(p: dict, author_name: str) -> dict:
    """Build a CommunityPostResponse-compatible dict from a post document."""
    from models import CommunityPostResponse
    return CommunityPostResponse(
        id=p.get("id", ""),
        author_id=p.get("author_id", ""),
        author_name=author_name,
        title=p.get("title", ""),
        content=p.get("content", ""),
        content_html=p.get("content_html"),
        specialty_tags=p.get("specialty_tags", []),
        topic_tags=p.get("topic_tags", []),
        type=p.get("type", "discussion"),
        status=p.get("status", "published"),
        stats=p.get("stats", {}),
        image_ids=p.get("image_ids", []),
        is_duplicate=p.get("is_duplicate", False),
        duplicate_of=p.get("duplicate_of"),
        ai_summary=p.get("ai_summary"),
        educational_safety_approved=p.get("educational_safety_approved", False),
        created_at=p.get("created_at", ""),
        updated_at=p.get("updated_at", ""),
    )


def enrich_comment_response(c: dict, author_name: str) -> dict:
    """Build a CommunityCommentResponse-compatible dict from a comment document."""
    from models import CommunityCommentResponse
    return CommunityCommentResponse(
        id=c.get("id", ""),
        post_id=c.get("post_id", ""),
        parent_id=c.get("parent_id"),
        author_id=c.get("author_id", ""),
        author_name=author_name,
        content=c.get("content", ""),
        status=c.get("status", "published"),
        stats=c.get("stats", {}),
        created_at=c.get("created_at", ""),
        updated_at=c.get("updated_at", ""),
    )


# ── Reaction toggle (DB-backed, uses db) ──


async def handle_reaction_toggle(
    user_id: str,
    target_type: str,
    target_id: str,
    reaction: str,
) -> dict:
    """
    Toggle a reaction (upvote/downvote) on a post or comment.

    Handles:
      - Removing reaction if same reaction clicked again
      - Switching between upvote/downvote
      - DuplicateKeyError race condition on concurrent first-reaction inserts

    Returns dict with:
      delta, score_delta, inc_field, had_race, target_author_id
    """
    from database import db

    reaction_value = 1 if reaction == "upvote" else -1
    score_field = "upvote_count" if reaction == "upvote" else "downvote_count"

    collection = db.community_posts if target_type == "post" else db.community_comments
    target = await collection.find_one({"id": target_id}, {"author_id": 1})
    if not target:
        return {"delta": 0, "score_delta": 0, "inc_field": score_field, "had_race": False, "target_author_id": None, "found": False}
    target_author_id = target["author_id"]

    existing = await db.community_reactions.find_one({
        "user_id": user_id, "target_type": target_type, "target_id": target_id,
    })

    delta = 0
    score_delta = 0
    inc_field = score_field
    had_race = False

    if existing:
        if existing["reaction"] == reaction:
            await db.community_reactions.delete_one({"id": existing["id"]})
            delta = -reaction_value
            score_delta = -reaction_value
        else:
            old_score_field = "upvote_count" if existing["reaction"] == "upvote" else "downvote_count"
            await db.community_reactions.update_one(
                {"id": existing["id"]},
                {"$set": {"reaction": reaction}},
            )
            delta = reaction_value
            score_delta = reaction_value * 2
            inc_field = score_field
            await collection.update_one(
                {"id": target_id},
                {"$inc": {f"stats.{old_score_field}": -1, "stats.score": -reaction_value if existing["reaction"] == "upvote" else 1}},
            )
    else:
        try:
            await db.community_reactions.insert_one({
                "id": uuid.uuid4().hex,
                "user_id": user_id,
                "target_type": target_type,
                "target_id": target_id,
                "reaction": reaction,
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
            delta = reaction_value
            score_delta = reaction_value
        except DuplicateKeyError:
            had_race = True
            existing = await db.community_reactions.find_one({
                "user_id": user_id, "target_type": target_type, "target_id": target_id,
            })
            if existing and existing["reaction"] == reaction:
                await db.community_reactions.delete_one({"id": existing["id"]})
                delta = -reaction_value
                score_delta = -reaction_value
            else:
                delta = 0
                score_delta = 0

    await collection.update_one(
        {"id": target_id},
        {"$inc": {f"stats.{inc_field}": delta, "stats.score": score_delta}},
    )

    return {
        "delta": delta,
        "score_delta": score_delta,
        "inc_field": inc_field,
        "had_race": had_race,
        "target_author_id": target_author_id,
        "found": True,
    }


# ── DB helpers (extracted from routes) ──


async def get_user_name(user_id: str) -> str:
    """Fetch a user's display name by id."""
    from database import db
    user = await db.users.find_one({"id": user_id}, {"name": 1})
    return user.get("name", "Unknown") if user else "Unknown"


async def get_post_or_404(post_id: str) -> dict:
    """Fetch a post by id or raise HTTPException 404."""
    from fastapi import HTTPException
    from database import db
    post = await db.community_posts.find_one({"id": post_id})
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return post


async def get_comment_or_404(comment_id: str) -> dict:
    """Fetch a comment by id or raise HTTPException 404."""
    from fastapi import HTTPException
    from database import db
    comment = await db.community_comments.find_one({"id": comment_id})
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    return comment


def visible_status_filter(user: dict) -> dict:
    """Build status filter: admins see all, regular users see published only."""
    if user.get("is_admin"):
        return {}
    return {"status": {"$in": ["published"]}}


def build_feed_query(
    specialty: Optional[str] = None,
    topic: Optional[str] = None,
    post_type: Optional[str] = None,
    search: Optional[str] = None,
) -> dict:
    """Build a MongoDB query dict for the community feed."""
    query = {"status": "published"}
    if specialty:
        query["specialty_tags"] = specialty
    if topic:
        query["topic_tags"] = topic
    if post_type:
        query["type"] = post_type
    if search:
        query["$text"] = {"$search": search}
    return query

