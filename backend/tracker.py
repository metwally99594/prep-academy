import logging, uuid
from datetime import datetime, timezone, timedelta
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
    """Record a single answer event + update aggregated weakness profile (non-blocking).

    Alpha-A:
    - on correct answer for a concept: increment correct_streak, reset wrong_streak to 0
    - on wrong answer for a concept: increment wrong_streak, reset correct_streak to 0
    - increment total_seen on every touch
    """
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

    # 2. Aggregated weakness profile — upsert with $inc/$set
    inc_fields = {"total_answered": 1}
    set_fields = {"updated_at": now}
    specialty_key = f"specialties.{question['specialty_id']}"
    inc_fields[f"{specialty_key}.total"] = 1

    if is_correct:
        inc_fields[f"{specialty_key}.correct"] = 1
        for concept in concepts:
            ckey = _ckey(concept)
            inc_fields[f"mistakes.{ckey}.correct_streak"] = 1
            inc_fields[f"mistakes.{ckey}.total_seen"] = 1
            set_fields[f"mistakes.{ckey}.wrong_streak"] = 0
            set_fields[f"mistakes.{ckey}.concept"] = concept
            set_fields[f"mistakes.{ckey}.specialty_id"] = question["specialty_id"]
    else:
        inc_fields[f"{specialty_key}.wrong"] = 1
        for concept in concepts:
            ckey = _ckey(concept)
            inc_fields[f"mistakes.{ckey}.count"] = 1
            inc_fields[f"mistakes.{ckey}.wrong_streak"] = 1
            inc_fields[f"mistakes.{ckey}.total_seen"] = 1
            set_fields[f"mistakes.{ckey}.correct_streak"] = 0
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
    """Return recent wrong answers where confidence was high (dangerous misconceptions).

    Placeholder — confidence not yet captured on answer submission.
    """
    cursor = db.answer_tracker.find(
        {"user_id": user_id, "is_correct": False},
        {"_id": 0, "question_id": 1, "specialty_id": 1, "concepts": 1, "timestamp": 1},
    ).sort("timestamp", -1).limit(limit)
    return await cursor.to_list(limit)


# ─── Alpha-A: weakness summary + review queue ──────────────────────

async def get_weakness_summary(db, user_id: str, limit: int = 10, recent_days: int = 7) -> dict:
    """Return a snapshot for the dashboard / Tutor context.

    Sort: (wrong_streak DESC, count DESC) — currently struggling rises first.
    Defensive on legacy docs missing correct_streak (defaults to 0).
    """
    profile = await db.weakness_profile.find_one(
        {"user_id": user_id},
        {"_id": 0, "mistakes": 1, "specialties": 1},
    ) or {}
    mistakes = profile.get("mistakes") or {}

    top: list[dict] = []
    for ckey, data in mistakes.items():
        cnt = data.get("count", 0) or 0
        if cnt < 1:
            continue
        top.append({
            "ckey": ckey,
            "concept": data.get("concept", ckey),
            "specialty_id": data.get("specialty_id", ""),
            "wrong_count": cnt,
            "wrong_streak": data.get("wrong_streak", 0) or 0,
            "correct_streak": data.get("correct_streak", 0) or 0,
        })
    top.sort(key=lambda r: (-(r["wrong_streak"]), -(r["wrong_count"])))
    top = top[:limit]

    # Recent wrongs in last `recent_days` days
    cutoff = (datetime.now(timezone.utc) - timedelta(days=recent_days)).isoformat()
    cursor = db.answer_tracker.find(
        {"user_id": user_id, "is_correct": False, "timestamp": {"$gte": cutoff}},
        {"_id": 0, "question_id": 1, "specialty_id": 1, "concepts": 1, "timestamp": 1},
    ).sort("timestamp", -1).limit(50)
    recent = await cursor.to_list(50)

    by_specialty = []
    for sid, sdata in (profile.get("specialties") or {}).items():
        total = sdata.get("total", 0) or 0
        correct = sdata.get("correct", 0) or 0
        wrong = sdata.get("wrong", 0) or 0
        accuracy = round(correct / total, 3) if total > 0 else 0.0
        by_specialty.append({
            "specialty_id": sid,
            "total": total,
            "correct": correct,
            "wrong": wrong,
            "accuracy": accuracy,
        })
    by_specialty.sort(key=lambda r: r["accuracy"])

    return {
        "top_weaknesses": top,
        "recent_wrongs_7d": recent,
        "by_specialty": by_specialty,
    }


