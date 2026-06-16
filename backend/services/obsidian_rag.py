"""Obsidian vault ingestion for the tutor RAG pipeline.

This module reuses the existing Qdrant tutor vector store and embedding
provider from vector_store.py / embeddings.py. It stores file state in MongoDB
so unchanged notes are not re-embedded.
"""
from __future__ import annotations

import asyncio
import hashlib
import os
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from pymongo import ReturnDocument

from database import db, logger
from vector_store import (
    delete_all_obsidian_notes,
    delete_obsidian_note,
    index_obsidian_chunks,
)


OBSIDIAN_VAULT_PATH = os.environ.get("OBSIDIAN_VAULT_PATH", "")
OBSIDIAN_AUTO_SYNC = os.environ.get("OBSIDIAN_AUTO_SYNC", "true").lower() in ("1", "true", "yes")
_WATCH_DEFAULT = "false" if os.environ.get("ENVIRONMENT", "").lower() == "production" else "true"
OBSIDIAN_WATCH_CHANGES = os.environ.get("OBSIDIAN_WATCH_CHANGES", _WATCH_DEFAULT).lower() in ("1", "true", "yes")
OBSIDIAN_WATCH_INTERVAL_SECONDS = int(os.environ.get("OBSIDIAN_WATCH_INTERVAL_SECONDS", "60"))
OBSIDIAN_CHUNK_WORDS = int(os.environ.get("OBSIDIAN_CHUNK_WORDS", "350"))
OBSIDIAN_CHUNK_OVERLAP = int(os.environ.get("OBSIDIAN_CHUNK_OVERLAP", "40"))

STATE_COLLECTION = "obsidian_rag_files"
STATUS_COLLECTION = "obsidian_rag_status"
STATUS_ID = "obsidian_rag_status"
LOCK_ID = "obsidian_watcher_lock"

_watcher_task: asyncio.Task | None = None
_sync_lock = asyncio.Lock()


@dataclass
class ParsedNote:
    vault_path: str
    abs_path: str
    title: str
    folder: str
    headings: list[dict[str, Any]]
    tags: list[str]
    backlinks: list[str]
    content: str
    metadata: dict[str, Any]
    file_hash: str
    mtime: float


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _vault_root() -> Path | None:
    if not OBSIDIAN_VAULT_PATH:
        return None
    root = Path(OBSIDIAN_VAULT_PATH).expanduser().resolve()
    return root if root.exists() and root.is_dir() else None


def _relative_path(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root).as_posix()


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---", 4)
    if end == -1:
        return {}, text
    raw = text[4:end].strip()
    body = text[end + 4 :].lstrip()
    try:
        data = yaml.safe_load(raw) or {}
        return data if isinstance(data, dict) else {}, body
    except Exception as e:
        logger.debug("[Obsidian] Frontmatter parse failed: %s", e)
        return {}, body


def _extract_tags(frontmatter: dict[str, Any], body: str) -> list[str]:
    tags = []
    fm_tags = frontmatter.get("tags") or frontmatter.get("tag") or []
    if isinstance(fm_tags, str):
        fm_tags = re.split(r"[,;\s]+", fm_tags)
    if isinstance(fm_tags, list):
        tags.extend(str(t).strip().lstrip("#") for t in fm_tags if str(t).strip())
    tags.extend(m.group(1) for m in re.finditer(r"(?<!\w)#([A-Za-z0-9_\-/]+)", body))
    return sorted(set(t for t in tags if t))


def _extract_backlinks(body: str) -> list[str]:
    links = []
    for match in re.finditer(r"\[\[([^\]]+)\]\]", body):
        target = match.group(1).split("|", 1)[0].split("#", 1)[0].strip()
        if target:
            links.append(target)
    return sorted(set(links))


def _extract_headings(body: str) -> list[dict[str, Any]]:
    headings = []
    for match in re.finditer(r"^(#{1,6})\s+(.+?)\s*$", body, flags=re.MULTILINE):
        headings.append({"level": len(match.group(1)), "text": match.group(2).strip()})
    return headings


def _title_for(path: Path, frontmatter: dict[str, Any], body: str) -> str:
    title = str(frontmatter.get("title") or "").strip()
    if title:
        return title
    h1 = re.search(r"^#\s+(.+?)\s*$", body, flags=re.MULTILINE)
    return h1.group(1).strip() if h1 else path.stem


def parse_note(root: Path, path: Path) -> ParsedNote:
    raw = path.read_text(encoding="utf-8-sig", errors="replace")
    metadata, body = _split_frontmatter(raw)
    vault_path = _relative_path(root, path)
    return ParsedNote(
        vault_path=vault_path,
        abs_path=str(path),
        title=_title_for(path, metadata, body),
        folder=str(Path(vault_path).parent).replace("\\", "/") if Path(vault_path).parent != Path(".") else "",
        headings=_extract_headings(body),
        tags=_extract_tags(metadata, body),
        backlinks=_extract_backlinks(body),
        content=body.strip(),
        metadata=metadata,
        file_hash=_hash_text(raw),
        mtime=path.stat().st_mtime,
    )


