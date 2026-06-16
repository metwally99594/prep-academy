import os
import hashlib
import logging
from typing import Any, Optional

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from qdrant_client.http.exceptions import UnexpectedResponse

from embeddings import embed_text, embed_query, embed_batch

logger = logging.getLogger(__name__)

COLLECTION = "tutor_chapters"
VECTOR_SIZE = 384  # text-embedding-3-small truncated to 384d


def _point_id(doc_id: str, chapter_index: int) -> int:
    """Deterministic 64-bit unsigned integer from doc_id + chapter index."""
    raw = f"{doc_id}_{chapter_index}"
    return int(hashlib.sha256(raw.encode()).hexdigest()[:16], 16)


def stable_point_id(doc_id: str, chunk_index: int) -> int:
    """Public deterministic point id helper for unified ingestion."""
    return _point_id(doc_id, chunk_index)


def _qdrant_search(client, collection_name, query_vector, query_filter, limit, with_payload):
    """Compatibility wrapper: try search(), fall back to query_points()."""
    if hasattr(client, "search"):
        return client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            query_filter=query_filter,
            limit=limit,
            with_payload=with_payload,
        )
    # qdrant-client >=1.10.x uses query_points
    result = client.query_points(
        collection_name=collection_name,
        query=query_vector,
        query_filter=query_filter,
        limit=limit,
        with_payload=with_payload,
    )
    # query_points returns QueryResponse with .points
    return result.points if hasattr(result, "points") else result

_client = None

def _get_client() -> QdrantClient:
    global _client
    if _client is not None:
        return _client

    url = os.environ.get("QDRANT_URL")
    api_key = os.environ.get("QDRANT_API_KEY")

    if url and api_key:
        _client = QdrantClient(url=url, api_key=api_key, timeout=30)
    else:
        logger.warning("QDRANT_URL/QDRANT_API_KEY not set, using local mode")
        _client = QdrantClient(path="./.qdrant_data", timeout=30)

    _ensure_collection()
    return _client

def _ensure_collection():
    try:
        collections = _client.get_collections().collections
        names = [c.name for c in collections]
        if COLLECTION not in names:
            _client.create_collection(
                collection_name=COLLECTION,
                vectors_config=qmodels.VectorParams(
                    size=VECTOR_SIZE,
                    distance=qmodels.Distance.COSINE,
                ),
            )
            _client.create_payload_index(
                collection_name=COLLECTION,
                field_name="specialty_id",
                field_schema=qmodels.PayloadSchemaType.KEYWORD,
            )
            _client.create_payload_index(
                collection_name=COLLECTION,
                field_name="document_id",
                field_schema=qmodels.PayloadSchemaType.KEYWORD,
            )
            _client.create_payload_index(
                collection_name=COLLECTION,
                field_name="chapter_index",
                field_schema=qmodels.PayloadSchemaType.INTEGER,
            )
            _client.create_payload_index(
                collection_name=COLLECTION,
                field_name="document_type",
                field_schema=qmodels.PayloadSchemaType.KEYWORD,
            )
            _client.create_payload_index(
                collection_name=COLLECTION,
                field_name="vault_path",
                field_schema=qmodels.PayloadSchemaType.KEYWORD,
            )
            logger.info(f"Created Qdrant collection '{COLLECTION}'")
        else:
            # Ensure indexes exist on existing collections (idempotent)
            for field, schema in [
                ("specialty_id", qmodels.PayloadSchemaType.KEYWORD),
                ("document_id", qmodels.PayloadSchemaType.KEYWORD),
                ("chapter_index", qmodels.PayloadSchemaType.INTEGER),
                ("document_type", qmodels.PayloadSchemaType.KEYWORD),
                ("source_type", qmodels.PayloadSchemaType.KEYWORD),
                ("source", qmodels.PayloadSchemaType.KEYWORD),
                ("category", qmodels.PayloadSchemaType.KEYWORD),
                ("vault_path", qmodels.PayloadSchemaType.KEYWORD),
            ]:
                try:
                    _client.create_payload_index(
                        collection_name=COLLECTION,
                        field_name=field,
                        field_schema=schema,
                    )
                except Exception:
                    pass  # index already exists
    except Exception as e:
        logger.error(f"Failed to ensure Qdrant collection: {e}")

