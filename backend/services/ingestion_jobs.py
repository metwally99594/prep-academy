"""Background ingestion job tracking for the unified RAG system."""
from __future__ import annotations

import asyncio
import uuid
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from typing import Any

from database import db, logger


JOB_COLLECTION = "rag_ingestion_jobs"
DEFAULT_MAX_ATTEMPTS = 3


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def create_job(
    *,
    job_type: str,
    source_type: str,
    requested_by: str = "",
    payload: dict[str, Any] | None = None,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
) -> dict[str, Any]:
    job = {
        "id": str(uuid.uuid4()),
        "job_type": job_type,
        "source_type": source_type,
        "status": "queued",
        "progress": {
            "total": 0,
            "processed": 0,
            "failed": 0,
            "message": "Queued",
        },
        "payload": payload or {},
        "result": None,
        "error": "",
        "failed_chunks": [],
        "attempts": 0,
        "max_attempts": max(1, max_attempts),
        "requested_by": requested_by,
        "created_at": _now(),
        "updated_at": _now(),
        "started_at": None,
        "finished_at": None,
    }
    await db[JOB_COLLECTION].insert_one(job)
    job.pop("_id", None)
    return job


async def update_job_progress(
    job_id: str,
    *,
    total: int | None = None,
    processed: int | None = None,
    failed: int | None = None,
    message: str | None = None,
    failed_chunks: list[dict[str, Any]] | None = None,
) -> None:
    set_doc: dict[str, Any] = {"updated_at": _now()}
    if total is not None:
        set_doc["progress.total"] = total
    if processed is not None:
        set_doc["progress.processed"] = processed
    if failed is not None:
        set_doc["progress.failed"] = failed
    if message is not None:
        set_doc["progress.message"] = message
    if failed_chunks is not None:
        set_doc["failed_chunks"] = failed_chunks
    await db[JOB_COLLECTION].update_one({"id": job_id}, {"$set": set_doc})


async def _run_job(job_id: str, worker: Callable[[], Awaitable[dict[str, Any]]]) -> None:
    await db[JOB_COLLECTION].update_one(
        {"id": job_id},
        {
            "$inc": {"attempts": 1},
            "$set": {
                "status": "running",
                "started_at": _now(),
                "updated_at": _now(),
                "progress.message": "Running",
                "error": "",
            },
        },
    )
    try:
        result = await worker()
        await db[JOB_COLLECTION].update_one(
            {"id": job_id},
            {"$set": {
                "status": "completed",
                "result": result,
                "progress.message": "Completed",
                "updated_at": _now(),
                "finished_at": _now(),
            }},
        )
    except Exception as e:
        logger.exception("[RAG Jobs] Ingestion job %s failed", job_id)
        job = await get_job(job_id)
        attempts = int((job or {}).get("attempts", 1))
        max_attempts = int((job or {}).get("max_attempts", DEFAULT_MAX_ATTEMPTS))
        retryable = attempts < max_attempts
        await db[JOB_COLLECTION].update_one(
            {"id": job_id},
            {"$set": {
                "status": "queued" if retryable else "failed",
                "error": str(e),
                "progress.message": "Retry queued" if retryable else "Failed",
                "updated_at": _now(),
                "finished_at": None if retryable else _now(),
            }},
        )
        if retryable:
            await asyncio.sleep(min(30, 2 ** attempts))
            asyncio.create_task(_run_job(job_id, worker))


def start_job(job_id: str, worker: Callable[[], Awaitable[dict[str, Any]]]) -> None:
    asyncio.create_task(_run_job(job_id, worker))


async def get_job(job_id: str) -> dict[str, Any] | None:
    job = await db[JOB_COLLECTION].find_one({"id": job_id}, {"_id": 0})
    return job


async def list_jobs(limit: int = 20) -> list[dict[str, Any]]:
    cursor = db[JOB_COLLECTION].find({}, {"_id": 0}).sort("created_at", -1).limit(max(1, min(limit, 100)))
    return await cursor.to_list(length=max(1, min(limit, 100)))


async def status_summary() -> dict[str, Any]:
    pipeline = [{"$group": {"_id": "$status", "count": {"$sum": 1}}}]
    rows = await db[JOB_COLLECTION].aggregate(pipeline).to_list(None)
    return {row["_id"]: row["count"] for row in rows}
