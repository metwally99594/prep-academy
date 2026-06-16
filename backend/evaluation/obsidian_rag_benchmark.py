"""Benchmark Obsidian RAG retrieval.

Input JSON/JSONL/CSV rows:
  query, expected_path

Optional aliases:
  question -> query
  vault_path / expected_note -> expected_path

Metrics:
  Recall@5, Recall@10, MRR, latency.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import time
from pathlib import Path
from typing import Any

import requests


def _load_cases(path: Path) -> list[dict[str, str]]:
    if path.suffix.lower() == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
    elif path.suffix.lower() == ".jsonl":
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    else:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        rows = data.get("cases", data) if isinstance(data, dict) else data
    cases = []
    for row in rows:
        query = row.get("query") or row.get("question") or row.get("q")
        expected = row.get("expected_path") or row.get("vault_path") or row.get("expected_note")
        if query and expected:
            cases.append({"query": str(query), "expected_path": str(expected)})
    return cases


def _login(base_url: str, email: str, password: str) -> str:
    r = requests.post(
        f"{base_url}/api/auth/login",
        json={"email": email, "password": password},
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()
    token = data.get("token") or data.get("access_token")
    if not token:
        raise RuntimeError("Login response did not include a token")
    return token


def _search(base_url: str, token: str, query: str, limit: int) -> tuple[list[dict[str, Any]], float]:
    started = time.perf_counter()
    r = requests.get(
        f"{base_url}/api/rag/obsidian/search",
        params={"q": query, "limit": limit},
        headers={"Authorization": f"Bearer {token}"},
        timeout=60,
    )
    latency_ms = (time.perf_counter() - started) * 1000
    r.raise_for_status()
    return r.json().get("results", []), latency_ms


def run(cases: list[dict[str, str]], base_url: str, token: str) -> dict[str, Any]:
    rows = []
    recall5 = recall10 = 0
    reciprocal_ranks = []
    latencies = []

    for case in cases:
        results, latency_ms = _search(base_url, token, case["query"], 10)
        latencies.append(latency_ms)
        expected = case["expected_path"].lower().replace("\\", "/")
        paths = [(r.get("vault_path") or "").lower().replace("\\", "/") for r in results]
        rank = None
        for i, path in enumerate(paths, 1):
            if path == expected or expected in path:
                rank = i
                break
        if rank and rank <= 5:
            recall5 += 1
        if rank and rank <= 10:
            recall10 += 1
        reciprocal_ranks.append(1 / rank if rank else 0)
        rows.append({
            "query": case["query"],
            "expected_path": case["expected_path"],
            "rank": rank,
            "latency_ms": round(latency_ms, 2),
            "top_paths": paths[:5],
        })

    total = len(cases)
    avg_latency = sum(latencies) / total if total else 0
    p95_index = max(0, min(total - 1, math.ceil(total * 0.95) - 1)) if total else 0
    p95_latency = sorted(latencies)[p95_index] if total else 0
    return {
        "summary": {
            "cases": total,
            "recall_at_5": round(recall5 / total, 4) if total else 0,
            "recall_at_10": round(recall10 / total, 4) if total else 0,
            "mrr": round(sum(reciprocal_ranks) / total, 4) if total else 0,
            "avg_latency_ms": round(avg_latency, 2),
            "p95_latency_ms": round(p95_latency, 2),
        },
        "results": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark Obsidian RAG retrieval.")
    parser.add_argument("--cases", required=True, type=Path)
    parser.add_argument("--base-url", default=os.environ.get("BENCHMARK_BASE_URL", "http://localhost:8000"))
    parser.add_argument("--token", default=os.environ.get("BENCHMARK_TOKEN", ""))
    parser.add_argument("--email", default=os.environ.get("ADMIN_EMAIL", "admin@medical.com"))
    parser.add_argument("--password", default=os.environ.get("ADMIN_PASSWORD", ""))
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    cases = _load_cases(args.cases)
    if not args.token and not args.password:
        raise RuntimeError("Provide --token or set ADMIN_PASSWORD/--password for benchmark login.")
    token = args.token or _login(args.base_url.rstrip("/"), args.email, args.password)
    report = run(cases, args.base_url.rstrip("/"), token)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Saved report to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
