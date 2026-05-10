"""
Community Search Service — query normalization, hashtag parsing, regex construction,
phrase matching, and projection building for community feed search.

Pure functions — no DB calls, no side effects.
"""
import re
from typing import Optional

from services.search_helpers import normalize_umlauts, safe_regex_contains

_HASHTAG_RE = re.compile(r"#(\w[\w-]*)")
_QUOTED_PHRASE_RE = re.compile(r'"([^"]+)"')


def parse_hashtags(text: str) -> list[str]:
    """Extract hashtags from text (without the # symbol)."""
    return _HASHTAG_RE.findall(text)


def parse_quoted_phrases(query: str) -> list[str]:
    """Extract quoted phrases from a search query."""
    return _QUOTED_PHRASE_RE.findall(query)


def normalize_search_input(query: Optional[str]) -> str:
    """Full normalization: strip, collapse spaces, normalize umlauts."""
    if not query:
        return ""
    return normalize_umlauts(re.sub(r"\s+", " ", query.strip()))


def build_regex_for_phrase(phrase: str) -> str:
    """Escape a phrase for safe regex matching. Handles special regex chars."""
    return re.escape(normalize_umlauts(phrase.strip()))


def build_mongo_text_search(query: str) -> Optional[dict]:
    """
    Build a MongoDB $text search query from a normalized query.
    Strips special characters that confuse MongoDB text indexes.
    Returns None if query is empty or too short.
    """
    normalized = normalize_search_input(query)
    if len(normalized) < 2:
        return None
    # Remove non-alphanumeric except spaces for text index
    clean = re.sub(r'[^\w\s]', ' ', normalized)
    clean = re.sub(r'\s+', ' ', clean).strip()
    if not clean:
        return None
    return {"$text": {"$search": clean}}


def build_hashtag_query(hashtags: list[str]) -> Optional[dict]:
    """Build a MongoDB query for hashtag search in content."""
    if not hashtags:
        return None
    patterns = [re.escape(f"#{h}") for h in hashtags]
    return {"content": {"$regex": "|".join(patterns), "$options": "i"}}


def build_phrase_query(phrases: list[str]) -> Optional[dict]:
    """Build a MongoDB regex query for quoted phrase matching."""
    if not phrases:
        return None
    patterns = [build_regex_for_phrase(p) for p in phrases]
    return {"$or": [
        {"title": {"$regex": p, "$options": "i"} for p in patterns},
        {"content": {"$regex": p, "$options": "i"} for p in patterns},
    ]}


FEED_SEARCH_PROJECTION = {
    "_id": 1, "id": 1, "author_id": 1, "title": 1, "content": 1,
    "specialty_tags": 1, "topic_tags": 1, "type": 1, "status": 1,
    "stats": 1, "image_ids": 1, "is_duplicate": 1, "duplicate_of": 1,
    "created_at": 1, "updated_at": 1,
}
