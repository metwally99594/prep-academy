"""Knowledge Lab service — file I/O, markdown parsing, search index."""

import os
import re
import time
import logging
from pathlib import Path
from typing import Optional

import yaml

logger = logging.getLogger(__name__)

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


# ── Frontmatter & wikilink parsing (Phase 2) ──────────────────────

_FRONTMATTER_PATTERN = re.compile(
    r'^---\s*\n(.*?)\n---\s*(?:\n|$)',
    re.DOTALL,
)
_WIKILINK_RE = re.compile(
    r'(?<!\\)(?<!!)\[\[([^\]|\n]+?)(?:\|([^\]\n]+?))?\]\]'
)
_FENCED_CODE_RE = re.compile(r'```[^\n]*\n.*?\n```', re.DOTALL)
_INLINE_CODE_RE = re.compile(r'`[^`\n]+?`')


def _strip_frontmatter(raw: str):
    """Strip a YAML frontmatter block from the top of a markdown string.

    Returns (frontmatter_dict, body). On missing or malformed frontmatter,
    returns ({}, raw). Tolerates a leading UTF-8 BOM.
    """
    if not raw:
        return {}, raw
    candidate = raw[1:] if raw.startswith('﻿') else raw
    if not candidate.startswith('---'):
        return {}, raw
    m = _FRONTMATTER_PATTERN.match(candidate)
    if not m:
        return {}, raw
    try:
        parsed = yaml.safe_load(m.group(1))
    except yaml.YAMLError as e:
        logger.warning(f"[knowledge_lab] Frontmatter parse error: {e}")
        return {}, raw
    if not isinstance(parsed, dict):
        if parsed is not None:
            logger.warning("[knowledge_lab] Frontmatter is not a dict; ignoring")
        return {}, raw
    body = candidate[m.end():].lstrip('\n')
    return parsed, body


def _mask_code(text: str):
    """Replace code regions with placeholders. Returns (masked, restore_fn)."""
    placeholders = []

    def store(match):
        idx = len(placeholders)
        placeholders.append(match.group(0))
        return f"\x00CB{idx}\x00"

    masked = _FENCED_CODE_RE.sub(store, text)
    masked = _INLINE_CODE_RE.sub(store, masked)

    def restore(s: str) -> str:
        for idx, original in enumerate(placeholders):
            s = s.replace(f"\x00CB{idx}\x00", original)
        return s

    return masked, restore