async def index_chapters(doc_id: str, filename: str, specialty_id: str, chapters: list[dict]):
    logger.info(f"[INDEX] index_chapters() received {len(chapters)} chapters for '{filename}'")
    if not chapters:
        logger.warning(f"[INDEX] No chapters to index for '{filename}' — skipping")
        return
    try:
        client = _get_client()
        # Collect valid texts and matching chapter metadata
        valid_texts = []
        valid_chapters = []
        skipped_no_text = 0
        for ch in chapters:
            text = ch.get("text", "")
            if not text or len(text.strip()) < 20:
                skipped_no_text += 1
                continue
            valid_texts.append(text)
            valid_chapters.append(ch)
        logger.info(f"[INDEX] {len(valid_texts)} valid chapters, {skipped_no_text} skipped (short text)")
        # Embed all chapters in one API call
        vectors = await embed_batch(valid_texts)
        # Build Qdrant points
        points = []
        skipped_bad_vec = 0
        for ch, vec in zip(valid_chapters, vectors):
            if not vec or all(v == 0.0 for v in vec):
                skipped_bad_vec += 1
                continue
            ch_idx = ch.get("index", 0)
            title = ch.get("title", "")
            text = ch.get("text", "")
            snippet = (text[:2000] + "...") if len(text) > 2000 else text
            points.append(qmodels.PointStruct(
                id=_point_id(doc_id, ch_idx),
                vector=vec,
                payload={
                    "document_id": doc_id,
                    "document_type": "tutor_document",
                    "source_type": "tutor",
                    "filename": filename,
                    "specialty_id": specialty_id,
                    "chapter_index": ch.get("index", 0),
                    "chapter_title": title,
                    "page_start": ch.get("page_start", 1),
                    "page_end": ch.get("page_end", 1),
                    "text": snippet,
                    "word_count": ch.get("word_count", 0),
                },
            ))
        logger.info(f"[INDEX] Vectors: {len(points)} good, {skipped_no_text} short-text, {skipped_bad_vec} bad-vectors")
        if points:
            result = client.upsert(
                collection_name=COLLECTION,
                points=points,
                wait=True,
            )
            logger.info(f"[INDEX] Qdrant upsert result: {result}")
            logger.info(f"[INDEX] Indexed {len(points)} chapters for doc '{filename}'")
        else:
            logger.warning(f"[INDEX] No valid points to upsert for '{filename}' — all chapters skipped")
    except Exception as e:
        logger.error(f"[INDEX] Index chapters error: {e}")


async def index_obsidian_chunks(chunks: list[dict]) -> int:
    """Upsert Obsidian note chunks into the existing tutor Qdrant collection."""
    if not chunks:
        return 0
    try:
        client = _get_client()
        valid_chunks = [c for c in chunks if c.get("text", "").strip()]
        vectors = await embed_batch([c["text"] for c in valid_chunks])
        points = []
        for chunk, vec in zip(valid_chunks, vectors):
            if not vec or all(v == 0.0 for v in vec):
                continue
            text = chunk.get("text", "")
            snippet = (text[:2000] + "...") if len(text) > 2000 else text
            points.append(qmodels.PointStruct(
                id=_point_id(chunk["document_id"], chunk["chunk_index"]),
                vector=vec,
                payload={
                    "document_id": chunk["document_id"],
                    "document_type": "obsidian_note",
                    "source_type": "obsidian",
                    "source": "Obsidian Vault",
                    "category": "Obsidian",
                    "filename": chunk.get("note_title", ""),
                    "specialty_id": chunk.get("specialty_id", "obsidian"),
                    "chapter_index": chunk["chunk_index"],
                    "chapter_title": chunk.get("chunk_title", ""),
                    "note_title": chunk.get("note_title", ""),
                    "vault_path": chunk.get("vault_path", ""),
                    "folder": chunk.get("folder", ""),
                    "headings": chunk.get("headings", []),
                    "tags": chunk.get("tags", []),
                    "backlinks": chunk.get("backlinks", []),
                    "file_hash": chunk.get("file_hash", ""),
                    "page_start": 1,
                    "page_end": 1,
                    "text": snippet,
                    "word_count": chunk.get("word_count", 0),
                    "updated_at": chunk.get("updated_at", ""),
                },
            ))
        if not points:
            return 0
        client.upsert(collection_name=COLLECTION, points=points, wait=True)
        logger.info("[Obsidian] Indexed %s chunks into Qdrant", len(points))
        return len(points)
    except Exception as e:
        logger.error("[Obsidian] Index chunks error: %s", e)
        return 0


