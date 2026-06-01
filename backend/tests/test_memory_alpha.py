"""Unit tests for Memory of Mistakes Alpha-A: tracker functions.

Endpoint integration tests are out of scope for Alpha-A — the endpoints
are thin wrappers over the tested tracker functions. If the tracker
behaves, the endpoints behave.
"""
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from tracker import (  # noqa: E402
    record_answer,
    get_weakness_summary,
    get_review_queue,
    _ckey,
)


def _make_db():
    """Build a MagicMock db with async-aware methods on the collections we use."""
    db = MagicMock()
    db.answer_tracker = MagicMock()
    db.answer_tracker.insert_one = AsyncMock()
    db.weakness_profile = MagicMock()
    db.weakness_profile.update_one = AsyncMock()
    db.weakness_profile.find_one = AsyncMock(return_value=None)
    return db


def _empty_cursor(return_value=None):
    cursor = MagicMock()
    cursor.sort = MagicMock(return_value=cursor)
    cursor.limit = MagicMock(return_value=cursor)
    cursor.to_list = AsyncMock(return_value=return_value or [])
    return cursor


def _make_question(qid, specialty, correct_text, tags=None):
    return {
        "id": qid,
        "specialty_id": specialty,
        "choices": [
            {"id": "a", "text": correct_text, "text_de": correct_text, "is_correct": True},
            {"id": "b", "text": "wrong choice", "text_de": "wrong choice", "is_correct": False},
        ],
        "tags": tags or [],
    }


# ── record_answer: streak + counter behaviour ───────────────────────

@pytest.mark.asyncio
async def test_record_answer_wrong_increments_wrong_streak_and_count():
    db = _make_db()
    q = _make_question("q1", "kardiologie", "Vierfachtherapie HFrEF")
    await record_answer(db, "u1", q, is_correct=False)
    update = db.weakness_profile.update_one.call_args.args[1]
    inc = update["$inc"]
    set_ = update["$set"]
    ckey = _ckey("Vierfachtherapie HFrEF")
    assert inc[f"mistakes.{ckey}.count"] == 1
    assert inc[f"mistakes.{ckey}.wrong_streak"] == 1
    assert inc[f"mistakes.{ckey}.total_seen"] == 1
    assert set_[f"mistakes.{ckey}.correct_streak"] == 0


@pytest.mark.asyncio
async def test_record_answer_correct_resets_wrong_streak_and_increments_correct_streak():
    db = _make_db()
    q = _make_question("q1", "kardiologie", "Vierfachtherapie HFrEF")
    await record_answer(db, "u1", q, is_correct=True)
    update = db.weakness_profile.update_one.call_args.args[1]
    inc = update["$inc"]
    set_ = update["$set"]
    ckey = _ckey("Vierfachtherapie HFrEF")
    assert inc[f"mistakes.{ckey}.correct_streak"] == 1
    assert inc[f"mistakes.{ckey}.total_seen"] == 1
    assert set_[f"mistakes.{ckey}.wrong_streak"] == 0
    # count must NOT be incremented on correct answers
    assert f"mistakes.{ckey}.count" not in inc


@pytest.mark.asyncio
async def test_record_answer_writes_event_log():
    db = _make_db()
    q = _make_question("q1", "kardiologie", "Asthma bronchiale")
    await record_answer(db, "u1", q, is_correct=False)
    assert db.answer_tracker.insert_one.called
    event = db.answer_tracker.insert_one.call_args.args[0]
    assert event["user_id"] == "u1"
    assert event["question_id"] == "q1"
    assert event["specialty_id"] == "kardiologie"
    assert event["is_correct"] is False
    assert "Asthma bronchiale" in event["concepts"]


@pytest.mark.asyncio
async def test_record_answer_specialty_counters_update_correctly():
    db = _make_db()
    q = _make_question("q1", "kardiologie", "X")
    await record_answer(db, "u1", q, is_correct=True)
    update = db.weakness_profile.update_one.call_args.args[1]
    inc = update["$inc"]
    assert inc["specialties.kardiologie.total"] == 1
    assert inc["specialties.kardiologie.correct"] == 1
    assert "specialties.kardiologie.wrong" not in inc


# ── get_weakness_summary ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_weakness_summary_empty_for_new_user():
    db = _make_db()
    db.answer_tracker.find = MagicMock(return_value=_empty_cursor([]))
    result = await get_weakness_summary(db, "new_user")
    assert result["top_weaknesses"] == []
    assert result["recent_wrongs_7d"] == []
    assert result["by_specialty"] == []


@pytest.mark.asyncio
async def test_weakness_summary_sorts_by_wrong_streak_desc_then_count():
    db = _make_db()
    db.weakness_profile.find_one = AsyncMock(return_value={
        "mistakes": {
            "low_streak_high_count": {
                "concept": "Low streak high count", "specialty_id": "kardiologie",
                "count": 10, "wrong_streak": 1, "correct_streak": 0,
            },
            "high_streak_low_count": {
                "concept": "High streak low count", "specialty_id": "kardiologie",
                "count": 2, "wrong_streak": 5, "correct_streak": 0,
            },
            "mid_streak_mid_count": {
                "concept": "Mid streak mid count", "specialty_id": "kardiologie",
                "count": 4, "wrong_streak": 3, "correct_streak": 0,
            },
        },
        "specialties": {},
    })
    db.answer_tracker.find = MagicMock(return_value=_empty_cursor([]))
    result = await get_weakness_summary(db, "u1")
    titles = [w["concept"] for w in result["top_weaknesses"]]
    assert titles == ["High streak low count", "Mid streak mid count", "Low streak high count"]


