import os
import hashlib
import logging
from typing import Optional

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
            logger.info(f"Created Qdrant collection '{COLLECTION}'")
        else:
            # Ensure indexes exist on existing collections (idempotent)
            for field, schema in [("specialty_id", qmodels.PayloadSchemaType.KEYWORD),
                                  ("document_id", qmodels.PayloadSchemaType.KEYWORD),
                                  ("chapter_index", qmodels.PayloadSchemaType.INTEGER)]:
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
    if not query or len(query) < 2:
        return []
    try:
        client = _get_client()
        sub_queries = _split_query(query)
        logger.info(f"[Qdrant] Query: '{query[:60]}' | sub_queries={len(sub_queries)} | specialty={specialty_id}")

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
        merged = {}  # (document_id, chapter_index) -> (score, payload)
        for sq in sub_queries:
            vec = await embed_query(sq)
            if not vec or all(v == 0.0 for v in vec):
                continue
            results = _qdrant_search(
                client,
                collection_name=COLLECTION,
                query_vector=vec,
                query_filter=query_filter,
                limit=search_limit,
                with_payload=True,
            )
            logger.info(f"[Qdrant] sub-query '{sq[:40]}' → {len(results)} hits")
            for r in results:
                p = r.payload
                key = (p.get("document_id", ""), p.get("chapter_index"))
                if key not in merged or r.score > merged[key][0]:
                    merged[key] = (r.score, p)

        # Convert to sorted list
        sorted_results = sorted(merged.values(), key=lambda x: -x[0])
        logger.info(f"[Qdrant] Merged {len(merged)} unique results from {len(sub_queries)} sub-queries")
        for i, (score, p) in enumerate(sorted_results[:10]):
            logger.info(f"[Qdrant] #{i+1}: doc={p.get('filename','?')} ch={p.get('chapter_title','?')} score={score:.4f}")

        docs = []
        for score, p in sorted_results[:limit]:
            docs.append({
                "document_id": p.get("document_id", ""),
                "specialty_id": p.get("specialty_id", ""),
                "filename": p.get("filename", "Unbekannt"),
                "chapter_title": p.get("chapter_title", ""),
                "chapter_index": p.get("chapter_index"),
                "text": p.get("text", ""),
                "score": round(score, 4),
                "page_start": p.get("page_start", 1),
                "page_end": p.get("page_end", 1),
            })
        return docs
    except Exception as e:
        logger.warning(f"[Qdrant] Search error: {e}")
        return []