async def delete_obsidian_note(vault_path: str) -> None:
    """Delete all vector chunks for one Obsidian vault path."""
    if not vault_path:
        return
    try:
        client = _get_client()
        client.delete(
            collection_name=COLLECTION,
            points_selector=qmodels.FilterSelector(filter=qmodels.Filter(must=[
                qmodels.FieldCondition(key="document_type", match=qmodels.MatchValue(value="obsidian_note")),
                qmodels.FieldCondition(key="vault_path", match=qmodels.MatchValue(value=vault_path)),
            ])),
            wait=True,
        )
    except Exception as e:
        logger.warning("[Obsidian] Delete vectors failed for %s: %s", vault_path, e)


async def delete_all_obsidian_notes() -> None:
    """Delete all Obsidian vectors from the tutor Qdrant collection."""
    try:
        client = _get_client()
        client.delete(
            collection_name=COLLECTION,
            points_selector=qmodels.FilterSelector(filter=qmodels.Filter(must=[
                qmodels.FieldCondition(key="document_type", match=qmodels.MatchValue(value="obsidian_note")),
            ])),
            wait=True,
        )
    except Exception as e:
        logger.warning("[Obsidian] Delete all vectors failed: %s", e)


async def upsert_unified_chunks(chunks: list[dict]) -> int:
    """Upsert chunks for any RAG source into the unified Qdrant collection.

    Expected chunk keys: document_id, chunk_index, text, source_type, source.
    Additional metadata is copied into the payload when JSON-serializable.
    """
    if not chunks:
        return 0
    try:
        client = _get_client()
        valid_chunks = [c for c in chunks if c.get("text", "").strip()]
        vectors = await embed_batch([c["text"] for c in valid_chunks])
        points = []
        for chunk, vec in zip(valid_chunks, vectors):
            if not vec or all(v == 0.0 for v in vec):
                continue
            text = chunk.get("text", "")
            payload = dict(chunk.get("metadata") or {})
            payload.update({
                "document_id": chunk["document_id"],
                "document_type": chunk.get("document_type", chunk.get("source_type", "document")),
                "source_type": chunk.get("source_type", "medical"),
                "source": chunk.get("source", chunk.get("filename", "Unknown")),
                "filename": chunk.get("filename", chunk.get("source", "")),
                "category": chunk.get("category", ""),
                "specialty_id": chunk.get("specialty_id", ""),
                "chapter_index": chunk["chunk_index"],
                "chapter_title": chunk.get("chunk_title", ""),
                "page_start": chunk.get("page_start", 1),
                "page_end": chunk.get("page_end", 1),
                "text": (text[:2000] + "...") if len(text) > 2000 else text,
                "word_count": chunk.get("word_count", len(text.split())),
                "updated_at": chunk.get("updated_at", ""),
            })
            points.append(qmodels.PointStruct(
                id=stable_point_id(chunk["document_id"], chunk["chunk_index"]),
                vector=vec,
                payload=payload,
            ))
        if not points:
            return 0
        client.upsert(collection_name=COLLECTION, points=points, wait=True)
        logger.info("[UnifiedRAG] Upserted %s chunks into Qdrant", len(points))
        return len(points)
    except Exception as e:
        logger.error("[UnifiedRAG] Upsert chunks error: %s", e)
        return 0


def _conditions_from_filters(filters: Optional[dict]) -> list:
    conditions = []
    for key, value in (filters or {}).items():
        if value is None or value == "":
            continue
        conditions.append(qmodels.FieldCondition(
            key=key,
            match=qmodels.MatchValue(value=value),
        ))
    return conditions


def count_unified(filters: Optional[dict] = None) -> int:
    """Count unified Qdrant points, optionally filtered by payload."""
    try:
        client = _get_client()
        query_filter = qmodels.Filter(must=_conditions_from_filters(filters)) if filters else None
        result = client.count(collection_name=COLLECTION, count_filter=query_filter, exact=True)
        return int(result.count)
    except Exception as e:
        logger.warning("[UnifiedRAG] Count error: %s", e)
        return 0


