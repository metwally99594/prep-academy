"""Unified RAG retrieval layer.

All new retrieval should flow through this module. It hides vector-store
details, normalizes scores, applies lightweight hybrid scoring, and returns a
single source schema for Medical, Obsidian, and Tutor documents.
"""
from __future__ import annotations

import math
import re
import time
from dataclasses import dataclass
from typing import Any

from database import logger
from vector_store import search_unified


DEFAULT_CANDIDATE_LIMIT = 40


@dataclass
class RetrievalRequest:
    query: str
    top_k: int = 5
    source_types: list[str] | None = None
    filters: dict[str, Any] | None = None
    use_hybrid: bool = True
    use_reranker: bool = True


def _tokens(text: str) -> list[str]:
    return [
        t
        for t in re.sub(r"[^\w\sÄÖÜäöüß-]", " ", (text or "").lower()).split()
        if len(t) > 2
    ]


def _bm25_like(query: str, text: str) -> float:
    q_terms = _tokens(query)
    if not q_terms:
        return 0.0
    doc_terms = _tokens(text)
    if not doc_terms:
        return 0.0
    tf = {}
    for term in doc_terms:
        tf[term] = tf.get(term, 0) + 1
    score = 0.0
    doc_len = max(len(doc_terms), 1)
    for term in q_terms:
        freq = tf.get(term, 0)
        if freq:
            score += (freq * 2.2) / (freq + 1.2 * (0.25 + 0.75 * doc_len / 250))
    return score


def _minmax(values: list[float]) -> list[float]:
    if not values:
        return []
    lo, hi = min(values), max(values)
    if math.isclose(lo, hi):
        return [1.0 if hi > 0 else 0.0 for _ in values]
    return [(v - lo) / (hi - lo) for v in values]


async def _rerank(query: str, candidates: list[dict]) -> tuple[list[dict], bool]:
    """Use the same CrossEncoder as rag.py when available, otherwise no-op."""
    if not candidates:
        return candidates, False
    try:
        from sentence_transformers import CrossEncoder

        # Lazy local model. Kept function-local to avoid startup work.
        if not hasattr(_rerank, "_model"):
            setattr(_rerank, "_model", CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2", device="cpu"))
        model = getattr(_rerank, "_model")
        pairs = [(query, c.get("text", "")) for c in candidates]
        scores = model.predict(pairs)
        for c, score in zip(candidates, scores):
            c["rerank_score"] = float(score)
        candidates.sort(key=lambda c: c.get("rerank_score", 0), reverse=True)
        return candidates, True
    except Exception as e:
        logger.debug("[UnifiedRAG] Reranker unavailable: %s", e)
    return candidates, False


def _apply_source_filters(candidates: list[dict], source_types: list[str] | None) -> list[dict]:
    if not source_types:
        return candidates
    allowed = set(source_types)
    return [c for c in candidates if c.get("source_type") in allowed or c.get("document_type") in allowed]


def _normalize_and_score(query: str, candidates: list[dict], use_hybrid: bool) -> list[dict]:
    vector_scores = [float(c.get("vector_score", c.get("score", 0)) or 0) for c in candidates]
    bm25_scores = [_bm25_like(query, c.get("text", "")) for c in candidates]
    vector_norm = _minmax(vector_scores)
    bm25_norm = _minmax(bm25_scores)

    for idx, (c, vn, bn) in enumerate(zip(candidates, vector_norm, bm25_norm)):
        c["vector_score_norm"] = round(vn, 4)
        c["bm25_score"] = round(bm25_scores[idx] if candidates else 0, 4)
        c["bm25_score_norm"] = round(bn, 4)
        c["score"] = round((0.72 * vn + 0.28 * bn) if use_hybrid else vn, 4)
    candidates.sort(key=lambda c: c.get("score", 0), reverse=True)
    return candidates


def _to_source_record(c: dict, index: int) -> dict:
    return {
        "index": index,
        "source_type": c.get("source_type", c.get("document_type", "")),
        "source": c.get("source") or c.get("filename") or "Unknown",
        "title": c.get("note_title") or c.get("chunk_title") or c.get("filename") or c.get("source", ""),
        "note_title": c.get("note_title", ""),
        "vault_path": c.get("vault_path", ""),
        "category": c.get("category", ""),
        "chunk_title": c.get("chunk_title", c.get("chapter_title", "")),
        "excerpt": (c.get("text") or "")[:600],
        "score": c.get("rerank_score", c.get("score")),
        "retrieval_score": c.get("score"),
        "vector_score": c.get("vector_score"),
        "bm25_score": c.get("bm25_score"),
        "document_id": c.get("document_id", ""),
        "page_start": c.get("page_start"),
        "page_end": c.get("page_end"),
        "tags": c.get("tags", []),
    }


async def retrieve(req: RetrievalRequest) -> dict[str, Any]:
    started = time.perf_counter()
    stage_started = started
    stages: dict[str, float] = {}
    top_k = max(1, min(req.top_k, 20))
    filters = dict(req.filters or {})
    candidate_limit = max(DEFAULT_CANDIDATE_LIMIT, top_k * 6)

    candidates = await search_unified(
        req.query,
        filters=filters,
        limit=candidate_limit,
        candidate_limit=candidate_limit,
    )
    stages["vector_ms"] = round((time.perf_counter() - stage_started) * 1000, 2)
    stage_started = time.perf_counter()
    candidates = _apply_source_filters(candidates, req.source_types)
    candidates = _normalize_and_score(req.query, candidates, req.use_hybrid)
    candidates = candidates[:candidate_limit]
    stages["hybrid_ms"] = round((time.perf_counter() - stage_started) * 1000, 2)
    stage_started = time.perf_counter()
    reranker_applied = False
    if req.use_reranker:
        candidates, reranker_applied = await _rerank(req.query, candidates[: min(len(candidates), 30)])
    stages["rerank_ms"] = round((time.perf_counter() - stage_started) * 1000, 2)

    selected = candidates[:top_k]
    total_ms = round((time.perf_counter() - started) * 1000, 2)
    return {
        "query": req.query,
        "sources": [_to_source_record(c, i + 1) for i, c in enumerate(selected)],
        "raw_candidates": selected,
        "latency_ms": total_ms,
        "orchestrator": {
            "vector_store": "qdrant",
            "hybrid": req.use_hybrid,
            "reranker": req.use_reranker,
            "reranker_applied": reranker_applied,
            "candidate_count": len(candidates),
            "stage_latency_ms": stages,
        },
    }
