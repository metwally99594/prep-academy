"""Tests for knowledge_lab_service Phase 2 parser helpers."""
import sys
from pathlib import Path

# Make the backend package importable regardless of pytest cwd
BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from services.knowledge_lab_service import (  # noqa: E402
    _strip_frontmatter,
    _resolve_wikilinks,
    get_page,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


# ── _strip_frontmatter ─────────────────────────────────────────────

def test_strip_frontmatter_no_frontmatter():
    text = "# Heading\n\nBody.\n"
    fm, body = _strip_frontmatter(text)
    assert fm == {}
    assert body == text


def test_strip_frontmatter_empty_string():
    fm, body = _strip_frontmatter("")
    assert fm == {}
    assert body == ""


def test_strip_frontmatter_full_extraction():
    raw = _read("full_frontmatter.md")
    fm, body = _strip_frontmatter(raw)
    assert fm["type"] == "disease"
    assert fm["title"] == "Asthma bronchiale"
    assert fm["icd10"] == "J45"
    assert "exam/kp" in fm["tags"]
    assert body.startswith("# Asthma bronchiale")
    assert "---" not in body.splitlines()[0]


def test_strip_frontmatter_malformed_returns_empty():
    raw = _read("malformed_yaml.md")
    fm, body = _strip_frontmatter(raw)
    assert fm == {}
    assert body == raw


def test_strip_frontmatter_missing_close_fence():
    text = "---\ntype: disease\ntitle: Foo\n\n# Body\n"
    fm, body = _strip_frontmatter(text)
    assert fm == {}
    assert body == text


def test_strip_frontmatter_bom_tolerated():
    text = "﻿---\ntype: index\ntitle: Foo\n---\n\n# Body\n"
    fm, body = _strip_frontmatter(text)
    assert fm["title"] == "Foo"
    assert body == "# Body\n"


def test_strip_frontmatter_list_top_level_rejected():
    text = "---\n- item1\n- item2\n---\n\n# Body\n"
    fm, body = _strip_frontmatter(text)
    assert fm == {}
    assert body == text


# ── _resolve_wikilinks ─────────────────────────────────────────────

def test_resolve_wikilinks_no_wikilinks_passthrough():
    text = "Just plain prose with [markdown](https://example.com) link."
    assert _resolve_wikilinks(text) == text


def test_resolve_wikilinks_basic():
    assert _resolve_wikilinks("See [[asthma]] here.") == "See [asthma](asthma.md) here."


def test_resolve_wikilinks_with_display():
    assert (
        _resolve_wikilinks("[[asthma|Asthma bronchiale]]")
        == "[Asthma bronchiale](asthma.md)"
    )


def test_resolve_wikilinks_with_path():
    assert (
        _resolve_wikilinks("[[sources/kp-vorbereitung-amboss]]")
        == "[sources/kp-vorbereitung-amboss](sources/kp-vorbereitung-amboss.md)"
    )


def test_resolve_wikilinks_with_section():
    assert _resolve_wikilinks("[[scores#NYHA]]") == "[scores#NYHA](scores.md#nyha)"


def test_resolve_wikilinks_section_and_display():
    assert (
        _resolve_wikilinks("[[scores#NYHA|NYHA Classes]]")
        == "[NYHA Classes](scores.md#nyha)"
    )


def test_resolve_wikilinks_embed_not_resolved():
    text = "![[ekg.png]]"
    assert _resolve_wikilinks(text) == text


def test_resolve_wikilinks_escaped_not_resolved():
    text = "Literal: \\[[escaped]]"
    assert _resolve_wikilinks(text) == text


def test_resolve_wikilinks_inline_code_not_resolved():
    text = "Use `[[in-inline-code]]` macro."
    assert _resolve_wikilinks(text) == text


def test_resolve_wikilinks_fenced_code_not_resolved():
    text = "Before.\n\n```\n[[in-fenced-code]]\n```\n\nAfter."
    assert _resolve_wikilinks(text) == text


def test_resolve_wikilinks_after_code_block_still_resolves():
    text = "```\n[[in-code]]\n```\n\nAfter [[outside]]."
    result = _resolve_wikilinks(text)
    assert "[[in-code]]" in result  # preserved inside fence
    assert "[outside](outside.md)" in result  # resolved after fence


def test_resolve_wikilinks_empty_left_alone():
    text = "Empty [[]] should stay."
    assert _resolve_wikilinks(text) == text


def test_resolve_wikilinks_mixed_fixture():
    raw = _read("wikilinks_mixed.md")
    result = _resolve_wikilinks(raw)
    # Resolved
    assert "[asthma](asthma.md)" in result
    assert "[chronic obstructive](copd.md)" in result
    assert "[sources/kp-vorbereitung-amboss](sources/kp-vorbereitung-amboss.md)" in result
    assert "[scores#NYHA](scores.md#nyha)" in result
    assert "[NYHA Classes](scores.md#nyha)" in result
    assert "[real-link](real-link.md)" in result
    assert "[Pneumologie](pneumologie.md)" in result
    # NOT resolved
    assert "![[ekg.png]]" in result
    assert "\\[[escaped]]" in result
    assert "`[[in-inline-code]]`" in result
    assert "[[in-fenced-code]]" in result


# ── get_page integration ───────────────────────────────────────────

def test_get_page_no_frontmatter_byte_identical(monkeypatch, tmp_path):
    """A page without frontmatter or wikilinks must round-trip byte-identical."""
    wiki = tmp_path / "wiki"
    wiki.mkdir()
    raw = (
        "# Plain\n\n"
        "No frontmatter, no wikilinks.\n\n"
        "## Related Pages\n\n"
        "- [Other](other.md) — Desc\n"
    )
    (wiki / "plain.md").write_text(raw, encoding="utf-8")
    monkeypatch.setenv("KNOWLEDGE_WIKI_DIR", str(wiki))

    page = get_page("plain")
    assert page is not None
    assert page["content"] == raw
    assert page["properties"] == {}
    assert page["title"] == "Plain"


def test_get_page_with_frontmatter_strips_yaml(monkeypatch, tmp_path):
    wiki = tmp_path / "wiki"
    wiki.mkdir()
    raw = (
        "---\n"
        "type: specialty\n"
        "title: Test Specialty\n"
        "tags: [type/specialty]\n"
        "---\n\n"
        "# Test Specialty\n\n"
        "Body here.\n"
    )
    (wiki / "test.md").write_text(raw, encoding="utf-8")
    monkeypatch.setenv("KNOWLEDGE_WIKI_DIR", str(wiki))

    page = get_page("test")
    assert page is not None
    assert page["properties"]["type"] == "specialty"
    assert page["properties"]["title"] == "Test Specialty"
    assert page["content"].startswith("# Test Specialty")
    assert "---" not in page["content"].splitlines()[0]
    assert page["title"] == "Test Specialty"


def test_get_page_resolves_wikilinks_in_body(monkeypatch, tmp_path):
    wiki = tmp_path / "wiki"
    wiki.mkdir()
    raw = "# Test\n\nLink to [[other]] here.\n"
    (wiki / "test.md").write_text(raw, encoding="utf-8")
    monkeypatch.setenv("KNOWLEDGE_WIKI_DIR", str(wiki))

    page = get_page("test")
    assert "[other](other.md)" in page["content"]
    assert "[[other]]" not in page["content"]


def test_get_page_malformed_frontmatter_falls_back(monkeypatch, tmp_path):
    wiki = tmp_path / "wiki"
    wiki.mkdir()
    raw = _read("malformed_yaml.md")
    (wiki / "broken.md").write_text(raw, encoding="utf-8")
    monkeypatch.setenv("KNOWLEDGE_WIKI_DIR", str(wiki))

    page = get_page("broken")
    assert page is not None
    assert page["properties"] == {}
    # Content falls back to raw (malformed YAML treated as no frontmatter)
    assert page["content"] == raw


# ── Phase 3 invariant: all wiki pages have valid frontmatter ───────

def test_all_wiki_pages_have_valid_frontmatter():
    """Every page in the strict Phase 3 scope must have YAML frontmatter
    with required fields (type, title, status, last_reviewed, tags) and
    a `type` that matches the path-derived category."""
    repo_root = Path(__file__).resolve().parents[2]
    knowledge_root = repo_root / "knowledge"
    wiki_dir = knowledge_root / "wiki"
    index_md = knowledge_root / "index.md"

    CONCEPT_NAMES = {"diagnostik", "biostatistik", "klinische-untersuchung", "praevention"}
    LICENSING_NAMES = {"nostrifikation"}

    def expected_category(filepath: Path) -> str:
        rel = filepath.resolve().relative_to(knowledge_root.resolve()).as_posix()
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

    required_fields = ["type", "title", "status", "last_reviewed", "tags"]

    files = (
        sorted(wiki_dir.glob("*.md"))
        + sorted((wiki_dir / "sources").glob("*.md"))
        + [index_md]
    )

    failures = []
    for f in files:
        if not f.exists():
            failures.append(f"{f}: file missing")
            continue
        raw = f.read_text(encoding="utf-8")
        fm, _body = _strip_frontmatter(raw)
        rel_name = f.resolve().relative_to(repo_root.resolve()).as_posix()
        if not fm:
            failures.append(f"{rel_name}: no frontmatter")
            continue
        for field in required_fields:
            if field not in fm:
                failures.append(f"{rel_name}: missing required field '{field}'")
        expected = expected_category(f)
        actual = fm.get("type")
        if actual != expected:
            failures.append(f"{rel_name}: type={actual!r} != expected {expected!r}")

    assert not failures, (
        "Frontmatter validation failures:\n  " + "\n  ".join(failures)
    )
