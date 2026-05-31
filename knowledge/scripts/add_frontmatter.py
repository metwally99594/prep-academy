"""
Phase 3 migration script: prepend YAML frontmatter to wiki pages.

Default mode is dry-run (no writes). Pass --apply to write changes.

Usage:
    python knowledge/scripts/add_frontmatter.py
        [--files PATH [PATH ...]]               # subset (default: strict scope)
        [--apply]                                # write changes (default: dry-run)
        [--reviewed-date YYYY-MM-DD]             # default: 2026-05-31
"""

import argparse
import re
import sys
from datetime import date
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
KNOWLEDGE = REPO / "knowledge"
WIKI = KNOWLEDGE / "wiki"
INDEX_MD = KNOWLEDGE / "index.md"

CONCEPT_NAMES = {"diagnostik", "biostatistik", "klinische-untersuchung", "praevention"}
LICENSING_NAMES = {"nostrifikation"}

# Map source-summary filename stems to short tag slugs
SOURCE_TAG_SLUG = {
    "kp-vorbereitung-amboss": "amboss",
    "austria-medical-licensing": "aerzteg",
}


# ── YAML rendering: block style for `related` and `sources` ────────

class _BlockList(list):
    """List subclass that forces block-style YAML output."""
    pass


def _represent_block_list(dumper, data):
    return dumper.represent_sequence(
        "tag:yaml.org,2002:seq", data, flow_style=False
    )


yaml.SafeDumper.add_representer(_BlockList, _represent_block_list)


# ── Scope discovery ─────────────────────────────────────────────────

def strict_scope() -> list:
    """Return the 27 files in the strict Phase 3 scope."""
    files = []
    for md in sorted(WIKI.glob("*.md")):
        files.append(md)
    for md in sorted((WIKI / "sources").glob("*.md")):
        files.append(md)
    files.append(INDEX_MD)
    return files


def detect_category(filepath: Path) -> str:
    rel = filepath.resolve().relative_to(KNOWLEDGE.resolve()).as_posix()
    stem = filepath.stem
    if rel == "index.md":
        return "index"
    if rel.startswith("wiki/sources/"):
        return "source"
    if stem in LICENSING_NAMES:
        return "licensing"
    if stem in CONCEPT_NAMES:
        return "concept"
    return "specialty"


# ── Title / related / sources extraction ────────────────────────────

_H1_RE = re.compile(r"^# (.+?)\s*$", re.MULTILINE)


def extract_title(raw: str, fallback_stem: str):
    m = _H1_RE.search(raw)
    if m:
        return m.group(1).strip(), False
    return fallback_stem.replace("-", " ").replace("_", " ").title(), True


_RELATED_SECTION_RE = re.compile(
    r"^##\s*Related Pages\s*$.*?(?=^##\s|\Z)",
    re.MULTILINE | re.DOTALL,
)
_RELATED_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+\.md)\)")


def extract_related(raw: str) -> list:
    match = _RELATED_SECTION_RE.search(raw)
    if not match:
        return []
    section = match.group(0)
    results = []
    seen = set()
    for _label, target in _RELATED_LINK_RE.findall(section):
        slug = target.replace(".md", "").replace("../", "").replace("wiki/", "")
        if slug not in seen:
            seen.add(slug)
            results.append(f"[[{slug}]]")
    return results


_SOURCES_LINK_RE = re.compile(r"\*\*Sources?:\*\*\s*\[([^\]]+)\]\(([^)]+\.md)\)")
_SOURCE_RAW_RE = re.compile(r"\*\*Source:\*\*\s*`(knowledge/raw/[^`]+)`")


def extract_sources(raw: str) -> list:
    results = []
    seen = set()
    for _label, target in _SOURCES_LINK_RE.findall(raw):
        slug = target.replace(".md", "").replace("../", "").replace("wiki/", "")
        if slug not in seen:
            seen.add(slug)
            results.append(f"[[{slug}]]")
    for raw_path in _SOURCE_RAW_RE.findall(raw):
        filename = raw_path.split("/")[-1].lower()
        link = None
        if "amboss" in filename or "kp" in filename:
            link = "[[sources/kp-vorbereitung-amboss]]"
        elif "austria" in filename or "licensing" in filename:
            link = "[[sources/austria-medical-licensing]]"
        if link and link not in seen:
            seen.add(link)
            results.append(link)
    return results


# ── Frontmatter composition ─────────────────────────────────────────

def compose_frontmatter(category: str, title: str, stem: str, related: list, sources: list, reviewed_date_obj: date) -> dict:
    """Compose the frontmatter dict per category. Lists destined for block style
    are wrapped in _BlockList; dates passed as date objects to render unquoted."""
    related_bl = _BlockList(related)
    sources_bl = _BlockList(sources)
    fm = {"type": category, "title": title}
    if category == "specialty":
        fm["specialty"] = [stem]
        fm["exam_relevance"] = "high"
        fm["status"] = "stable"
        fm["last_reviewed"] = reviewed_date_obj
        fm["sources"] = sources_bl
        fm["tags"] = ["type/specialty", f"specialty/{stem}", "exam/kp", "status/stable"]
        fm["related"] = related_bl
    elif category == "concept":
        fm["status"] = "stable"
        fm["last_reviewed"] = reviewed_date_obj
        fm["sources"] = sources_bl
        fm["tags"] = ["type/concept", "exam/kp", "status/stable"]
        fm["related"] = related_bl
    elif category == "licensing":
        fm["status"] = "stable"
        fm["last_reviewed"] = reviewed_date_obj
        fm["sources"] = sources_bl
        fm["tags"] = ["type/licensing", "exam/kp", "status/stable"]
        fm["related"] = related_bl
    elif category == "source":
        fm["status"] = "stable"
        fm["last_reviewed"] = reviewed_date_obj
        slug = SOURCE_TAG_SLUG.get(stem, stem.split("-")[0])
        fm["tags"] = ["type/source", f"source/{slug}"]
        fm["related"] = related_bl
    elif category == "index":
        fm["status"] = "stable"
        fm["last_reviewed"] = reviewed_date_obj
        fm["tags"] = ["type/index"]
    return fm


