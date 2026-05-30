import logging, re
from typing import Optional

logger = logging.getLogger(__name__)


def _jaccard_similarity(a: str, b: str) -> float:
    tok_a = set(re.findall(r'\w+', a.lower()))
    tok_b = set(re.findall(r'\w+', b.lower()))
    if not tok_a or not tok_b:
        return 0.0
    return len(tok_a & tok_b) / len(tok_a | tok_b)


def compute_agreement(responses: list[dict]) -> dict:
    n = len(responses)
    if n < 2:
        return {"agreement_score": 100.0, "models_agreeing": n, "models_total": n, "is_majority": True}

    threshold = 0.35
    agree_counts = [0] * n
    for i in range(n):
        for j in range(i + 1, n):
            sim = _jaccard_similarity(
                responses[i].get("answer", ""), responses[j].get("answer", "")
            )
            if sim >= threshold:
                agree_counts[i] += 1
                agree_counts[j] += 1

    max_agree = max(agree_counts) if agree_counts else 0
    models_agreeing = max_agree + 1

    return {
        "agreement_score": round(models_agreeing / n * 100, 1),
        "models_agreeing": models_agreeing,
        "models_total": n,
        "is_majority": max_agree >= (n - 1),
    }


def compute_evidence_coverage(doc_results: list[dict]) -> dict:
    if not doc_results:
        return {"documents": 0, "chapters": 0, "pages": 0, "average_similarity": 0.0, "coverage_score": 0.0}

    doc_ids = set()
    chapter_keys = set()
    total_pages = 0

    for r in doc_results:
        did = r.get("document_id") or r.get("filename", "")
        doc_ids.add(did)
        ch_key = f"{did}:{r.get('chapter_index') or r.get('chapter_title', '')}"
        chapter_keys.add(ch_key)
        ps = int(r.get("page_start") or 0)
        pe = int(r.get("page_end") or 0)
        total_pages += max(1, pe - ps + 1)

    sims = [float(r.get("score", 0) or 0) for r in doc_results]
    avg_sim = sum(sims) / len(sims) if sims else 0.0

    n_docs = len(doc_ids)
    n_ch = len(chapter_keys)

    doc_score = min(n_docs / 3.0, 1.0)
    ch_score = min(n_ch / 5.0, 1.0)
    sim_score = min(avg_sim, 1.0)
    coverage_score = (0.40 * ch_score + 0.40 * sim_score + 0.20 * doc_score) * 100

    return {
        "documents": n_docs,
        "chapters": n_ch,
        "pages": total_pages,
        "average_similarity": round(avg_sim, 4),
        "coverage_score": round(coverage_score, 1),
    }


def compute_confidence(
    agreement_score: Optional[float] = None,
    coverage_score: Optional[float] = None,
    similarity: Optional[float] = None,
) -> dict:
    has_agreement = agreement_score is not None
    a_w = 0.50 if has_agreement else 0.0
    c_w = 0.35 if has_agreement else 0.70
    s_w = 0.15 if has_agreement else 0.30

    a = (agreement_score or 0) * a_w
    c = (coverage_score or 0) * c_w
    s = ((similarity or 0) * 100) * s_w

    return {"confidence_score": round(min(a + c + s, 100.0), 1)}
