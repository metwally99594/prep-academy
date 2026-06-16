from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _python_files():
    for path in ROOT.rglob("*.py"):
        rel = path.relative_to(ROOT).as_posix()
        if (
            "__pycache__" in rel
            or rel.startswith("venv/")
            or rel.startswith(".venv/")
            or rel.startswith("chroma_db/")
            or rel.startswith(".qdrant_data/")
        ):
            continue
        yield rel, path


def test_no_direct_chroma_query_in_active_code():
    offenders = []
    for rel, path in _python_files():
        if rel.startswith("tests/"):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "_collection.query" in text or "rag_module._collection.query" in text:
            offenders.append(rel)
    assert offenders == []


def test_legacy_search_chapters_not_imported_by_active_code():
    offenders = []
    for rel, path in _python_files():
        if rel in {"vector_store.py"} or rel.startswith("tests/"):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "search_chapters" in text:
            offenders.append(rel)
    assert offenders == []
