import logging, uuid
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


def _extract_concepts(question: dict) -> list[str]:
    """Extract the medical concept(s) from a question — primarily the correct answer text."""
    concepts = []
    choices = question.get("choices") or question.get("choices_de", [])
    for c in choices:
        if c.get("is_correct"):
            text = (c.get("text_de") or c.get("text", "")).strip()
            if text and len(text) > 2:
                concepts.append(text)
    for t in (question.get("tags") or []):
        if isinstance(t, str) and t.strip():
            concepts.append(t.strip())
    return concepts or []


async def record_answer(db, user_id: str, question: dict, is_correct: bool):
    """Record a single answer event + update aggregated weakness profile (non-blocking)."""
    concepts = _extract_concepts(question)
    now = datetime.now(timezone.utc).isoformat()

    # 1. Raw event log — one doc per answer
    await db.answer_tracker.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "question_id": question["id"],
        "specialty_id": question["specialty_id"],
        "concepts": concepts,
        "is_correct": is_correct,
        "year": question.get("year"),
        "exam_location": question.get("exam_location"),
        "timestamp": now,
    })

    # 2. Aggregated weakness profile — upsert with $inc
    inc_fields = {"total_answered": 1}
    specialty_key = f"specialties.{question['specialty_id']}"
    inc_fields[f"{specialty_key}.total"] = 1

    if is_correct:
        inc_fields[f"{specialty_key}.correct"] = 1
    else:
        inc_fields[f"{specialty_key}.wrong"] = 1
        # Track each missed concept
        for concept in concepts:
            ckey = _ckey(concept)
            inc_fields[f"mistakes.{ckey}.count"] = 1
            inc_fields[f"mistakes.{ckey}.wrong_streak"] = 1

    set_fields = {"updated_at": now}
    if not is_correct:
        for concept in concepts:
            ckey = _ckey(concept)
            set_fields[f"mistakes.{ckey}.concept"] = concept
            set_fields[f"mistakes.{ckey}.specialty_id"] = question["specialty_id"]

    await db.weakness_profile.update_one(
        {"user_id": user_id},
        {"$inc": inc_fields, "$set": set_fields},
        upsert=True,
    )


def _ckey(concept: str) -> str:
    """Normalize a concept into a MongoDB-safe key."""
    import re
    return re.sub(r'[^a-zA-Z0-9_]', '_', concept.lower().strip())[:80]


async def get_heatmap(db, user_id: str) -> list[dict]:
    """Return per-specialty correctness percentages."""
    profile = await db.weakness_profile.find_one(
        {"user_id": user_id},
        {"_id": 0, "specialties": 1},
    )
    if not profile or "specialties" not in profile:
        return []

    rows = []
    for sid, data in profile["specialties"].items():
        total = data.get("total", 0) or 0
        correct = data.get("correct", 0) or 0
        pct = round(correct / total * 100, 1) if total > 0 else 0.0
        wrong = data.get("wrong", 0) or 0
        rows.append({
            "specialty_id": sid,
            "total": total,
            "correct": correct,
            "wrong": wrong,
            "percentage": pct,
        })
    rows.sort(key=lambda r: r["percentage"])
    return rows


async def get_repeated_mistakes(db, user_id: str, min_count: int = 2) -> list[dict]:
    """Return concepts missed >= min_count times."""
    profile = await db.weakness_profile.find_one(
        {"user_id": user_id},
        {"_id": 0, "mistakes": 1},
    )
    if not profile or "mistakes" not in profile:
        return []

    results = []
    for key, data in profile["mistakes"].items():
        cnt = data.get("count", 0) or 0
        if cnt >= min_count:
            results.append({
                "concept": data.get("concept", key),
                "specialty_id": data.get("specialty_id", ""),
                "count": cnt,
                "wrong_streak": data.get("wrong_streak", 0),
            })
    results.sort(key=lambda r: r["count"], reverse=True)
    return results


async def get_confidence_mismatches(db, user_id: str, limit: int = 20) -> list[dict]:
    """Return recent wrong answers where confidence was high (dangerous misconceptions)."""
    # We don't store confidence yet — this is a placeholder for future integration
    # For now, return recent wrong answers as a starting point
    cursor = db.answer_tracker.find(
        {"user_id": user_id, "is_correct": False},
        {"_id": 0, "question_id": 1, "specialty_id": 1, "concepts": 1, "timestamp": 1},
    ).sort("timestamp", -1).limit(limit)
    return await cursor.to_list(limit)
