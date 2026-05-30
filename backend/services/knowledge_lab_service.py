"""Knowledge Lab service — file I/O, markdown parsing, search index."""

import os
import re
import time
from pathlib import Path
from typing import Optional

# Path to knowledge/wiki relative to this file (backend/services/ -> project root -> knowledge/wiki)
_WIKI_DIR = Path(__file__).resolve().parent.parent.parent / "knowledge" / "wiki"
_INDEX_CACHE = None
_INDEX_MTIME = 0
_INDEX_TTL = 60  # seconds before re-checking mtime


def _get_wiki_path() -> Path:
    """Return the wiki directory, falling back to env var if set."""
    env_path = os.environ.get("KNOWLEDGE_WIKI_DIR")
    if env_path:
        return Path(env_path)
    return _WIKI_DIR


# ── Category detection ────────────────────────────────────────────

_CONCEPT_PATHS = {
    "diagnostik", "biostatistik", "klinische-untersuchung", "praevention",
}
_LICENSING_PATHS = {"nostrifikation"}
_SOURCE_PREFIX = "sources/"


def _detect_category(path: str) -> str:
    if path.startswith(_SOURCE_PREFIX):
        return "source"
    if path in _LICENSING_PATHS:
        return "licensing"
    if path in _CONCEPT_PATHS:
        return "concept"
    return "specialty"


# ── File discovery ────────────────────────────────────────────────

def discover_pages():
    """Walk wiki/ and return metadata for every .md file."""
    wiki = _get_wiki_path()
    if not wiki.is_dir():
        return []

    pages = []
    for md_file in sorted(wiki.rglob("*.md")):
        rel = md_file.relative_to(wiki)
        path = str(rel.with_suffix("")).replace("\\", "/")
        title = _extract_title(md_file)
        mtime = md_file.stat().st_mtime
        pages.append({
            "path": path,
            "title": title or path.split("/")[-1].replace("-", " ").title(),
            "category": _detect_category(path),
            "last_modified": mtime,
        })
    return pages


def _extract_title(filepath: Path) -> Optional[str]:
    """Read the first # heading as the page title."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("# ") and not line.startswith("## "):
                    return line[2:].strip()
    except Exception:
        pass
    return None


# ── Page content ──────────────────────────────────────────────────

def get_page(path: str):
    """Return full page data: content, metadata, related, sources."""
    wiki = _get_wiki_path()
    filepath = wiki / f"{path}.md"
    if not filepath.is_file():
        return None

    try:
        raw = filepath.read_text(encoding="utf-8")
    except Exception:
        return None

    title = _extract_title(filepath) or path.split("/")[-1].replace("-", " ").title()
    related = _extract_related(raw)
    sources = _extract_sources(raw)
    word_count = len(raw.split())
    mtime = filepath.stat().st_mtime

    return {
        "path": path,
        "title": title,
        "content": raw,
        "related_pages": related,
        "sources": sources,
        "category": _detect_category(path),
        "last_modified": mtime,
        "word_count": word_count,
    }


_RE_RELATED = re.compile(
    r'^##\s*Related Pages\s*$.*?(?=^##\s|\Z)',
    re.MULTILINE | re.DOTALL,
)


def _extract_related(raw: str) -> list:
    """Parse the ## Related Pages section for markdown links."""
    match = _RE_RELATED.search(raw)
    if not match:
        return []

    section = match.group(0)
    links = re.findall(
        r'\[([^\]]+)\]\(([^)]+\.md)\)\s*[—\-–]\s*(.+)',
        section,
    )
    result = []
    for title, target, desc in links:
        target_path = target.replace(".md", "").replace("../", "").replace("wiki/", "")
        result.append({
            "title": title,
            "path": target_path,
            "description": desc.strip(),
        })
    return result


def _extract_sources(raw: str) -> list:
    """Parse source references from the content."""
    sources = []
    # Pattern 1: **Sources:** [title](path)
    pattern1 = re.findall(r'\*\*Sources?:\*\*\s*\[([^\]]+)\]\(([^)]+)\)', raw)
    for title, target in pattern1:
        target_path = target.replace(".md", "").replace("../", "")
        sources.append({"title": title, "path": target_path})

    # Pattern 2: `**Source:** knowledge/raw/...` in source summary pages
    pattern2 = re.findall(r'\*\*Source:\*\*\s*`([^`]+)`', raw)
    for raw_ref in pattern2:
        sources.append({"title": raw_ref, "path": raw_ref})

    return sources