def _resolve_wikilinks(text: str) -> str:
    """Convert Obsidian [[wikilinks]] to standard markdown links.

    Skips fenced code blocks, inline code, escaped wikilinks (\\[[…]]),
    and embed syntax (![[…]]).
    """
    if not text or '[[' not in text:
        return text

    masked, restore = _mask_code(text)

    def replace(m):
        target = m.group(1).strip()
        display = (m.group(2) or '').strip()
        if not target:
            return m.group(0)
        if '#' in target:
            path_part, _, section = target.partition('#')
            section_slug = section.lower().replace(' ', '-')
            href = f"{path_part}.md#{section_slug}"
            label = display if display else target
        else:
            href = f"{target}.md"
            label = display if display else target
        return f"[{label}]({href})"

    resolved = _WIKILINK_RE.sub(replace, masked)
    return restore(resolved)


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
    """Use frontmatter title if present; else scan first # heading."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            raw = f.read()
        fm, body = _strip_frontmatter(raw)
        if fm.get("title"):
            return str(fm["title"]).strip()
        for line in body.splitlines():
            s = line.strip()
            if s.startswith("# ") and not s.startswith("## "):
                return s[2:].strip()
    except Exception:
        pass
    return None


# ── Page content ──────────────────────────────────────────────────

def get_page(path: str):
    """Return full page data: content, metadata, related, sources, properties."""
    wiki = _get_wiki_path()
    filepath = wiki / f"{path}.md"
    if not filepath.is_file():
        return None

    try:
        raw = filepath.read_text(encoding="utf-8")
    except Exception:
        return None

    properties, body = _strip_frontmatter(raw)
    body = _resolve_wikilinks(body)

    # Title: frontmatter > first H1 in body > path-derived
    fm_title = properties.get("title")
    if fm_title:
        title = str(fm_title).strip()
    else:
        title = None
        for line in body.splitlines():
            s = line.strip()
            if s.startswith("# ") and not s.startswith("## "):
                title = s[2:].strip()
                break
        if not title:
            title = path.split("/")[-1].replace("-", " ").title()

    related = _extract_related(body)
    sources = _extract_sources(body)
    word_count = len(body.split())
    mtime = filepath.stat().st_mtime

    return {
        "path": path,
        "title": title,
        "content": body,
        "related_pages": related,
        "sources": sources,
        "category": _detect_category(path),
        "last_modified": mtime,
        "word_count": word_count,
        "properties": properties,
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

_STOPWORDS = frozenset([
    "welche", "hat", "was", "sind", "ist", "die", "der", "das",
    "ein", "eine", "bei", "mit", "von", "für", "und", "oder",
    "wie", "wird", "dem", "den", "des", "auch", "nicht", "werden",
    "haben", "sein", "durch", "auf", "aus", "nach", "vor", "bis",
    "zum", "zur", "ins", "im", "am", "ans", "dass", "diese", "dieser",
    "dieses", "einen", "einer", "einem", "keine", "keinen", "keinem",
    "ihre", "ihrer", "ihren", "seinem", "seiner", "seinen", "seine",
    "sich", "ihn", "ihm", "uns", "euch", "ab", "an", "da", "dazu",
    "dann", "daran", "darauf", "darin", "darüber", "danach",
])

_DISEASE_SPECIALTY = {
    "parkinson": "neurologie",
    "schlaganfall": "neurologie",
    "apoplex": "neurologie",
    "demenz": "neurologie",
    "alzheimer": "neurologie",
    "epilepsie": "neurologie",
    "meningitis": "neurologie",
    "multiple": "neurologie",
    "sklerose": "neurologie",
    "demyelinisierend": "neurologie",
    "hypertonie": "kardiologie",
    "bluthochdruck": "kardiologie",
    "herzinsuffizienz": "kardiologie",
    "vorhofflimmern": "kardiologie",
    "stemi": "kardiologie",
    "nstemi": "kardiologie",
    "myokardinfarkt": "kardiologie",
    "herz": "kardiologie",
    "kardiologie": "kardiologie",
    "cor": "kardiologie",
    "copd": "pneumologie",
    "asthma": "pneumologie",
    "pneumonie": "pneumologie",
    "lunge": "pneumologie",
    "atemnot": "pneumologie",
    "tuberkulose": "pneumologie",
    "diabetes": "innere-medizin",
    "diabetisch": "innere-medizin",
    "schilddrüse": "innere-medizin",
    "thyreoidea": "innere-medizin",
    "osteoporose": "innere-medizin",
    "osteopenie": "innere-medizin",
    "gicht": "innere-medizin",
    "rheuma": "innere-medizin",
    "anämie": "innere-medizin",
    "gastroenterologie": "gastroenterologie",
    "gastro": "gastroenterologie",
    "reflux": "gastroenterologie",
    "ulkus": "gastroenterologie",
    "leber": "gastroenterologie",
    "pankreas": "gastroenterologie",
    "colitis": "gastroenterologie",
    "crohn": "gastroenterologie",
    "depression": "psychiatrie",
    "depressiv": "psychiatrie",
    "schizophrenie": "psychiatrie",
    "psychose": "psychiatrie",
    "sucht": "psychiatrie",
    "fraktur": "orthopaedie",
    "osteosynthese": "orthopaedie",
    "bandscheibe": "orthopaedie",
    "wirbel": "orthopaedie",
    "gynäkologie": "gynaekologie",
    "schwangerschaft": "gynaekologie",
    "prostata": "urologie",
    "niere": "urologie",
    "nieren": "urologie",
    "harn": "urologie",
    "hno": "hno",
    "hals": "hno",
    "nase": "hno",
    "ohr": "hno",
    "haut": "dermatologie",
    "dermatologie": "dermatologie",
    "ausschlag": "dermatologie",
    "ekzem": "dermatologie",
}

_MEDICAL_PHRASES = [
    "morbus parkinson",
    "morbus alzheimer",
    "morbus crohn",
    "multiple sklerose",
    "multiplen sklerose",
    "multipler sklerose",
    "arterielle hypertonie",
    "arteriellen hypertonie",
    "diabetes mellitus",
    "chronisch obstruktive lungenerkrankung",
    "koronare herzkrankheit",
    "periphere arterielle verschlusskrankheit",
    "colitis ulcerosa",
    "ulcus ventriculi",
    "benignes prostatasyndrom",
    "systemischer lupus erythematodes",
    "akutes koronarsyndrom",
    "tiefe beinvenenthrombose",
    "lungenembolie",
    "niereninsuffizienz",
    "leberzirrhose",
    "vorhofflimmern",
]


def _check_stale():
    """Return True if the cache is stale based on wiki dir mtime."""
    wiki = _get_wiki_path()
    if not wiki.is_dir():
        return True
    current = max(
        (p.stat().st_mtime for p in wiki.rglob("*.md")),
        default=0,
    )
    return current > _INDEX_MTIME + 0.01


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
            "headings": _extract_headings(content_lower),
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


def _extract_headings(content_lower: str) -> list:
    """Extract all markdown heading lines for heading-bonus scoring."""
    headings = []
    for line in content_lower.split("\n"):
        stripped = line.strip()
        if stripped.startswith("##") or stripped.startswith("# "):
            headings.append(stripped)
    return headings


def search(query: str, limit: int = 20):
    """Full-text keyword search with relevance improvements:
    - Stopword filtering
    - Multi-word medical phrase detection (big bonus)
    - Disease-to-specialty biasing (relevant specialty gets major boost)
    - Title boosting for meaningful tokens
    - Heading-occurrence bonus
    - Early-occurrence bonus
    """
    if not query or not query.strip():
        return []

    index = build_index()
    q_lower = query.lower()

    # 1. Tokenize and filter stopwords
    all_tokens = re.findall(r"[a-zA-ZäöüßÄÖÜ0-9\-]+", q_lower)
    tokens = [t for t in all_tokens if t not in _STOPWORDS]
    if not tokens:
        tokens = all_tokens  # fallback: use all if everything was stopped

    # 2. Detect medical phrases in query
    detected_phrases = [p for p in _MEDICAL_PHRASES if p in q_lower]

    # 3. Determine which specialties to boost based on medical terms in query
    boost_specialties = set()
    for token in tokens:
        if token in _DISEASE_SPECIALTY:
            boost_specialties.add(_DISEASE_SPECIALTY[token])
        else:
            # German compound word handling: e.g. "nierensteine" -> "niere"
            for term, specialty in _DISEASE_SPECIALTY.items():
                if len(term) >= 4 and term in token:
                    boost_specialties.add(specialty)
    for phrase in detected_phrases:
        if phrase in _DISEASE_SPECIALTY:
            boost_specialties.add(_DISEASE_SPECIALTY[phrase])
            for pt in phrase.split():
                if pt in _DISEASE_SPECIALTY:
                    boost_specialties.add(_DISEASE_SPECIALTY[pt])

    scored = []
    for page in index:
        score = 0
        matched_tokens = set()
        content = page["content"]
        title_lower = page["title_lower"]

        # Title boosting — meaningful tokens in title get 20 each
        for token in tokens:
            if token in title_lower:
                score += 20
                matched_tokens.add(token)

        # Content token frequency (meaningful tokens only)
        for token in tokens:
            count = content.count(token)
            if count:
                token_score = count * 2
                # Boost known medical terms in content
                if token in _DISEASE_SPECIALTY:
                    token_score += count * 2  # double score for medical terms
                score += token_score
                matched_tokens.add(token)

        # Phrase bonus — big boost when full multi-word disease name is found
        for phrase in detected_phrases:
            phrase_count = content.count(phrase)
            if phrase_count:
                phrase_words = len(phrase.split())
                phrase_bonus = phrase_count * 40 + phrase_words * 5
                score += phrase_bonus

        # Specialty relevance boost — exact slug match gets strong bonus
        page_path = page["path"]
        for specialty in boost_specialties:
            if page_path == specialty:
                score += 60
            elif page_path.startswith(specialty) or specialty in page_path:
                score += 30

        # Heading bonus
        for heading in page.get("headings", []):
            for token in tokens:
                if token in heading:
                    score += 8
                    break

        # Early occurrence bonus
        first_part = content[:max(300, len(content) // 3)]
        for token in tokens:
            if token in first_part:
                score += 3

        if score > 0:
            snippet = _make_snippet(page["raw_snippet"], query, 400)
            has_title_match = any(t in title_lower for t in tokens)
            scored.append({
                "path": page_path,
                "title": page["title"],
                "snippet": snippet,
                "score": score,
                "category": page["category"],
                "word_count": page["word_count"],
                "matched_tokens": len(matched_tokens),
                "_title_match": has_title_match,
            })

    # Sort: highest score first
    # Tiebreak: more matched tokens, then prefer pages with title match, then shorter pages
    scored.sort(key=lambda x: (
        -x["score"],
        -x["matched_tokens"],
        -int(x["_title_match"]),
        x["word_count"],
    ))
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