def delete_unified(filters: dict[str, Any]) -> int:
    """Delete unified Qdrant points matching payload filters."""
    if not filters:
        raise ValueError("delete_unified requires at least one filter")
    try:
        before = count_unified(filters)
        client = _get_client()
        client.delete(
            collection_name=COLLECTION,
            points_selector=qmodels.FilterSelector(
                filter=qmodels.Filter(must=_conditions_from_filters(filters))
            ),
            wait=True,
        )
        return before
    except Exception as e:
        logger.warning("[UnifiedRAG] Delete error: %s", e)
        return 0


def list_unified_sources(limit: int = 1000) -> list[dict[str, Any]]:
    """Aggregate source metadata from Qdrant payloads for admin/source views."""
    try:
        client = _get_client()
        points, _ = client.scroll(
            collection_name=COLLECTION,
            limit=max(1, min(limit, 10000)),
            with_payload=True,
            with_vectors=False,
        )
        sources: dict[str, dict[str, Any]] = {}
        for point in points:
            payload = point.payload or {}
            source = payload.get("source") or payload.get("filename") or "Unknown"
            key = f"{payload.get('source_type', '')}:{source}"
            if key not in sources:
                sources[key] = {
                    "source": source,
                    "source_type": payload.get("source_type", payload.get("document_type", "")),
                    "document_type": payload.get("document_type", ""),
                    "category": payload.get("category", ""),
                    "language": payload.get("language", ""),
                    "version": payload.get("version", ""),
                    "uploaded_at": payload.get("uploaded_at") or payload.get("updated_at", ""),
                    "chunks": 0,
                }
            sources[key]["chunks"] += 1
        return sorted(sources.values(), key=lambda s: (s.get("source_type", ""), s.get("source", "")))
    except Exception as e:
        logger.warning("[UnifiedRAG] List sources error: %s", e)
        return []


def list_unified_source_versions(source_name: str, limit: int = 1000) -> list[dict[str, Any]]:
    """Aggregate versions for a single source from Qdrant payloads."""
    try:
        client = _get_client()
        points, _ = client.scroll(
            collection_name=COLLECTION,
            scroll_filter=qmodels.Filter(must=_conditions_from_filters({"source": source_name})),
            limit=max(1, min(limit, 10000)),
            with_payload=True,
            with_vectors=False,
        )
        versions: dict[str, dict[str, Any]] = {}
        for point in points:
            payload = point.payload or {}
            version = payload.get("version") or "1.0"
            if version not in versions:
                versions[version] = {
                    "version": version,
                    "source": source_name,
                    "chunks": 0,
                    "uploaded_at": payload.get("uploaded_at") or payload.get("updated_at", ""),
                }
            versions[version]["chunks"] += 1
        return sorted(versions.values(), key=lambda v: v.get("version", ""))
    except Exception as e:
        logger.warning("[UnifiedRAG] List source versions error: %s", e)
        return []


async def search_unified(
    query: str,
    *,
    filters: Optional[dict] = None,
    limit: int = 10,
    candidate_limit: int = 50,
) -> list[dict]:
    """Unified vector search across all source types in Qdrant."""
    if not query or len(query.strip()) < 2:
        return []
    try:
        client = _get_client()
        vec = await embed_query(query)
        if not vec or all(v == 0.0 for v in vec):
            return []
        query_filter = qmodels.Filter(must=_conditions_from_filters(filters)) if filters else None
        results = _qdrant_search(
            client,
            collection_name=COLLECTION,
            query_vector=vec,
            query_filter=query_filter,
            limit=max(limit, candidate_limit),
            with_payload=True,
        )
        docs = []
        for r in results[: max(limit, candidate_limit)]:
            p = r.payload or {}
            docs.append({
                "document_id": p.get("document_id", ""),
                "source_type": p.get("source_type", p.get("document_type", "")),
                "document_type": p.get("document_type", ""),
                "source": p.get("source", p.get("filename", "Unknown")),
                "filename": p.get("filename", ""),
                "category": p.get("category", ""),
                "specialty_id": p.get("specialty_id", ""),
                "chunk_title": p.get("chapter_title", ""),
                "chapter_title": p.get("chapter_title", ""),
                "chunk_index": p.get("chapter_index"),
                "text": p.get("text", ""),
                "score": round(float(r.score), 4) if r.score is not None else 0.0,
                "vector_score": round(float(r.score), 4) if r.score is not None else 0.0,
                "page_start": p.get("page_start", 1),
                "page_end": p.get("page_end", 1),
                "note_title": p.get("note_title", ""),
                "vault_path": p.get("vault_path", ""),
                "tags": p.get("tags", []),
                "backlinks": p.get("backlinks", []),
                "metadata": p,
            })
        return docs[:limit]
    except Exception as e:
        logger.warning("[UnifiedRAG] Search error: %s", e)
        return []