async def get_review_queue(db, user_id: str, limit: int = 10, min_wrong_count: int = 2) -> dict:
    """Return ordered weak concepts with sample question IDs.

    Alpha-A filter: wrong_count >= min_wrong_count (default 2, per decision A).
    Sort: (wrong_streak DESC, wrong_count DESC).
    """
    profile = await db.weakness_profile.find_one(
        {"user_id": user_id},
        {"_id": 0, "mistakes": 1},
    ) or {}
    mistakes = profile.get("mistakes") or {}
    entries: list[dict] = []
    for ckey, data in mistakes.items():
        cnt = data.get("count", 0) or 0
        if cnt < min_wrong_count:
            continue
        entries.append({
            "ckey": ckey,
            "concept": data.get("concept", ckey),
            "specialty_id": data.get("specialty_id", ""),
            "wrong_count": cnt,
            "wrong_streak": data.get("wrong_streak", 0) or 0,
        })
    entries.sort(key=lambda r: (-(r["wrong_streak"]), -(r["wrong_count"])))
    total_size = len(entries)
    top = entries[:limit]

    # Attach sample question IDs (specialty filter only — keep simple for Alpha-A)
    for entry in top:
        sid = entry.get("specialty_id")
        if not sid:
            entry["sample_question_ids"] = []
            continue
        cursor = db.questions.find(
            {"specialty_id": sid},
            {"_id": 0, "id": 1},
        ).limit(3)
        docs = await cursor.to_list(3)
        entry["sample_question_ids"] = [d.get("id") for d in docs if d.get("id")]

    return {"queue": top, "total_queue_size": total_size}


async def get_weak_specialty_priorities(
    db, user_id: str, min_wrong_count: int = 1,
) -> list[dict]:
    """Return specialties sorted by weakness priority for concept-aware question selection.

    Returns [{specialty_id, concept_keys: [str, ...], top_wrong_streak: int, top_count: int}]
    sorted by (wrong_streak DESC, count DESC).
    Only includes specialties with at least one concept meeting min_wrong_count.
    Empty list when profile is missing or no weak concepts exist (pure random fallback).
    """
    profile = await db.weakness_profile.find_one(
        {"user_id": user_id},
        {"_id": 0, "mistakes": 1},
    ) or {}
    mistakes = profile.get("mistakes") or {}

    by_specialty: dict[str, dict] = {}
    for ckey, data in mistakes.items():
        cnt = data.get("count", 0) or 0
        if cnt < min_wrong_count:
            continue
        sid = data.get("specialty_id", "")
        if not sid:
            continue
        if sid not in by_specialty:
            by_specialty[sid] = {
                "specialty_id": sid,
                "concept_keys": [],
                "top_wrong_streak": 0,
                "top_count": 0,
            }
        by_specialty[sid]["concept_keys"].append(ckey)
        ws = data.get("wrong_streak", 0) or 0
        if ws > by_specialty[sid]["top_wrong_streak"]:
            by_specialty[sid]["top_wrong_streak"] = ws
        if cnt > by_specialty[sid]["top_count"]:
            by_specialty[sid]["top_count"] = cnt

    result = list(by_specialty.values())
    result.sort(key=lambda r: (-(r["top_wrong_streak"]), -(r["top_count"])))
    return result