# ── Search index ──────────────────────────────────────────────────

def _check_stale():
    """Return True if the cache is stale based on wiki dir mtime."""
    wiki = _get_wiki_path()
    if not wiki.is_dir():
        return True
    current = max(
        (p.stat().st_mtime for p in wiki.rglob("*.md")),
        default=0,
    )
    return current > _INDEX_MTIME + 0.01  # small tolerance


def build_index(force=False):
    """Build or rebuild the in-memory search index."""
    global _INDEX_CACHE, _INDEX_MTIME
    if not force and _INDEX_CACHE is not None and not _check_stale():
        return _INDEX_CACHE

    pages = discover_pages()
    index = []
    for meta in pages:
        page_data = get_page(meta["path"])
        if page_data is None:
            continue
        content_lower = page_data.get("content", "").lower()
        index.append({
            "path": meta["path"],
            "title": meta["title"],
            "title_lower": meta["title"].lower(),
            "content": content_lower,
            "raw_snippet": page_data.get("content", ""),
            "category": meta["category"],
            "word_count": page_data.get("word_count", 0),
        })

    _INDEX_CACHE = index
    wiki = _get_wiki_path()
    _INDEX_MTIME = max(
        (p.stat().st_mtime for p in wiki.rglob("*.md")),
        default=time.time(),
    )
    return _INDEX_CACHE


def search(query: str, limit: int = 20):
    """Full-text keyword search over the index. Returns scored results."""
    if not query or not query.strip():
        return []

    index = build_index()
    tokens = re.findall(r"[a-zA-ZäöüßÄÖÜ0-9\-]+", query.lower())

    scored = []
    for page in index:
        score = 0
        matched_tokens = set()
        for token in tokens:
            if token in page["title_lower"]:
                score += 10
                matched_tokens.add(token)
            count = page["content"].count(token)
            if count:
                score += count * 2
                matched_tokens.add(token)

        if score > 0:
            snippet = _make_snippet(page["raw_snippet"], query, 150)
            scored.append({
                "path": page["path"],
                "title": page["title"],
                "snippet": snippet,
                "score": score,
                "category": page["category"],
                "word_count": page["word_count"],
                "matched_tokens": len(matched_tokens),
            })

    scored.sort(key=lambda x: (-x["score"], -x["matched_tokens"]))
    return scored[:limit]


def _make_snippet(content: str, query: str, context_chars: int = 120) -> str:
    """Extract a snippet around the first occurrence of any query term."""
    lower = content.lower()
    q_lower = query.lower()
    idx = lower.find(q_lower)
    if idx == -1:
        # Try first word of query
        first_word = re.findall(r"\w+", q_lower)
        if first_word:
            idx = lower.find(first_word[0])

    if idx == -1:
        return content[:context_chars] + "..." if len(content) > context_chars else content

    start = max(0, idx - context_chars // 2)
    end = min(len(content), idx + len(q_lower) + context_chars // 2)
    snippet = content[start:end].replace("\n", " ").strip()
    if start > 0:
        snippet = "..." + snippet
    if end < len(content):
        snippet = snippet + "..."
    return snippet


# ── Stats ─────────────────────────────────────────────────────────

def get_stats():
    """Return KB statistics."""
    pages = discover_pages()
    total = len(pages)

    category_counts = {}
    word_count_total = 0
    last_updated = 0
    for p in pages:
        cat = p["category"]
        category_counts[cat] = category_counts.get(cat, 0) + 1

        data = get_page(p["path"])
        if data:
            word_count_total += data["word_count"]
            if data["last_modified"] > last_updated:
                last_updated = data["last_modified"]

    return {
        "total_pages": total,
        "categories": category_counts,
        "total_words": word_count_total,
        "last_updated": last_updated,
        "source_count": category_counts.get("source", 0),
        "specialty_count": category_counts.get("specialty", 0),
        "concept_count": category_counts.get("concept", 0),
    }