def render_frontmatter(fm: dict) -> str:
    body = yaml.safe_dump(
        fm,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=None,
    )
    return f"---\n{body}---\n\n"


# ── File processing ─────────────────────────────────────────────────

_FRONTMATTER_CHECK_RE = re.compile(r"^---\s*\n.*?\n---\s*(?:\n|$)", re.DOTALL)


def has_frontmatter(raw: str) -> bool:
    candidate = raw[1:] if raw.startswith("﻿") else raw
    if not candidate.startswith("---"):
        return False
    return _FRONTMATTER_CHECK_RE.match(candidate) is not None


def process_file(filepath: Path, reviewed_date_obj: date, apply: bool) -> dict:
    raw = filepath.read_text(encoding="utf-8")
    rel_path = filepath.resolve().relative_to(REPO.resolve()).as_posix()
    status = {
        "path": rel_path,
        "category": detect_category(filepath),
        "marker": None,
        "title": None,
        "related_count": 0,
        "sources_count": 0,
        "frontmatter_yaml": None,
    }
    if has_frontmatter(raw):
        status["marker"] = "SKIP"
        status["note"] = "already has frontmatter"
        return status
    stem = filepath.stem
    category = detect_category(filepath)
    title, used_fallback = extract_title(raw, stem)
    status["title"] = title
    status["marker"] = "WARN" if used_fallback else "OK"
    if used_fallback:
        status["note"] = "no H1 found; using filename-derived title"
    related = extract_related(raw) if category != "index" else []
    sources = extract_sources(raw) if category not in {"source", "index"} else []
    status["related_count"] = len(related)
    status["sources_count"] = len(sources)
    fm = compose_frontmatter(category, title, stem, related, sources, reviewed_date_obj)
    fm_block = render_frontmatter(fm)
    status["frontmatter_yaml"] = fm_block
    if apply:
        new_content = fm_block + raw
        filepath.write_text(new_content, encoding="utf-8")
        check = filepath.read_text(encoding="utf-8")
        m = _FRONTMATTER_CHECK_RE.match(check)
        if not m:
            status["marker"] = "ERROR"
            status["note"] = "written but frontmatter fence not recognised on re-read"
        else:
            try:
                parsed = yaml.safe_load(re.match(r"^---\s*\n(.*?)\n---", check, re.DOTALL).group(1))
                if not isinstance(parsed, dict):
                    status["marker"] = "ERROR"
                    status["note"] = "written but YAML did not round-trip to a dict"
            except yaml.YAMLError as e:
                status["marker"] = "ERROR"
                status["note"] = f"written but YAML invalid on round-trip: {e}"
    return status


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Write changes (default: dry-run, no writes)")
    parser.add_argument("--files", nargs="+", help="Subset of files (relative to repo root)")
    parser.add_argument("--reviewed-date", default="2026-05-31", help="Value for last_reviewed (YYYY-MM-DD)")
    args = parser.parse_args()

    try:
        reviewed_date_obj = date.fromisoformat(args.reviewed_date)
    except ValueError:
        print(f"ERROR: --reviewed-date must be YYYY-MM-DD, got {args.reviewed_date}", file=sys.stderr)
        sys.exit(2)

    if args.files:
        files = []
        for f in args.files:
            p = Path(f)
            if not p.is_absolute():
                p = (REPO / f).resolve()
            if not p.exists():
                print(f"WARN: file not found: {f}", file=sys.stderr)
                continue
            files.append(p)
    else:
        files = strict_scope()

    mode = "APPLY" if args.apply else "DRY-RUN"
    print("=" * 72)
    print(f"  Phase 3 frontmatter migration -- {mode}")
    print(f"  Files in scope: {len(files)}")
    print(f"  Last reviewed date: {args.reviewed_date}")
    print("=" * 72)

    summary = {"total": 0, "ok": 0, "warn": 0, "skip": 0, "error": 0, "written": 0}
    for f in files:
        status = process_file(f, reviewed_date_obj, apply=args.apply)
        print(f"\n--- {status['path']} ---")
        marker = status["marker"]
        line2 = f"  category: {status['category']} | marker: {marker}"
        if status.get("note"):
            line2 += f" | {status['note']}"
        print(line2)
        if status["title"]:
            print(f"  title: {status['title']}")
            print(f"  related: {status['related_count']} | sources: {status['sources_count']}")
        if status["frontmatter_yaml"]:
            print("  proposed frontmatter:")
            for line in status["frontmatter_yaml"].rstrip().splitlines():
                print(f"    {line}")
        summary["total"] += 1
        if marker == "OK":
            summary["ok"] += 1
            if args.apply:
                summary["written"] += 1
        elif marker == "WARN":
            summary["warn"] += 1
            if args.apply:
                summary["written"] += 1
        elif marker == "SKIP":
            summary["skip"] += 1
        elif marker == "ERROR":
            summary["error"] += 1

    print("\n" + "=" * 72)
    print(f"  Summary: total={summary['total']} | OK={summary['ok']} | WARN={summary['warn']} | SKIP={summary['skip']} | ERROR={summary['error']} | written={summary['written']}")
    print("=" * 72)


if __name__ == "__main__":
    main()