@pytest.mark.asyncio
async def test_weakness_summary_defaults_correct_streak_for_legacy_docs():
    """Legacy mistake docs (pre-Alpha-A) have no correct_streak field."""
    db = _make_db()
    db.weakness_profile.find_one = AsyncMock(return_value={
        "mistakes": {
            "legacy_concept": {
                "concept": "Legacy",
                "specialty_id": "kardiologie",
                "count": 3,
                "wrong_streak": 1,
                # no correct_streak field
            },
        },
        "specialties": {},
    })
    db.answer_tracker.find = MagicMock(return_value=_empty_cursor([]))
    result = await get_weakness_summary(db, "u1")
    assert result["top_weaknesses"][0]["correct_streak"] == 0


@pytest.mark.asyncio
async def test_weakness_summary_by_specialty_sorted_ascending_by_accuracy():
    db = _make_db()
    db.weakness_profile.find_one = AsyncMock(return_value={
        "mistakes": {},
        "specialties": {
            "kardiologie": {"total": 100, "correct": 80, "wrong": 20},
            "pneumologie": {"total": 100, "correct": 50, "wrong": 50},
            "neurologie": {"total": 100, "correct": 90, "wrong": 10},
        },
    })
    db.answer_tracker.find = MagicMock(return_value=_empty_cursor([]))
    result = await get_weakness_summary(db, "u1")
    accs = [s["accuracy"] for s in result["by_specialty"]]
    assert accs == sorted(accs)
    assert result["by_specialty"][0]["specialty_id"] == "pneumologie"


# ── get_review_queue ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_review_queue_filters_by_min_wrong_count_2():
    db = _make_db()
    db.weakness_profile.find_one = AsyncMock(return_value={
        "mistakes": {
            "single_wrong": {
                "concept": "Single", "specialty_id": "kardiologie",
                "count": 1, "wrong_streak": 1,
            },
            "double_wrong": {
                "concept": "Double", "specialty_id": "kardiologie",
                "count": 2, "wrong_streak": 1,
            },
        },
    })
    db.questions.find = MagicMock(return_value=_empty_cursor([]))
    result = await get_review_queue(db, "u1", limit=5)
    assert len(result["queue"]) == 1
    assert result["queue"][0]["concept"] == "Double"
    assert result["total_queue_size"] == 1


@pytest.mark.asyncio
async def test_review_queue_includes_sample_question_ids():
    db = _make_db()
    db.weakness_profile.find_one = AsyncMock(return_value={
        "mistakes": {
            "weak1": {
                "concept": "Weak One", "specialty_id": "kardiologie",
                "count": 5, "wrong_streak": 2,
            },
        },
    })
    db.questions.find = MagicMock(return_value=_empty_cursor([
        {"id": "q-a"}, {"id": "q-b"}, {"id": "q-c"}
    ]))
    result = await get_review_queue(db, "u1")
    assert result["queue"][0]["sample_question_ids"] == ["q-a", "q-b", "q-c"]


@pytest.mark.asyncio
async def test_review_queue_empty_for_new_user():
    db = _make_db()
    db.weakness_profile.find_one = AsyncMock(return_value=None)
    db.questions.find = MagicMock(return_value=_empty_cursor([]))
    result = await get_review_queue(db, "new_user")
    assert result["queue"] == []
    assert result["total_queue_size"] == 0


@pytest.mark.asyncio
async def test_review_queue_sort_order():
    db = _make_db()
    db.weakness_profile.find_one = AsyncMock(return_value={
        "mistakes": {
            "low_streak": {
                "concept": "Low", "specialty_id": "kardiologie",
                "count": 8, "wrong_streak": 1,
            },
            "high_streak": {
                "concept": "High", "specialty_id": "kardiologie",
                "count": 3, "wrong_streak": 4,
            },
        },
    })
    db.questions.find = MagicMock(return_value=_empty_cursor([]))
    result = await get_review_queue(db, "u1")
    titles = [e["concept"] for e in result["queue"]]
    assert titles == ["High", "Low"]


# ── _ckey behaviour (unchanged but locked-in) ───────────────────────

def test_ckey_normalises_spaces_and_case():
    assert _ckey("Vierfachtherapie HFrEF") == "vierfachtherapie_hfref"


def test_ckey_truncates_to_80_chars():
    assert len(_ckey("x" * 200)) == 80


def test_ckey_strips_non_alphanumeric():
    # Umlauts and special chars are replaced with _
    key = _ckey("Anästhesie / Notfall (akut)")
    assert all(c.isalnum() or c == "_" for c in key)
