import re
from typing import Optional

UMLAUT_MAP = {
    "ä": "ae",
    "ö": "oe",
    "ü": "ue",
    "Ä": "Ae",
    "Ö": "Oe",
    "Ü": "Ue",
    "ß": "ss",
}

_umlaut_pattern = re.compile("|".join(re.escape(k) for k in UMLAUT_MAP))


def normalize_umlauts(text: str) -> str:
    """Replace German umlauts: ä→ae, ö→oe, ü→ue, ß→ss."""
    return _umlaut_pattern.sub(lambda m: UMLAUT_MAP[m.group(0)], text)


def safe_regex_contains(text: str, query: str) -> bool:
    """Case-insensitive regex search with proper escaping. Handles special regex chars."""
    if not text or not query:
        return False
    escaped = re.escape(query)
    return bool(re.search(escaped, text, re.IGNORECASE))


def normalize_search_query(query: str) -> str:
    """Normalize a search query: strip, collapse whitespace, normalize umlauts."""
    if not query:
        return ""
    q = query.strip()
    q = re.sub(r"\s+", " ", q)
    return normalize_umlauts(q)