def scan_vault(root: Path) -> list[ParsedNote]:
    notes = []
    for path in sorted(root.rglob("*.md")):
        if ".obsidian" in path.parts:
            continue
        try:
            notes.append(parse_note(root, path))
        except Exception as e:
            logger.warning("[Obsidian] Failed to parse %s: %s", path, e)
    return notes


def _section_chunks(note: ParsedNote) -> list[tuple[str, str, list[str]]]:
    lines = note.content.splitlines()
    sections: list[tuple[str, str, list[str]]] = []
    current_title = note.title
    hierarchy: list[tuple[int, str]] = []
    buffer: list[str] = []

    def flush():
        if buffer:
            headings = [h[1] for h in hierarchy]
            sections.append((current_title, "\n".join(buffer).strip(), headings))
            buffer.clear()

    for line in lines:
        hm = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
        if hm:
            flush()
            level = len(hm.group(1))
            text = hm.group(2).strip()
            hierarchy[:] = [h for h in hierarchy if h[0] < level]
            hierarchy.append((level, text))
            current_title = " > ".join(h[1] for h in hierarchy) or note.title
        buffer.append(line)
    flush()
    return sections or [(note.title, note.content, [])]


def chunk_note(note: ParsedNote) -> list[dict[str, Any]]:
    chunks = []
    document_id = "obs_" + hashlib.sha256(note.vault_path.encode("utf-8")).hexdigest()[:24]
    for section_title, section_text, hierarchy in _section_chunks(note):
        words = section_text.split()
        if not words:
            continue
        step = max(1, OBSIDIAN_CHUNK_WORDS - OBSIDIAN_CHUNK_OVERLAP)
        for start in range(0, len(words), step):
            part_words = words[start : start + OBSIDIAN_CHUNK_WORDS]
            if len(part_words) < 20 and chunks:
                break
            body = " ".join(part_words)
            header = [
                f"Title: {note.title}",
                f"Path: {note.vault_path}",
            ]
            if hierarchy:
                header.append(f"Headings: {' > '.join(hierarchy)}")
            if note.tags:
                header.append(f"Tags: {', '.join(note.tags)}")
            text = "\n".join(header) + "\n\n" + body
            chunks.append({
                "document_id": document_id,
                "vault_path": note.vault_path,
                "note_title": note.title,
                "folder": note.folder,
                "chunk_index": len(chunks),
                "chunk_title": section_title,
                "headings": hierarchy,
                "tags": note.tags,
                "backlinks": note.backlinks,
                "file_hash": note.file_hash,
                "text": text,
                "word_count": len(part_words),
                "specialty_id": "obsidian",
                "updated_at": _now(),
            })
    return chunks


async def _write_status(payload: dict[str, Any]) -> None:
    await db[STATUS_COLLECTION].update_one(
        {"id": STATUS_ID},
        {"$set": {"id": STATUS_ID, **payload, "updated_at": _now()}},
        upsert=True,
    )


async def get_obsidian_status() -> dict[str, Any]:
    root = _vault_root()
    indexed_notes = await db[STATE_COLLECTION].count_documents({})
    pipeline = [{"$group": {"_id": None, "chunks": {"$sum": "$chunk_count"}}}]
    agg = await db[STATE_COLLECTION].aggregate(pipeline).to_list(1)
    indexed_chunks = agg[0]["chunks"] if agg else 0
    status = await db[STATUS_COLLECTION].find_one({"id": STATUS_ID}, {"_id": 0}) or {}
    return {
        "configured": root is not None,
        "vault_path": str(root) if root else OBSIDIAN_VAULT_PATH,
        "auto_sync": OBSIDIAN_AUTO_SYNC,
        "watch_changes": OBSIDIAN_WATCH_CHANGES,
        "watcher_running": bool(_watcher_task and not _watcher_task.done()),
        "indexed_notes_count": indexed_notes,
        "indexed_chunks_count": indexed_chunks,
        "last_sync_at": status.get("last_sync_at"),
        "last_reindex_at": status.get("last_reindex_at"),
        "last_error": status.get("last_error", ""),
    }


