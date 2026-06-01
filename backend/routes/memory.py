"""Memory of Mistakes — Alpha-A endpoints.

Four endpoints under /api/:
- GET  /api/me/weakness-summary
- GET  /api/me/review-queue
- POST /api/review/start
- GET  /api/tutor/context/memory

All JWT-authenticated via get_current_user. No new collections. Reads
weakness_profile and answer_tracker; writes nothing.
"""
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel
from slowapi.errors import RateLimitExceeded

from database import db
from auth import get_current_user
from limiter import limiter
from tracker import get_weakness_summary, get_review_queue

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["memory"])


class ReviewStartRequest(BaseModel):
    limit: int = 10
    specialty_filter: Optional[str] = None


@router.get("/me/weakness-summary")
@limiter.limit("30/minute;200/hour")
async def weakness_summary_endpoint(request: Request, user: dict = Depends(get_current_user)):
    """Top weaknesses + recent wrongs + per-specialty accuracy."""
    return await get_weakness_summary(db, user["id"], limit=10)


@router.get("/me/review-queue")
@limiter.limit("20/minute;100/hour")
async def review_queue_endpoint(
    request: Request,
    limit: int = Query(10, ge=1, le=20),
    user: dict = Depends(get_current_user),
):
    """Queue of weak concepts (wrong_count >= 2) with sample question IDs."""
    return await get_review_queue(db, user["id"], limit=limit, min_wrong_count=2)


@router.post("/review/start")
@limiter.limit("10/minute;50/hour")
async def review_start_endpoint(
    request: Request,
    body: ReviewStartRequest,
    user: dict = Depends(get_current_user),
):
    """Build a review session of N questions targeting the user's weak concepts.

    Returns full question objects (for sessionStorage-driven quiz UI) plus
    question_ids and targeted_concepts. session_id is opaque, not persisted.
    """
    capped_limit = max(1, min(int(body.limit or 10), 20))
    rq = await get_review_queue(db, user["id"], limit=capped_limit, min_wrong_count=2)
    queue = rq.get("queue") or []
    if body.specialty_filter:
        queue = [e for e in queue if e.get("specialty_id") == body.specialty_filter]

    question_ids: List[str] = []
    seen = set()
    for entry in queue:
        for qid in (entry.get("sample_question_ids") or [])[:2]:
            if qid and qid not in seen:
                seen.add(qid)
                question_ids.append(qid)
                if len(question_ids) >= capped_limit:
                    break
        if len(question_ids) >= capped_limit:
            break

    # Fallback: fill remaining slots from the weakest specialty's question bank
    if len(question_ids) < capped_limit and queue:
        target_sid = queue[0].get("specialty_id")
        if target_sid:
            need = capped_limit - len(question_ids)
            cursor = db.questions.find(
                {"specialty_id": target_sid, "id": {"$nin": list(seen)}},
                {"_id": 0, "id": 1},
            ).limit(need)
            extra = await cursor.to_list(need)
            for d in extra:
                qid = d.get("id")
                if qid:
                    question_ids.append(qid)
                    seen.add(qid)

    # Hydrate full question objects in selected order
    questions: List[dict] = []
    for qid in question_ids:
        q = await db.questions.find_one({"id": qid}, {"_id": 0})
        if q:
            questions.append(q)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    session_id = f"rv_{today}_{uuid.uuid4().hex[:8]}"
    targeted = [
        {
            "ckey": entry.get("ckey"),
            "concept": entry.get("concept"),
            "specialty_id": entry.get("specialty_id"),
        }
        for entry in queue
    ]
    return {
        "session_id": session_id,
        "questions": questions,
        "question_ids": question_ids,
        "targeted_concepts": targeted,
    }


@router.get("/tutor/context/memory")
@limiter.limit("30/minute;200/hour")
async def tutor_context_memory_endpoint(request: Request, user: dict = Depends(get_current_user)):
    """Compact memory snapshot for the Tutor UI badge.

    The server-side Tutor prompt builder uses services.memory_context
    .build_tutor_memory_prefix() directly (which obeys decision B and emits
    only top weaknesses + weakest specialty). This endpoint exposes a
    slightly richer payload for the UI badge — the user-facing badge MAY
    display recent_wrongs_7d_count for transparency.
    """
    summary = await get_weakness_summary(db, user["id"], limit=3)
    top = (summary.get("top_weaknesses") or [])[:3]
    by_spec = summary.get("by_specialty") or []
    weakest_specialty = None
    for s in by_spec:
        if (s.get("total") or 0) >= 10:
            weakest_specialty = s.get("specialty_id")
            break
    return {
        "top_weaknesses": [
            {"concept": w.get("concept"), "specialty_id": w.get("specialty_id")}
            for w in top
        ],
        "recent_wrongs_7d_count": len(summary.get("recent_wrongs_7d") or []),
        "weakest_specialty": weakest_specialty,
    }
