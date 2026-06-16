"""Production smoke checks for Prep Academy.

This script intentionally uses only public/protected endpoint checks that do
not require secrets. Set EXPECTED_BACKEND_COMMIT to verify the deployed Render
commit prefix when /api/health exposes deployment metadata.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from typing import Any


BACKEND_URL = os.environ.get("BACKEND_URL", "https://prep-academy.onrender.com").rstrip("/")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "https://prepacademy-med.com").rstrip("/")
EXPECTED_BACKEND_COMMIT = os.environ.get("EXPECTED_BACKEND_COMMIT", "").strip()
TIMEOUT_SECONDS = float(os.environ.get("SMOKE_TIMEOUT_SECONDS", "30"))


def _request(method: str, url: str) -> tuple[int, str, float]:
    start = time.perf_counter()
    req = urllib.request.Request(url, method=method)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace"), time.perf_counter() - start
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return exc.code, body, time.perf_counter() - start


def _json(body: str) -> dict[str, Any]:
    try:
        data = json.loads(body)
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def _check(name: str, ok: bool, details: dict[str, Any]) -> dict[str, Any]:
    return {"name": name, "ok": ok, **details}


def main() -> int:
    checks: list[dict[str, Any]] = []

    status, body, latency = _request("GET", f"{BACKEND_URL}/api/health")
    health = _json(body)
    deployment = health.get("deployment", {}) if isinstance(health.get("deployment"), dict) else {}
    deployed_commit = str(deployment.get("commit", ""))
    commit_ok = not EXPECTED_BACKEND_COMMIT or deployed_commit.startswith(EXPECTED_BACKEND_COMMIT[:12])
    checks.append(
        _check(
            "backend_health",
            status == 200 and health.get("status") == "healthy" and commit_ok,
            {
                "status_code": status,
                "latency_ms": round(latency * 1000),
                "deployment_commit": deployed_commit,
                "expected_commit": EXPECTED_BACKEND_COMMIT[:12],
            },
        )
    )

    status, body, latency = _request("GET", f"{BACKEND_URL}/api/rag/status")
    rag = _json(body)
    checks.append(
        _check(
            "rag_status",
            status == 200 and rag.get("ready") is True and rag.get("active_vector_store") == "qdrant",
            {
                "status_code": status,
                "latency_ms": round(latency * 1000),
                "active_vector_store": rag.get("active_vector_store"),
                "legacy_chroma_ready": rag.get("legacy_chroma_ready"),
                "unified_document_count": rag.get("unified_document_count"),
            },
        )
    )

    status, _body, latency = _request("GET", FRONTEND_URL + "/")
    checks.append(
        _check(
            "frontend_domain",
            status == 200,
            {"status_code": status, "latency_ms": round(latency * 1000), "url": FRONTEND_URL},
        )
    )

    for name, path in (
        ("dicom_protected", "/api/dicom/kb-info"),
        ("obsidian_protected", "/api/rag/obsidian/status"),
    ):
        status, _body, latency = _request("GET", f"{BACKEND_URL}{path}")
        checks.append(
            _check(
                name,
                status in (401, 403),
                {"status_code": status, "latency_ms": round(latency * 1000), "path": path},
            )
        )

    ok = all(item["ok"] for item in checks)
    report = {
        "ok": ok,
        "backend_url": BACKEND_URL,
        "frontend_url": FRONTEND_URL,
        "checks": checks,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