_COMMON_CAPS = frozenset(['Der','Die','Das','Den','Dem','Des','Ein','Eine','Einen','Einer','Einem','Im','In','Bei','Mit','Von','Zum','Zur','Auf','Für','Aus','Nach','Vor','Durch','Über','Unter','Neben','An','Am','Um','Ohne','Gegen','Bis','Seit','Außer','Innerhalb','Außerhalb','Wegen'])


def _split_query(query: str) -> list[str]:
    """Split multi-topic query into individual sub-queries for better retrieval precision.
    
    Strategy:
    1. Split on punctuation and German conjunctions (und, oder, sowie, bzw.)
    2. If only one part, detect a list of medical terms by counting uppercase 
       nouns. If >= 3 medical terms found, split at each term boundary.
    """
    parts = [p.strip() for p in _re_split_sep.split(query) if p.strip()]
    if len(parts) > 1:
        logger.info(f"[Split] Query split into {len(parts)} sub-queries via separators")
        return parts
    # No separators: check if it's a list of capitalized medical terms
    words = query.split()
    if len(words) < 4:
        return [query]
    # Find capitalized terms that look like medical conditions
    caps = [i for i, w in enumerate(words) if w and w[0].isupper() and w not in _COMMON_CAPS and len(w) > 2]
    if len(caps) < 3:
        return [query]
    # Split at each capitalized term, grouping consecutive caps as named entities
    sub_queries = []
    start = 0
    for j in range(len(caps)):
        idx = caps[j]
        if j > 0 and idx - caps[j - 1] == 1:
            continue  # part of previous named entity (e.g. "Morbus Crohn")
        if idx > start:
            seg = ' '.join(words[start:idx]).strip()
            if seg:
                sub_queries.append(seg)
        start = idx
    last = ' '.join(words[start:]).strip()
    if last:
        sub_queries.append(last)
    if len(sub_queries) <= 1:
        return [query]
    logger.info(f"[Split] Query split into {len(sub_queries)} sub-queries via medical terms: {sub_queries}")
    return sub_queries


import re as _re_mod
_re_split_sep = _re_mod.compile(r'\s*[,;.:]+\s*|\s+(?:und|oder|sowie|bzw\.?)\s+', _re_mod.IGNORECASE)


async def search_chapters(query: str, specialty_id: Optional[str] = None, chapter_index: Optional[int] = None, limit: int = 5) -> list[dict]:
    """Deprecated compatibility wrapper over the unified Qdrant schema."""
    if not query or len(query) < 2:
        return []
    try:
        filters: dict[str, Any] = {}
        if specialty_id:
            filters["specialty_id"] = specialty_id
        if chapter_index is not None:
            filters["chapter_index"] = chapter_index
        docs = await search_unified(
            query,
            filters=filters or None,
            limit=limit,
            candidate_limit=max(limit, 10),
        )
        return [
            {
                "document_id": d.get("document_id", ""),
                "specialty_id": d.get("specialty_id", ""),
                "filename": d.get("filename") or d.get("source") or "Unbekannt",
                "chapter_title": d.get("chapter_title", ""),
                "chapter_index": d.get("chunk_index"),
                "text": d.get("text", ""),
                "score": d.get("score", 0.0),
                "page_start": d.get("page_start", 1),
                "page_end": d.get("page_end", 1),
                "document_type": d.get("document_type", "document"),
                "note_title": d.get("note_title", ""),
                "vault_path": d.get("vault_path", ""),
                "tags": d.get("tags", []),
                "backlinks": d.get("backlinks", []),
            }
            for d in docs
        ]
    except Exception as e:
        logger.warning(f"[UnifiedRAG] Legacy search_chapters wrapper failed: {e}")
        return []
