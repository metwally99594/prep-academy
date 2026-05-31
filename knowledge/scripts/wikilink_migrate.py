"""
Phase 4 migration script: convert internal markdown links in wiki bodies to
Obsidian wikilinks. Frontmatter blocks are never touched.

Default mode is dry-run (no writes). Pass --apply to write changes.

Usage:
    python knowledge/scripts/wikilink_migrate.py
        [--files PATH [PATH ...]]               # subset (default: strict scope)
        [--apply]                                # write changes (default: dry-run)
        [--reverse]                              # wikilinks → markdown links
        [--keep-redundant-display]               # preserve [[page|page]]
        [--no-diff]                              # suppress per-file diff sample
"""

import argparse
import difflib
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
KNOWLEDGE = REPO / "knowledge"
WIKI = KNOWLEDGE / "wiki"
INDEX_MD = KNOWLEDGE / "index.md"

# ── Regexes ───────────────────────────────────────────────────────────────

_FENCED_CODE_RE = re.compile(r"```[^\n]*\n.*?\n```", re.DOTALL)
_INLINE_CODE_RE = re.compile(r"`[^`\n]+?`")

# Forward: [Text](target.md) or [Text](target.md#anchor) — excluding embeds
_MD_LINK_RE = re.compile(
    r"(?<!!)\[([^\]\n]*?)\]\(([^)\s]+\.md(?:#[^)]*)?)\)"
)

# Reverse: [[target]] or [[target|Display]] — excluding embeds/escaped
_WIKILINK_RE = re.compile(
    r"(?<!\\)(?<!!)\[\[([^\]|\n]+?)(?:\|([^\]\n]+?))?\]\]"
)


# ── Code-block masking ────────────────────────────────────────────────────

def _mask_code(text: str):
    placeholders = []

    def store(m):
        idx = len(placeholders)
        placeholders.append(m.group(0))
        return f"\x00CB{idx}\x00"

    masked = _FENCED_CODE_RE.sub(store, text)
    masked = _INLINE_CODE_RE.sub(store, masked)

    def restore(s: str) -> str:
        for i, original in enumerate(placeholders):
            s = s.replace(f"\x00CB{i}\x00", original)
        return s

    return masked, restore


# ── Frontmatter handling: split so we never touch frontmatter ─────────────

_FRONTMATTER_RE = re.compile(r"^---\s*\n.*?\n---\s*(?:\n|$)", re.DOTALL)


def _split_frontmatter(raw: str):
    """Return (frontmatter_with_fences, body)."""
    if not raw.startswith("---"):
        return "", raw
    m = _FRONTMATTER_RE.match(raw)
    if not m:
        return "", raw
    return raw[: m.end()], raw[m.end():]


# ── Target normalisation ──────────────────────────────────────────────────

def _is_external(target: str) -> bool:
    return ("://" in target) or target.startswith(("mailto:", "tel:", "#"))


def _normalise_target(target: str):
    """Split into (path, anchor); strip .md, leading ../ and wiki/."""
    if "#" in target:
        path_part, anchor = target.split("#", 1)
    else:
        path_part, anchor = target, ""
    if path_part.endswith(".md"):
        path_part = path_part[:-3]
    while path_part.startswith("../"):
        path_part = path_part[3:]
    if path_part.startswith("wiki/"):
        path_part = path_part[5:]
    return path_part, anchor


def _display_collapses(display: str, target_path: str) -> bool:
    """Should we drop the display text?
    Strict rule (decision: Option C): collapse only when the display text is
    literally identical to the target filename. This preserves all
    user-facing labels (no case folding, no lowercase regression).
    Empty display is also collapsed.
    """
    display_s = display.strip()
    if not display_s:
        return True
    target_basename = target_path.rsplit("/", 1)[-1]
    return display_s == target_basename


# ── Target existence (log only, never blocking) ───────────────────────────

def _target_exists(target_path: str) -> bool:
    # Try canonical locations first
    for base in (KNOWLEDGE, WIKI):
        if (base / f"{target_path}.md").exists():
            return True
    # Fallback: search by basename anywhere in the vault
    basename = target_path.rsplit("/", 1)[-1]
    return any(KNOWLEDGE.rglob(f"{basename}.md"))


# ── Forward conversion (markdown link → wikilink) ─────────────────────────

def convert_forward(text: str, collapse_redundant: bool = True):
    masked, restore = _mask_code(text)

    # Diagnostic counts
    all_md_in_text = _MD_LINK_RE.findall(text)
    non_code_md = _MD_LINK_RE.findall(masked)
    in_code = len(all_md_in_text) - len(non_code_md)

    stats = {
        "found_in_body": len(all_md_in_text),
        "in_code_skipped": in_code,
        "converted": 0,
        "collapsed": 0,
        "unresolved": [],
        "samples": [],
    }

    def replace(m):
        display = m.group(1)
        target = m.group(2)
        if _is_external(target):
            # Should be impossible because regex requires .md, but defensive
            return m.group(0)
        target_path, anchor = _normalise_target(target)
        link_target = f"{target_path}#{anchor}" if anchor else target_path
        if collapse_redundant and _display_collapses(display, target_path):
            wikilink = f"[[{link_target}]]"
            stats["collapsed"] += 1
        else:
            wikilink = f"[[{link_target}|{display}]]"
        if not _target_exists(target_path):
            stats["unresolved"].append(
                {"target_path": target_path, "wikilink": wikilink}
            )
        stats["converted"] += 1
        if len(stats["samples"]) < 5:
            stats["samples"].append({"before": m.group(0), "after": wikilink})
        return wikilink

    converted = _MD_LINK_RE.sub(replace, masked)
    return restore(converted), stats


# ── Reverse conversion (wikilink → markdown link) ─────────────────────────

