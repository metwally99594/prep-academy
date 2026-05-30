import os
import logging
from typing import Optional

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from qdrant_client.http.exceptions import UnexpectedResponse

from embeddings import embed_text, embed_query, embed_batch

logger = logging.getLogger(__name__)

COLLECTION = "tutor_chapters"
VECTOR_SIZE = 384  # text-embedding-3-small truncated to 384d

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
            logger.info(f"Created Qdrant collection '{COLLECTION}'")
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
            title = ch.get("title", "")
            text = ch.get("text", "")
            snippet = (text[:2000] + "...") if len(text) > 2000 else text
            points.append(qmodels.PointStruct(
                id=f"{doc_id}_{ch.get('index', 0)}",
                vector=vec,
                payload={
                    "document_id": doc_id,
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

async def search_chapters(query: str, specialty_id: Optional[str] = None, chapter_index: Optional[int] = None, limit: int = 5) -> list[dict]:
    if not query or len(query) < 2:
        return []
    try:
        client = _get_client()
        vec = await embed_query(query)
        if not vec or all(v == 0.0 for v in vec):
            logger.warning(f"[Qdrant] embed_query returned zero vector for '{query[:60]}'")
            return []

        filters = []
        if specialty_id:
            filters.append(qmodels.FieldCondition(
                key="specialty_id",
                match=qmodels.MatchValue(value=specialty_id),
            ))
        if chapter_index is not None:
            filters.append(qmodels.FieldCondition(
                key="chapter_index",
                match=qmodels.MatchValue(value=chapter_index),
            ))

        query_filter = qmodels.Filter(must=filters) if filters else None

        search_limit = max(limit, 10)
        results = client.search(
            collection_name=COLLECTION,
            query_vector=vec,
            query_filter=query_filter,
            limit=search_limit,
            with_payload=True,
        )

        logger.info(f"[Qdrant] Query: '{query[:60]}' | specialty={specialty_id} | limit={limit} | returned {len(results)} hits")
        for i, r in enumerate(results[:10]):
            p = r.payload
            logger.info(
                f"[Qdrant] #{i+1}: doc={p.get('filename','?')} "
                f"ch={p.get('chapter_title','?')} "
                f"pp={p.get('page_start','?')}-{p.get('page_end','?')} "
                f"score={r.score:.4f}"
            )

        docs = []
        for r in results[:limit]:
            p = r.payload
            docs.append({
                "document_id": p.get("document_id", ""),
                "specialty_id": p.get("specialty_id", ""),
                "filename": p.get("filename", "Unbekannt"),
                "chapter_title": p.get("chapter_title", ""),
                "chapter_index": p.get("chapter_index"),
                "text": p.get("text", ""),
                "score": round(r.score, 4),
                "page_start": p.get("page_start", 1),
                "page_end": p.get("page_end", 1),
            })
        return docs
    except Exception as e:
        logger.warning(f"[Qdrant] Search error: {e}")
        return []
