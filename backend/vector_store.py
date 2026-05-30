import os
import logging
from typing import Optional

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from qdrant_client.http.exceptions import UnexpectedResponse

from embeddings import embed_text, embed_query

logger = logging.getLogger(__name__)

COLLECTION = "tutor_chapters"
VECTOR_SIZE = 384  # multilingual-e5-small

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

def index_chapters(doc_id: str, filename: str, specialty_id: str, chapters: list[dict]):
    if not chapters:
        return
    try:
        client = _get_client()
        points = []
        for ch in chapters:
            text = ch.get("text", "")
            if not text or len(text.strip()) < 20:
                continue
            vec = embed_text(text)
            if not vec or all(v == 0.0 for v in vec):
                continue
            title = ch.get("title", "")
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
        if points:
            client.upsert(
                collection_name=COLLECTION,
                points=points,
                wait=True,
            )
            logger.info(f"Indexed {len(points)} chapters for doc '{filename}'")
    except Exception as e:
        logger.error(f"Index chapters error: {e}")

def search_chapters(query: str, specialty_id: Optional[str] = None, chapter_index: Optional[int] = None, limit: int = 5) -> list[dict]:
    if not query or len(query) < 2:
        return []
    try:
        client = _get_client()
        vec = embed_query(query)
        if not vec or all(v == 0.0 for v in vec):
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

        results = client.search(
            collection_name=COLLECTION,
            query_vector=vec,
            query_filter=query_filter,
            limit=limit,
            with_payload=True,
        )

        docs = []
        for r in results:
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
        logger.warning(f"Qdrant search error: {e}")
        return []