def convert_reverse(text: str):
    masked, restore = _mask_code(text)

    stats = {"converted": 0, "samples": []}

    def replace(m):
        target = (m.group(1) or "").strip()
        display = (m.group(2) or "").strip()
        if not target:
            return m.group(0)
        if "#" in target:
            path_part, anchor = target.split("#", 1)
            href = f"{path_part}.md#{anchor}"
        else:
            href = f"{target}.md"
        label = display if display else target
        result = f"[{label}]({href})"
        stats["converted"] += 1
        if len(stats["samples"]) < 5:
            stats["samples"].append({"before": m.group(0), "after": result})
        return result

    converted = _WIKILINK_RE.sub(replace, masked)
    return restore(converted), stats


# ── Per-file pipeline ─────────────────────────────────────────────────────

def process_file(filepath: Path, apply: bool, reverse: bool, collapse_redundant: bool):
    raw = filepath.read_text(encoding="utf-8")
    fm, body = _split_frontmatter(raw)
    if reverse:
        new_body, stats = convert_reverse(body)
    else:
        new_body, stats = convert_forward(body, collapse_redundant=collapse_redundant)
    changed = new_body != body
    if apply and changed:
        filepath.write_text(fm + new_body, encoding="utf-8")
    return {
        "path": filepath.resolve().relative_to(REPO.resolve()).as_posix(),
        "changed": changed,
        "stats": stats,
        "old_body": body,
        "new_body": new_body,
    }


# ── Scope ─────────────────────────────────────────────────────────────────

def strict_scope():
    files = sorted(WIKI.glob("*.md"))
    files += sorted((WIKI / "sources").glob("*.md"))
    files.append(INDEX_MD)
    return files


# ── Reporting ─────────────────────────────────────────────────────────────

def print_file_report(report, show_diff: bool, reverse: bool):
    print(f"\n--- {report['path']} ---")
    st = report["stats"]
    if not reverse:
        print(f"  links found in body (incl. code): {st['found_in_body']}")
        print(f"  skipped (in code block): {st['in_code_skipped']}")
        print(f"  converted: {st['converted']}  (of which collapsed display: {st['collapsed']})")
        if st["unresolved"]:
            print(f"  WARN: {len(st['unresolved'])} target(s) not found on disk (log only):")
            for u in st["unresolved"][:5]:
                print(f"    {u['wikilink']}  (target_path={u['target_path']})")
            if len(st["unresolved"]) > 5:
                print(f"    ... +{len(st['unresolved']) - 5} more")
    else:
        print(f"  wikilinks converted back: {st['converted']}")
    if st.get("samples"):
        print("  sample conversions:")
        for s in st["samples"]:
            print(f"    {s['before']}  ->  {s['after']}")
    if show_diff and report["old_body"] != report["new_body"]:
        old_lines = report["old_body"].splitlines()
        new_lines = report["new_body"].splitlines()
        diff = list(
            difflib.unified_diff(old_lines, new_lines, lineterm="", n=0)
        )
        diff_payload = [
            l for l in diff
            if not l.startswith("---") and not l.startswith("+++") and not l.startswith("@@")
        ]
        if diff_payload:
            shown = min(20, len(diff_payload))
            print(f"  diff sample (first {shown} of {len(diff_payload)} lines):")
            for l in diff_payload[:shown]:
                truncated = l[:200] + ("..." if len(l) > 200 else "")
                print(f"    {truncated}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--reverse", action="store_true")
    parser.add_argument("--files", nargs="+")
    parser.add_argument("--keep-redundant-display", action="store_true")
    parser.add_argument("--no-diff", action="store_true")
    args = parser.parse_args()

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
    direction = "REVERSE" if args.reverse else "FORWARD"
    print("=" * 72)
    print(f"  Phase 4 wikilink migration -- {direction} / {mode}")
    print(f"  Files in scope: {len(files)}")
    print(f"  Collapse redundant display: {not args.keep_redundant_display}")
    print("=" * 72)

    summary = {
        "files": 0, "changed": 0, "unchanged": 0,
        "found": 0, "in_code": 0, "converted": 0, "collapsed": 0,
        "files_with_unresolved": 0, "total_unresolved": 0,
    }
    for f in files:
        rep = process_file(
            f,
            apply=args.apply,
            reverse=args.reverse,
            collapse_redundant=not args.keep_redundant_display,
        )
        print_file_report(rep, show_diff=not args.no_diff, reverse=args.reverse)
        summary["files"] += 1
        if rep["changed"]:
            summary["changed"] += 1
        else:
            summary["unchanged"] += 1
        st = rep["stats"]
        if not args.reverse:
            summary["found"] += st.get("found_in_body", 0)
            summary["in_code"] += st.get("in_code_skipped", 0)
            summary["collapsed"] += st.get("collapsed", 0)
            if st.get("unresolved"):
                summary["files_with_unresolved"] += 1
                summary["total_unresolved"] += len(st["unresolved"])
        summary["converted"] += st.get("converted", 0)

    print("\n" + "=" * 72)
    print(f"  Summary:")
    print(f"    files processed: {summary['files']} | changed: {summary['changed']} | unchanged: {summary['unchanged']}")
    if not args.reverse:
        print(f"    .md links found in body (incl. code): {summary['found']}")
        print(f"    skipped (in code blocks): {summary['in_code']}")
        print(f"    converted: {summary['converted']}  (of which collapsed: {summary['collapsed']})")
        print(f"    files with unresolved targets: {summary['files_with_unresolved']} ({summary['total_unresolved']} total — log only)")
    else:
        print(f"    wikilinks converted back: {summary['converted']}")
    print("=" * 72)


if __name__ == "__main__":
    main()