async def sync_obsidian_vault(force: bool = False) -> dict[str, Any]:
    root = _vault_root()
    if not root:
        return {"ok": False, "error": "OBSIDIAN_VAULT_PATH is not configured or not readable"}

    async with _sync_lock:
        started = time.perf_counter()
        try:
            await db[STATE_COLLECTION].create_index("vault_path", unique=True)
            await db[STATE_COLLECTION].create_index("file_hash")
        except Exception as e:
            logger.debug("[Obsidian] Index creation skipped: %s", e)
        notes = scan_vault(root)
        seen_paths = {n.vault_path for n in notes}
        existing = await db[STATE_COLLECTION].find({}, {"_id": 0}).to_list(None)
        existing_by_path = {d["vault_path"]: d for d in existing}
        indexed_notes = updated_notes = skipped_notes = deleted_notes = indexed_chunks = 0

        for note in notes:
            prev = existing_by_path.get(note.vault_path)
            if prev and prev.get("file_hash") == note.file_hash and not force:
                skipped_notes += 1
                continue

            await delete_obsidian_note(note.vault_path)
            chunks = chunk_note(note)
            added = await index_obsidian_chunks(chunks)
            indexed_chunks += added
            indexed_notes += 1
            if prev:
                updated_notes += 1

            await db[STATE_COLLECTION].update_one(
                {"vault_path": note.vault_path},
                {"$set": {
                    "vault_path": note.vault_path,
                    "abs_path": note.abs_path,
                    "title": note.title,
                    "folder": note.folder,
                    "tags": note.tags,
                    "backlinks": note.backlinks,
                    "headings": note.headings,
                    "file_hash": note.file_hash,
                    "mtime": note.mtime,
                    "chunk_count": added,
                    "updated_at": _now(),
                }},
                upsert=True,
            )

        for old_path in set(existing_by_path) - seen_paths:
            await delete_obsidian_note(old_path)
            await db[STATE_COLLECTION].delete_one({"vault_path": old_path})
            deleted_notes += 1

        result = {
            "ok": True,
            "notes_scanned": len(notes),
            "notes_indexed": indexed_notes,
            "notes_updated": updated_notes,
            "notes_skipped": skipped_notes,
            "notes_deleted": deleted_notes,
            "chunks_indexed": indexed_chunks,
            "duration_ms": round((time.perf_counter() - started) * 1000),
            "last_sync_at": _now(),
        }
        await _write_status({"last_sync_at": result["last_sync_at"], "last_error": "", "last_result": result})
        return result


async def reindex_obsidian_vault() -> dict[str, Any]:
    root = _vault_root()
    if not root:
        return {"ok": False, "error": "OBSIDIAN_VAULT_PATH is not configured or not readable"}
    async with _sync_lock:
        await delete_all_obsidian_notes()
        await db[STATE_COLLECTION].delete_many({})
    result = await sync_obsidian_vault(force=True)
    result["last_reindex_at"] = _now()
    await _write_status({"last_reindex_at": result["last_reindex_at"], "last_error": "", "last_result": result})
    return result


async def search_obsidian(query: str, limit: int = 5) -> list[dict[str, Any]]:
    from services.retrieval_orchestrator import RetrievalRequest, retrieve

    retrieval = await retrieve(RetrievalRequest(
        query=query,
        top_k=limit,
        source_types=["obsidian", "obsidian_note"],
        use_hybrid=True,
        use_reranker=True,
    ))
    results = retrieval.get("sources", [])
    return [
        {
            "note_title": r.get("note_title") or r.get("title", ""),
            "vault_path": r.get("vault_path", ""),
            "chunk_text": r.get("excerpt", ""),
            "relevance_score": r.get("score") or r.get("retrieval_score"),
            "chunk_title": r.get("chunk_title", ""),
            "tags": r.get("tags", []),
        }
        for r in results
    ]


async def _watch_loop() -> None:
    while True:
        try:
            now = time.time()
            lock_until = now + max(30, OBSIDIAN_WATCH_INTERVAL_SECONDS * 2)
            lock = await db[STATUS_COLLECTION].find_one_and_update(
                {
                    "id": LOCK_ID,
                    "$or": [
                        {"locked_until": {"$lt": now}},
                        {"locked_until": {"$exists": False}},
                    ],
                },
                {"$set": {"id": LOCK_ID, "locked_until": lock_until, "updated_at": _now()}},
                upsert=True,
                return_document=ReturnDocument.AFTER,
            )
            if lock:
                await sync_obsidian_vault()
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.warning("[Obsidian] Auto-sync failed: %s", e)
            await _write_status({"last_error": str(e)})
        await asyncio.sleep(max(10, OBSIDIAN_WATCH_INTERVAL_SECONDS))


def start_obsidian_watcher_once() -> bool:
    global _watcher_task
    if not OBSIDIAN_AUTO_SYNC or not OBSIDIAN_WATCH_CHANGES or not _vault_root():
        return False
    if _watcher_task and not _watcher_task.done():
        return True
    try:
        _watcher_task = asyncio.create_task(_watch_loop())
        logger.info("[Obsidian] Watcher started")
        return True
    except RuntimeError:
        return False
