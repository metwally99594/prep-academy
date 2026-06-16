"""
Retrieval Evaluation Harness

Usage:
    python -m evaluation.run_eval          # from backend/
    python evaluation/run_eval.py          # from backend/

Requires QDRANT_URL + QDRANT_API_KEY in environment (or local .qdrant_data/).
Output: printed report + evaluation/report.json
"""

import asyncio
import json
import logging
import os
import sys
import time
from collections import defaultdict
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")

from services.retrieval_orchestrator import RetrievalRequest, retrieve
from evaluation.questions import EVAL_QUESTIONS


def _matches(text: str, keywords: list[str]) -> bool:
    t = text.lower()
    return all(kw.lower() in t for kw in keywords)


async def run_evaluation() -> dict:
    n = len(EVAL_QUESTIONS)
    print(f"\n{'='*60}")
    print(f"  PrepAcademy — Retrieval Evaluation")
    print(f"  {n} gold-standard questions")
    print(f"{'='*60}\n")

    per_question = []
    top1_ok_total = 0
    top5_ok_total = 0

    for i, q in enumerate(EVAL_QUESTIONS, 1):
        qid = q["id"]
        query = q["query"]
        keywords = q["expected_keywords"]
        cat = q.get("category", "Allgemein")

        start = time.time()
        retrieval = await retrieve(RetrievalRequest(query=query, top_k=5, use_hybrid=True, use_reranker=True))
        docs = [
            {
                "chapter_title": r.get("chunk_title") or r.get("title", ""),
                "text": r.get("excerpt", ""),
                "score": r.get("score") or r.get("retrieval_score"),
            }
            for r in retrieval.get("sources", [])
        ]
        elapsed = time.time() - start

        top1_ok = False
        top5_ok = False
        top1_title = None
        top1_score = None
        result_count = len(docs)

        if docs:
            top1_text = f"{docs[0].get('chapter_title', '')} {docs[0].get('text', '')}"
            top1_ok = _matches(top1_text, keywords)
            top1_title = docs[0].get("chapter_title", "?")
            top1_score = docs[0].get("score")

            for d in docs[:5]:
                d_text = f"{d.get('chapter_title', '')} {d.get('text', '')}"
                if _matches(d_text, keywords):
                    top5_ok = True
                    break

        if top1_ok:
            top1_ok_total += 1
        if top5_ok:
            top5_ok_total += 1

        status = ""
        if not docs:
            status = "  NO RESULTS"
        elif not top5_ok:
            status = "  TOP-5 FAIL"
        elif not top1_ok:
            status = "  TOP-1 FAIL (top-5 ok)"

        print(
            f"  [{i:2d}/{n}] {qid:9s} top-1={'✓' if top1_ok else '✗'} "
            f"top-5={'✓' if top5_ok else '✗'}  "
            f"{top1_title or '—':30s} {top1_score or 0:.3f}  {elapsed:.1f}s{status}"
        )

        per_question.append({
            "id": qid,
            "category": cat,
            "query": query,
            "expected_keywords": keywords,
            "top1_ok": top1_ok,
            "top5_ok": top5_ok,
            "top1_chapter": top1_title,
            "top1_score": top1_score,
            "result_count": result_count,
            "latency_s": round(elapsed, 2),
        })

    top1_acc = top1_ok_total / n * 100
    top5_acc = top5_ok_total / n * 100

    cats = defaultdict(lambda: {"top1": 0, "top5": 0, "n": 0})
    for q in per_question:
        c = q["category"]
        cats[c]["n"] += 1
        if q["top1_ok"]:
            cats[c]["top1"] += 1
        if q["top5_ok"]:
            cats[c]["top5"] += 1

    print(f"\n{'─'*60}")
    print(f"  SCORE REPORT")
    print(f"{'─'*60}")
    print(f"  Total questions:  {n}")
    print(f"  Top-1 accuracy:   {top1_acc:.1f}%  ({top1_ok_total}/{n})")
    print(f"  Top-5 accuracy:   {top5_acc:.1f}%  ({top5_ok_total}/{n})")
    print(f"  Avg latency:      {sum(q['latency_s'] for q in per_question)/n:.2f}s")
    print(f"{'─'*60}\n")

    print(f"  {'Category':30s} {'n':>4s} {'top-1':>8s} {'top-5':>8s}")
    print(f"  {'─'*30} {'─'*4} {'─'*8} {'─'*8}")
    for cat in sorted(cats):
        c = cats[cat]
        print(
            f"  {cat:30s} {c['n']:4d} "
            f"{c['top1']/c['n']*100:6.1f}%  "
            f"{c['top5']/c['n']*100:6.1f}%"
        )

    fails = [q for q in per_question if not q["top5_ok"]]
    if fails:
        print(f"\n  FAILED (no match in top-5):")
        for q in fails:
            print(f"    [{q['id']}] {q['query'][:60]}")

    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total": n,
        "top1_accuracy_pct": round(top1_acc, 1),
        "top5_accuracy_pct": round(top5_acc, 1),
        "top1_correct": top1_ok_total,
        "top5_correct": top5_ok_total,
        "avg_latency_s": round(sum(q["latency_s"] for q in per_question) / n, 2),
        "categories": {
            cat: {
                "total": c["n"],
                "top1_correct": c["top1"],
                "top5_correct": c["top5"],
                "top1_accuracy_pct": round(c["top1"] / c["n"] * 100, 1),
                "top5_accuracy_pct": round(c["top5"] / c["n"] * 100, 1),
            }
            for cat, c in sorted(cats.items())
        },
        "failed_queries": [
            {"id": q["id"], "query": q["query"], "category": q["category"]}
            for q in fails
        ],
        "results": per_question,
    }

    report_path = Path(__file__).parent / "report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\n  Full report saved to: {report_path}")

    return report


if __name__ == "__main__":
    asyncio.run(run_evaluation())
