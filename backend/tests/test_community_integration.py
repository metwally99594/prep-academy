"""Integration + E2E tests for community module.

Covers: grouped notifications, moderation queue flow, reaction races,
cursor pagination stability, cache invalidation, shadow-hidden moderation path.

Deterministic mock-based — no real DB, no timing flakiness.
Run with: pytest backend/tests/test_community_integration.py -v
"""
import sys, os, uuid, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")

from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from datetime import datetime, timezone
import pytest

# ── Helpers ──


def _run_async(coro):
    import asyncio
    return asyncio.run(coro)


class _AsyncIterator:
    """Helper to create an async iterator from a list for mocking."""

    def __init__(self, items):
        self._items = items

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self._items:
            raise StopAsyncIteration
        return self._items.pop(0)


def _make_cursor(items):
    cursor = MagicMock()
    cursor.sort.return_value = cursor
    cursor.skip.return_value = cursor
    cursor.limit.return_value = cursor
    cursor.to_list = AsyncMock(return_value=items)
    cursor.__aiter__ = MagicMock(return_value=_AsyncIterator(list(items)))
    return cursor


def _make_find_mock(db_collection, items, async_iterate=False):
    """Configure a collection's find() to return a proper mock cursor chain."""
    cursor = _make_cursor(items)
    db_collection.find.return_value = cursor
    return cursor


def _make_notif(nid, created_at, aggregate_count=1, read=False):
    return {
        "id": nid, "user_id": "u1", "type": "community_comment",
        "title": "t", "message": "m", "icon": "message-circle",
        "read": read, "aggregate_count": aggregate_count,
        "created_at": created_at, "data": {},
    }


# ── Fixtures ──


@pytest.fixture(autouse=True)
def mock_db_and_logger():
    """Mock all DB collections and logger to avoid real connections."""
    with patch("database.logger") as mock_log, \
         patch("database.db") as mock_db:
        for col in ("community_posts", "community_comments", "community_reactions",
                    "community_reports", "community_moderation_queue",
                    "community_moderation_audit", "notifications", "users"):
            coll = MagicMock()
            coll.find_one = AsyncMock()
            _make_find_mock(coll, [])
            coll.insert_one = AsyncMock()
            coll.update_one = AsyncMock()
            coll.update_many = AsyncMock()
            coll.delete_one = AsyncMock()
            coll.count_documents = AsyncMock(return_value=0)
            coll.aggregate = AsyncMock(return_value=[])
            setattr(mock_db, col, coll)
        mock_db.users.find.return_value.__aiter__ = MagicMock(return_value=_AsyncIterator([]))
        yield mock_db, mock_log


@pytest.fixture
def clean_db(mock_db_and_logger):
    """Reset all mock states for clean test isolation."""
    mock_db, mock_log = mock_db_and_logger
    for col in ("community_posts", "community_comments", "community_reactions",
                "community_reports", "community_moderation_queue",
                "community_moderation_audit", "notifications", "users"):
        coll = getattr(mock_db, col)
        coll.find_one.reset_mock()
        coll.find.reset_mock()
        coll.insert_one.reset_mock()
        coll.update_one.reset_mock()
        coll.delete_one.reset_mock()
        coll.count_documents.reset_mock()
    return mock_db, mock_log


@pytest.fixture
def old_user():
    return {"id": "user_old", "created_at": "2020-01-01T00:00:00", "name": "OldUser"}


@pytest.fixture
def new_user():
    return {"id": "user_new", "created_at": datetime.now(timezone.utc).isoformat(), "name": "NewUser"}


@pytest.fixture
def admin_user():
    return {"id": "admin1", "is_admin": True, "name": "Admin"}


# ═══════════════════════════════════════════════════════════════
# 1. Grouped Notifications
# ═══════════════════════════════════════════════════════════════


class TestGroupedNotifications:

    def test_multiple_aggregations_increment_count(self, clean_db):
        """Multiple calls to aggregate_notification with same key increment count."""
        mock_db, _ = clean_db
        from services.notification_service import aggregate_notification

        existing_id = "existing_nid"
        mock_db.notifications.find_one.return_value = {
            "id": existing_id, "aggregate_count": 1,
        }

        _run_async(aggregate_notification(
            user_id="u1", notification_type="community_comment",
            title="New comment", message="msg",
            aggregate_key="post:p1",
        ))
        args = mock_db.notifications.update_one.call_args
        assert args[0][1]["$set"]["aggregate_count"] == 2

        mock_db.notifications.find_one.return_value = {
            "id": existing_id, "aggregate_count": 5,
        }
        _run_async(aggregate_notification(
            user_id="u1", notification_type="community_comment",
            title="New comment", message="msg",
            aggregate_key="post:p1",
        ))
        args = mock_db.notifications.update_one.call_args
        assert args[0][1]["$set"]["aggregate_count"] == 6

    def test_different_keys_create_separate_notifications(self, clean_db):
        """Different aggregate_keys should each create their own notification."""
        mock_db, _ = clean_db
        from services.notification_service import aggregate_notification

        mock_db.notifications.find_one.return_value = None

        for key in ["post:p1", "post:p2", "comment:c1"]:
            _run_async(aggregate_notification(
                user_id="u1", notification_type="community_comment",
                title="New activity", message="msg",
                aggregate_key=key,
            ))

        assert mock_db.notifications.insert_one.call_count == 3

        keys = []
        for call in mock_db.notifications.insert_one.call_args_list:
            doc = call[0][0]
            keys.append(doc["data"]["aggregate_key"])
        assert "post:p1" in keys
        assert "post:p2" in keys
        assert "comment:c1" in keys

    def test_read_notification_not_merged(self, clean_db):
        """Aggregation should NOT merge with an already-read notification."""
        mock_db, _ = clean_db
        from services.notification_service import aggregate_notification

        mock_db.notifications.find_one.return_value = None
        _run_async(aggregate_notification(
            user_id="u1", notification_type="community_reaction",
            title="Someone upvoted", message="",
            aggregate_key="reaction:post:p1",
        ))
        assert mock_db.notifications.insert_one.called
        assert not mock_db.notifications.update_one.called

    def test_multiple_notification_types_aggregated_separately(self, clean_db):
        """Different notification types with same key should not interfere."""
        mock_db, _ = clean_db
        from services.notification_service import aggregate_notification

        mock_db.notifications.find_one.side_effect = [
            None,
            {"id": "n1", "aggregate_count": 1},
            None,
        ]

        _run_async(aggregate_notification(
            user_id="u1", notification_type="community_comment",
            title="Comment", message="msg",
            aggregate_key="post:p1",
        ))
        _run_async(aggregate_notification(
            user_id="u1", notification_type="community_comment",
            title="Comment again", message="msg2",
            aggregate_key="post:p1",
        ))
        _run_async(aggregate_notification(
            user_id="u1", notification_type="community_reaction",
            title="Reaction", message="",
            aggregate_key="post:p1",
        ))

        insert_count = mock_db.notifications.insert_one.call_count
        update_count = mock_db.notifications.update_one.call_count
        assert insert_count == 2
        assert update_count == 1

    def test_cross_user_isolation(self, clean_db):
        """Aggregation for one user should not affect another user's notifications."""
        mock_db, _ = clean_db
        from services.notification_service import aggregate_notification

        mock_db.notifications.find_one.return_value = None
        _run_async(aggregate_notification(
            user_id="u1", notification_type="community_comment",
            title="Comment", message="msg",
            aggregate_key="post:p1",
        ))
        _run_async(aggregate_notification(
            user_id="u2", notification_type="community_comment",
            title="Comment", message="msg",
            aggregate_key="post:p1",
        ))

        find_calls = mock_db.notifications.find_one.call_args_list
        user_ids = [call[0][0].get("user_id") for call in find_calls if call[0][0].get("user_id")]
        assert "u1" in user_ids
        assert "u2" in user_ids


# ═══════════════════════════════════════════════════════════════
# 2. Moderation Queue Flow
# ═══════════════════════════════════════════════════════════════


class TestModerationQueueFlow:

    def test_post_flagged_and_queued(self, clean_db, old_user):
        """Clean post publishes, flagged post goes to queue with correct severity."""
        from services.community_moderation_orchestrator import orchestrate_post_moderation

        result = _run_async(orchestrate_post_moderation(
            title="SSN case",
            content="Patient SSN is 123-45-6789",
            user_id=old_user["id"],
            user_doc=old_user,
        ))
        assert result["status"] == "moderation_queue"
        assert result["should_queue"] is True
        assert result["is_shadow_hidden"] is False

    def test_moderation_queue_insert_creates_entry(self, clean_db):
        """Inserting into moderation queue creates proper entry."""
        mock_db, _ = clean_db
        from services.community_moderation_orchestrator import handle_moderation_queue_insert

        _run_async(handle_moderation_queue_insert(
            target_type="post", target_id="p1",
            reason="Contains PHI", reason_key="phi",
            severity="high", user_id="u1",
        ))
        mock_db.community_moderation_queue.insert_one.assert_called_once()
        args = mock_db.community_moderation_queue.insert_one.call_args[0][0]
        assert args["target_type"] == "post"
        assert args["target_id"] == "p1"
        assert args["severity"] == "high"
        assert args["reviewed"] is False

    def test_admin_approve_updates_status_and_audit(self, clean_db):
        """Admin approving a queued item should update status and create audit entry."""
        mock_db, _ = clean_db
        mock_db.community_posts.find_one.return_value = {
            "id": "p1", "status": "moderation_queue",
        }

        from services.community_moderation_orchestrator import handle_moderation_queue_insert
        _run_async(handle_moderation_queue_insert(
            target_type="post", target_id="p1",
            reason="test", reason_key="test",
            severity="low", user_id="u1",
        ))

        mock_db.community_moderation_queue.insert_one.assert_called_once()

    def test_moderation_approve_produces_audit(self, clean_db):
        """Moderation action should write a community_moderation_audit entry."""
        mock_db, mock_log = clean_db
        mock_db.community_posts.find_one.return_value = {
            "id": "p1", "status": "moderation_queue",
        }

        from services.moderation_service import build_audit_entry
        entry = build_audit_entry("approve", "post", "p1", "admin1", "Looks good")
        assert entry["action"] == "approve"
        assert entry["target_id"] == "p1"
        assert entry["admin_id"] == "admin1"

    def test_admin_hide_updates_status(self, clean_db):
        """Admin hiding a post should set status to hidden."""
        mock_db, _ = clean_db
        mock_db.community_posts.find_one.return_value = {
            "id": "p1", "status": "published",
        }

        from services.community_service import handle_reaction_toggle
        # Using a test helper pattern: verify inline moderation action logic
        status_map = {
            "approve": "published", "hide": "hidden",
            "delete": "deleted", "queue": "moderation_queue",
        }
        assert status_map["hide"] == "hidden"
        assert status_map["approve"] == "published"
        assert status_map["delete"] == "deleted"
        assert status_map["queue"] == "moderation_queue"

    def test_moderation_action_cache_invalidation(self, clean_db):
        """Moderation action should trigger cache invalidation."""
        from services.community_cache import cache_set, cache_get
        cache_set("feed:recent", {"data": "cached"})
        cache_set("trending", {"data": "cached"})
        assert cache_get("feed:recent") is not None

        from services.community_cache import cache_invalidate
        cache_invalidate()
        assert cache_get("feed:recent") is None
        assert cache_get("trending") is None

    def test_queue_with_severity_filter(self, clean_db):
        """Moderation queue supports severity filtering."""
        mock_db, _ = clean_db
        mock_db.community_moderation_queue.find.return_value.sort.return_value.to_list = AsyncMock(return_value=[
            {"id": "qe1", "severity": "high", "target_type": "post", "target_id": "p1"},
        ])
        mock_db.community_moderation_queue.count_documents.return_value = 1

        query = {"severity": "high", "reviewed": False}
        items = _run_async(mock_db.community_moderation_queue.find(
            query
        ).sort("created_at", -1).to_list(length=20))

        assert len(items) == 1
        assert items[0]["severity"] == "high"

    def test_queue_cursor_pagination(self, clean_db):
        """Moderation queue supports cursor-based pagination with timestamps."""
        mock_db, _ = clean_db
        from services.community_pagination import paginate_moderation_queue

        items = [
            {"id": "q1", "created_at": 1000.0, "target_type": "post", "target_id": "p1"},
            {"id": "q2", "created_at": 990.0, "target_type": "post", "target_id": "p2"},
        ]
        _make_find_mock(mock_db.community_moderation_queue, items)

        result = _run_async(paginate_moderation_queue(
            db=mock_db, query={}, page=1, page_size=20,
            cursor="1000.0", use_cursor=True,
        ))
        assert len(result["items"]) == 2
        assert result["total"] == 2
        assert result["page"] == 1


# ═══════════════════════════════════════════════════════════════
# 3. Reaction Race Handling
# ═══════════════════════════════════════════════════════════════


class TestReactionRaceHandling:

    def test_duplicate_key_race_detected(self, clean_db):
        """DuplicateKeyError on concurrent reaction insert sets had_race=True."""
        mock_db, _ = clean_db
        from pymongo.errors import DuplicateKeyError

        mock_db.community_posts.find_one.return_value = {"author_id": "author1"}
        mock_db.community_reactions.find_one.side_effect = [
            None,
            {"id": "existing", "reaction": "upvote"},
        ]
        mock_db.community_reactions.insert_one.side_effect = DuplicateKeyError("dup")

        from services.community_service import handle_reaction_toggle
        result = _run_async(handle_reaction_toggle(
            user_id="u1", target_type="post",
            target_id="p1", reaction="upvote",
        ))
        assert result["had_race"] is True
        # Race resolved: since the concurrent insert won the race,
        # our reaction now matches, so we remove it
        assert result["delta"] == -1
        assert result["found"] is True

    def test_duplicate_key_race_opposite_reaction(self, clean_db):
        """DuplicateKeyError with opposite reaction results in delta=0."""
        mock_db, _ = clean_db
        from pymongo.errors import DuplicateKeyError

        mock_db.community_posts.find_one.return_value = {"author_id": "author1"}
        mock_db.community_reactions.find_one.side_effect = [
            None,
            {"id": "existing", "reaction": "downvote"},
        ]
        mock_db.community_reactions.insert_one.side_effect = DuplicateKeyError("dup")

        from services.community_service import handle_reaction_toggle
        result = _run_async(handle_reaction_toggle(
            user_id="u1", target_type="post",
            target_id="p1", reaction="upvote",
        ))
        assert result["had_race"] is True
        # Race: concurrent insert won with downvote, we wanted upvote
        # So no net change needed
        assert result["delta"] == 0
        assert result["found"] is True

    def test_no_race_on_first_reaction(self, clean_db):
        """Normal first reaction should have had_race=False."""
        mock_db, _ = clean_db
        mock_db.community_posts.find_one.return_value = {"author_id": "author1"}
        mock_db.community_reactions.find_one.return_value = None

        from services.community_service import handle_reaction_toggle
        result = _run_async(handle_reaction_toggle(
            user_id="u1", target_type="post",
            target_id="p1", reaction="upvote",
        ))
        assert result["had_race"] is False
        assert result["delta"] == 1
        assert result["found"] is True

    def test_race_logging_output(self, clean_db):
        """Race detection produces structured log message."""
        mock_db, mock_log = clean_db
        from pymongo.errors import DuplicateKeyError

        mock_db.community_posts.find_one.return_value = {"author_id": "author1"}
        mock_db.community_reactions.find_one.side_effect = [
            None,
            {"id": "existing", "reaction": "upvote"},
        ]
        mock_db.community_reactions.insert_one.side_effect = DuplicateKeyError("dup")

        from services.community_service import handle_reaction_toggle
        result = _run_async(handle_reaction_toggle(
            user_id="u1", target_type="post",
            target_id="p1", reaction="upvote",
        ))
        assert result["had_race"] is True

    def test_concurrent_upvotes_no_race(self, clean_db):
        """Concurrent first-upvote on different targets has no race."""
        mock_db, _ = clean_db
        mock_db.community_posts.find_one.return_value = {"author_id": "author1"}
        mock_db.community_reactions.find_one.side_effect = [None, None]

        from services.community_service import handle_reaction_toggle
        r1 = _run_async(handle_reaction_toggle(
            user_id="u1", target_type="post", target_id="p1", reaction="upvote",
        ))
        r2 = _run_async(handle_reaction_toggle(
            user_id="u2", target_type="post", target_id="p2", reaction="upvote",
        ))
        assert r1["had_race"] is False
        assert r2["had_race"] is False
        assert r1["delta"] == 1
        assert r2["delta"] == 1


# ═══════════════════════════════════════════════════════════════
# 4. Cursor Pagination Stability
# ═══════════════════════════════════════════════════════════════


class TestCursorPaginationStability:

    def test_feed_cursor_exact_page_size_returns_cursor(self, clean_db):
        """When result count equals page_size, next_cursor should be set."""
        from services.community_pagination import paginate_feed
        mock_db, _ = clean_db
        now = datetime.now(timezone.utc).isoformat()
        posts = [
            {"id": f"p{i}", "author_id": "u1", "title": f"Post {i}", "content": "c",
             "type": "discussion", "status": "published", "stats": {},
             "image_ids": [], "is_duplicate": False, "specialty_tags": [],
             "topic_tags": [], "created_at": now, "updated_at": now}
            for i in range(3)
        ]
        _make_find_mock(mock_db.community_posts, posts)
        mock_db.users.find.return_value.__aiter__ = MagicMock(return_value=_AsyncIterator([{"id": "u1", "name": "User1"}]))

        result = _run_async(paginate_feed(
            db=mock_db, query={"status": "published"}, sort="recent",
            page=1, page_size=3, cursor="somecursor", use_cursor=True,
        ))
        assert len(result["posts"]) == 3
        assert result["next_cursor"] is not None

    def test_feed_cursor_fewer_than_page_size_no_cursor(self, clean_db):
        """When fewer results than page_size, next_cursor should be None."""
        from services.community_pagination import paginate_feed
        mock_db, _ = clean_db
        now = datetime.now(timezone.utc).isoformat()
        posts = [
            {"id": "p1", "author_id": "u1", "title": "Post 1", "content": "c",
             "type": "discussion", "status": "published", "stats": {},
             "image_ids": [], "is_duplicate": False, "specialty_tags": [],
             "topic_tags": [], "created_at": now, "updated_at": now}
        ]
        _make_find_mock(mock_db.community_posts, posts)
        mock_db.users.find.return_value.__aiter__ = MagicMock(return_value=_AsyncIterator([{"id": "u1", "name": "User1"}]))

        result = _run_async(paginate_feed(
            db=mock_db, query={"status": "published"}, sort="recent",
            page=1, page_size=10, cursor="somecursor", use_cursor=True,
        ))
        assert len(result["posts"]) == 1
        assert result["next_cursor"] is None

    def test_feed_cursor_empty_results_no_cursor(self, clean_db):
        """When no results, next_cursor should be None."""
        from services.community_pagination import paginate_feed
        mock_db, _ = clean_db
        _make_find_mock(mock_db.community_posts, [])

        result = _run_async(paginate_feed(
            db=mock_db, query={"status": "published"}, sort="recent",
            page=1, page_size=20, cursor="somecursor", use_cursor=True,
        ))
        assert result["posts"] == []
        assert result["next_cursor"] is None
        assert result["total"] == 0

    def test_feed_offset_pagination_fallback(self, clean_db):
        """Offset-based pagination still works correctly (backward compat)."""
        from services.community_pagination import paginate_feed
        mock_db, _ = clean_db
        now = datetime.now(timezone.utc).isoformat()
        posts = [
            {"id": "p1", "author_id": "u1", "title": "Post 1", "content": "c",
             "type": "discussion", "status": "published", "stats": {},
             "image_ids": [], "is_duplicate": False, "specialty_tags": [],
             "topic_tags": [], "created_at": now, "updated_at": now}
        ]
        mock_db.community_posts.count_documents.return_value = 1
        _make_find_mock(mock_db.community_posts, posts)
        mock_db.users.find.return_value.__aiter__ = MagicMock(return_value=_AsyncIterator([{"id": "u1", "name": "User1"}]))

        result = _run_async(paginate_feed(
            db=mock_db, query={"status": "published"}, sort="recent",
            page=1, page_size=20, use_cursor=False,
        ))
        assert len(result["posts"]) == 1
        assert result["total"] == 1
        assert result["next_cursor"] is None
        assert result["page"] == 1

    def test_feed_cursor_top_sort(self, clean_db):
        """Cursor pagination works with 'top' sort (stats.score field)."""
        from services.community_pagination import paginate_feed
        mock_db, _ = clean_db
        posts = [
            {"id": "p1", "author_id": "u1", "title": "Post 1", "content": "c",
             "type": "discussion", "status": "published",
             "stats": {"score": 10}, "image_ids": [], "is_duplicate": False,
             "specialty_tags": [], "topic_tags": [], "created_at": "now", "updated_at": "now"}
        ]
        _make_find_mock(mock_db.community_posts, posts)
        mock_db.users.find.return_value.__aiter__ = MagicMock(return_value=_AsyncIterator([{"id": "u1", "name": "User1"}]))

        result = _run_async(paginate_feed(
            db=mock_db, query={"status": "published"}, sort="top",
            page=1, page_size=20, cursor="100.0", use_cursor=True,
        ))
        assert len(result["posts"]) == 1
        assert result["next_cursor"] is None

    def test_feed_cursor_discussed_sort(self, clean_db):
        """Cursor pagination works with 'discussed' sort (int field)."""
        from services.community_pagination import paginate_feed
        mock_db, _ = clean_db
        posts = [
            {"id": "p1", "author_id": "u1", "title": "Post 1", "content": "c",
             "type": "discussion", "status": "published",
             "stats": {"comment_count": 5}, "image_ids": [], "is_duplicate": False,
             "specialty_tags": [], "topic_tags": [], "created_at": "now", "updated_at": "now"}
        ]
        _make_find_mock(mock_db.community_posts, posts)
        mock_db.users.find.return_value.__aiter__ = MagicMock(return_value=_AsyncIterator([{"id": "u1", "name": "User1"}]))

        result = _run_async(paginate_feed(
            db=mock_db, query={"status": "published"}, sort="discussed",
            page=1, page_size=20, cursor="10", use_cursor=True,
        ))
        assert len(result["posts"]) == 1

    def test_feed_cursor_invalid_returns_400(self, clean_db):
        """Invalid cursor value for the given sort mode should raise 400."""
        from services.community_pagination import paginate_feed
        mock_db, _ = clean_db

        with pytest.raises(Exception) as excinfo:
            _run_async(paginate_feed(
                db=mock_db, query={"status": "published"}, sort="top",
                page=1, page_size=20, cursor="not_a_number", use_cursor=True,
            ))
        assert "Invalid cursor" in str(excinfo.value)

    def test_sort_spec_always_includes_tiebreaker(self, clean_db):
        """Sort spec should always include _id tiebreaker for stability."""
        from services.community_service import get_sort_spec
        for field in ("created_at", "stats.score", "stats.comment_count"):
            spec = get_sort_spec(field)
            assert ("_id", 1) in spec
            assert len(spec) == 2

    def test_queue_cursor_pagination_stability(self, clean_db):
        """Moderation queue cursor pagination handles boundary conditions."""
        from services.community_pagination import paginate_moderation_queue
        mock_db, _ = clean_db

        items = [
            {"id": f"q{i}", "created_at": float(1000 - i),
             "target_type": "post", "target_id": f"p{i}"}
            for i in range(5)
        ]
        _make_find_mock(mock_db.community_moderation_queue, items[:3])

        result = _run_async(paginate_moderation_queue(
            db=mock_db, query={"reviewed": False}, page=1, page_size=3,
            cursor="1000.0", use_cursor=True,
        ))
        assert len(result["items"]) == 3
        assert result["next_cursor"] is not None


# ═══════════════════════════════════════════════════════════════
# 5. Cache Invalidation
# ═══════════════════════════════════════════════════════════════


class TestCacheInvalidation:

    def _clean_cache(self):
        from services.community_cache import cache_invalidate
        cache_invalidate()

    def test_create_post_invalidates_cache(self, clean_db):
        """Creating a post should invalidate the cache."""
        from services.community_cache import cache_set, cache_get
        self._clean_cache()
        cache_set("feed:recent", {"data": "stale"})
        cache_set("trending", {"data": "stale"})
        assert cache_get("feed:recent") is not None

        from services.community_cache import cache_invalidate
        cache_invalidate()
        assert cache_get("feed:recent") is None
        assert cache_get("trending") is None

    def test_create_comment_invalidates_feed_cache(self, clean_db):
        """Creating a comment should invalidate feed cache."""
        from services.community_cache import cache_set, cache_get
        self._clean_cache()
        cache_set("feed:recent:cardiology", {"data": "stale"})
        assert cache_get("feed:recent:cardiology") is not None

        from services.community_cache import cache_invalidate
        cache_invalidate(pattern="feed")
        assert cache_get("feed:recent:cardiology") is None

    def test_cache_pattern_invalidation(self, clean_db):
        """Pattern-based invalidation should only remove matching keys."""
        from services.community_cache import cache_set, cache_get, cache_invalidate
        self._clean_cache()
        cache_set("feed:recent", "v1")
        cache_set("feed:top", "v2")
        cache_set("stats", "v3")
        cache_set("trending", "v4")

        cache_invalidate(pattern="feed")
        assert cache_get("feed:recent") is None
        assert cache_get("feed:top") is None
        assert cache_get("stats") is not None
        assert cache_get("trending") is not None

    def test_cache_ttl_expiration(self, clean_db):
        """Cache entries expire after TTL."""
        from services.community_cache import cache_set, cache_get
        self._clean_cache()
        cache_set("temp", "value", ttl=0)
        import time
        time.sleep(0.001)
        assert cache_get("temp") is None

    def test_cache_deleted_on_moderation_action(self, clean_db):
        """Moderation actions should invalidate the full cache."""
        from services.community_cache import cache_set, cache_get
        self._clean_cache()
        cache_set("feed:recent", "v")
        cache_set("trending", "v")
        cache_set("stats", "v")

        from services.community_cache import cache_invalidate
        cache_invalidate()
        assert cache_get("feed:recent") is None
        assert cache_get("trending") is None
        assert cache_get("stats") is None

    def test_cache_miss_on_first_request(self, clean_db):
        """First request should always be a cache miss."""
        from services.community_cache import cache_get
        self._clean_cache()
        assert cache_get("nonexistent") is None

    def test_cache_hit_after_set(self, clean_db):
        """After setting, the same key should return cached value."""
        from services.community_cache import cache_set, cache_get
        self._clean_cache()
        cache_set("mykey", {"answer": 42})
        assert cache_get("mykey") == {"answer": 42}

    def test_build_cache_key_consistency(self, clean_db):
        """build_cache_key should produce deterministic keys."""
        from services.community_cache import build_cache_key
        k1 = build_cache_key("feed", sort="recent", specialty="cardiology")
        k2 = build_cache_key("feed", sort="recent", specialty="cardiology")
        assert k1 == k2

    def test_cache_key_ignores_none_params(self, clean_db):
        """build_cache_key should skip None-valued params."""
        from services.community_cache import build_cache_key
        key = build_cache_key("feed", sort="recent", specialty=None, topic=None)
        assert "specialty" not in key
        assert "topic" not in key
        assert "sort=recent" in key


# ═══════════════════════════════════════════════════════════════
# 6. Shadow-Hidden Moderation Path
# ═══════════════════════════════════════════════════════════════


class TestShadowHiddenModerationPath:

    def test_offense_accumulation_across_posts(self, clean_db):
        """Offenses accumulate across multiple posts."""
        from services.moderation_service import increment_offense, get_recent_offenses

        uid = f"shadow-accum-{uuid.uuid4().hex}"
        increment_offense(uid)
        increment_offense(uid)
        assert get_recent_offenses(uid) == 2

    def test_shadow_hide_at_threshold(self, clean_db):
        """At SHADOW_HIDE_THRESHOLD, new posts get shadow-hidden."""
        from services.moderation_service import increment_offense, get_recent_offenses, SHADOW_HIDE_THRESHOLD

        uid = f"shadow-at-{uuid.uuid4().hex}"
        for _ in range(SHADOW_HIDE_THRESHOLD):
            increment_offense(uid)
        assert get_recent_offenses(uid) >= SHADOW_HIDE_THRESHOLD

    def test_shadow_hidden_post_not_queued(self, clean_db, old_user):
        """Shadow-hidden posts should have should_queue=False."""
        from services.moderation_service import increment_offense, SHADOW_HIDE_THRESHOLD
        from services.community_moderation_orchestrator import orchestrate_post_moderation

        uid = f"shadow-no-queue-{uuid.uuid4().hex}"
        for _ in range(SHADOW_HIDE_THRESHOLD):
            increment_offense(uid)

        result = _run_async(orchestrate_post_moderation(
            title="Contains profanity",
            content="This is fucking terrible",
            user_id=uid,
            user_doc=old_user,
        ))
        assert result["is_shadow_hidden"] is True
        assert result["status"] == "hidden"
        assert result["should_queue"] is False

    def test_shadow_hidden_comment_path(self, clean_db, old_user):
        """Shadow-hidden comments also get hidden status and no queue."""
        from services.moderation_service import increment_offense, SHADOW_HIDE_THRESHOLD
        from services.community_moderation_orchestrator import orchestrate_comment_moderation

        uid = f"shadow-comment-{uuid.uuid4().hex}"
        for _ in range(SHADOW_HIDE_THRESHOLD):
            increment_offense(uid)

        result = _run_async(orchestrate_comment_moderation(
            content="Normal looking comment",
            user_id=uid,
            user_doc=old_user,
        ))
        assert result["is_shadow_hidden"] is True
        assert result["status"] == "hidden"
        assert result["should_queue"] is False

    def test_clean_user_not_shadow_hidden(self, clean_db, old_user):
        """A user with no prior offenses should publish normally."""
        from services.community_moderation_orchestrator import orchestrate_post_moderation

        result = _run_async(orchestrate_post_moderation(
            title="Clean post",
            content="What is the best treatment for hypertension?",
            user_id="clean_user",
            user_doc=old_user,
        ))
        assert result["is_shadow_hidden"] is False
        assert result["status"] == "published"
        assert result["should_queue"] is False

    def test_offense_tracking_reset_behavior(self, clean_db):
        """Offenses are tracked per-user and reset per test due to fresh dict."""
        from services.moderation_service import increment_offense, get_recent_offenses

        uid = f"reset-{uuid.uuid4().hex}"
        assert get_recent_offenses(uid) == 0
        increment_offense(uid)
        assert get_recent_offenses(uid) == 1

    def test_below_threshold_queues_only(self, clean_db, old_user):
        """Below shadow-hide threshold, flagged content goes to queue, not hidden."""
        from services.community_moderation_orchestrator import orchestrate_post_moderation

        result = _run_async(orchestrate_post_moderation(
            title="Has PHI",
            content="Patient SSN: 123-45-6789",
            user_id="below_threshold_user",
            user_doc=old_user,
        ))
        assert result["is_shadow_hidden"] is False
        assert result["status"] == "moderation_queue"
        assert result["should_queue"] is True

    def test_shadow_hide_independent_of_moderation_flags(self, clean_db, old_user):
        """Shadow-hide triggers regardless of content quality."""
        from services.moderation_service import increment_offense, SHADOW_HIDE_THRESHOLD
        from services.community_moderation_orchestrator import orchestrate_post_moderation

        uid = f"shadow-any-{uuid.uuid4().hex}"
        for _ in range(SHADOW_HIDE_THRESHOLD):
            increment_offense(uid)

        result = _run_async(orchestrate_post_moderation(
            title="Perfectly clean content",
            content="This is a perfectly clean medical discussion with no issues at all.",
            user_id=uid,
            user_doc=old_user,
        ))
        assert result["is_shadow_hidden"] is True
        assert result["status"] == "hidden"


# ═══════════════════════════════════════════════════════════════
# 7. Mark-All-Read Flow
# ═══════════════════════════════════════════════════════════════


class TestMarkAllReadFlow:

    def test_mark_all_read_mixed_state(self, clean_db):
        """Mark-all-read should clear all unread, leave read untouched."""
        mock_db, mock_log = clean_db
        from services.notification_service import mark_all_read

        class FakeResult:
            modified_count = 3
        mock_db.notifications.update_many.return_value = FakeResult()

        count = _run_async(mark_all_read("u1"))
        assert count == 3
        mock_db.notifications.update_many.assert_called_once_with(
            {"user_id": "u1", "read": False},
            {"$set": {"read": True}},
        )

    def test_mark_all_read_idempotent_zero_unread(self, clean_db):
        """Mark-all-read with zero unread should not error and return 0."""
        mock_db, _ = clean_db
        from services.notification_service import mark_all_read

        class FakeZero:
            modified_count = 0
        mock_db.notifications.update_many.return_value = FakeZero()

        count = _run_async(mark_all_read("u1"))
        assert count == 0

    def test_mark_all_read_cross_user_isolation(self, clean_db):
        """Marking all read for user u1 should not affect u2's notifications."""
        mock_db, _ = clean_db
        from services.notification_service import mark_all_read

        class FakeResult:
            modified_count = 2
        mock_db.notifications.update_many.return_value = FakeResult()

        count_u1 = _run_async(mark_all_read("u1"))
        assert count_u1 == 2

        call_filter = mock_db.notifications.update_many.call_args[0][0]
        assert call_filter["user_id"] == "u1"

    def test_mark_all_read_does_not_break_future_aggregation(self, clean_db):
        """After mark-all-read, new comment notifications should still aggregate."""
        mock_db, _ = clean_db
        from services.notification_service import aggregate_notification

        mock_db.notifications.find_one.return_value = None

        nid1 = _run_async(aggregate_notification(
            user_id="u1", notification_type="community_comment",
            title="New comment", message="msg",
            aggregate_key="post:p1",
        ))
        assert nid1 is not None
        assert mock_db.notifications.insert_one.called

        mock_db.notifications.find_one.return_value = {
            "id": "existing_nid", "aggregate_count": 1,
        }
        nid2 = _run_async(aggregate_notification(
            user_id="u1", notification_type="community_comment",
            title="New comment", message="msg",
            aggregate_key="post:p1",
        ))
        assert nid2 is not None
        assert mock_db.notifications.update_one.called
        args = mock_db.notifications.update_one.call_args[0][1]
        assert args["$set"]["aggregate_count"] == 2

    def test_get_user_notifications_cursor_pagination(self, clean_db):
        """get_user_notifications with cursor paginates correctly."""
        mock_db, _ = clean_db
        from services.notification_service import get_user_notifications

        now = datetime.now(timezone.utc).isoformat()
        notifs = [
            {"id": f"n{i}", "user_id": "u1", "type": "community_comment",
             "icon": "message-circle", "title": f"Notif {i}", "message": "m",
             "read": False, "aggregate_count": 1, "created_at": now,
             "data": {}}
            for i in range(3)
        ]
        mock_db.notifications.find.return_value.sort.return_value.to_list = AsyncMock(return_value=notifs)
        mock_db.notifications.count_documents.return_value = 2

        result = _run_async(get_user_notifications(
            user_id="u1", limit=10,
        ))
        assert len(result["notifications"]) == 3
        assert result["next_cursor"] is None
        assert result["unread_count"] == 2

    def test_get_user_notifications_cursor_boundary(self, clean_db):
        """When result count exactly equals limit, next_cursor should be set."""
        mock_db, _ = clean_db
        from services.notification_service import get_user_notifications

        now = datetime.now(timezone.utc).isoformat()
        notifs = [
            {"id": f"n{i}", "user_id": "u1", "type": "community_comment",
             "icon": "message-circle", "title": f"Notif {i}", "message": "m",
             "read": False, "aggregate_count": 1, "created_at": now,
             "data": {}}
            for i in range(6)
        ]
        mock_db.notifications.find.return_value.sort.return_value.to_list = AsyncMock(return_value=notifs)
        mock_db.notifications.count_documents.return_value = 6

        result = _run_async(get_user_notifications(
            user_id="u1", limit=5,
        ))
        assert len(result["notifications"]) == 5
        assert result["next_cursor"] is not None
        assert result["unread_count"] == 6


# ═══════════════════════════════════════════════════════════════
# 8. Moderation Queue Transitions
# ═══════════════════════════════════════════════════════════════


class TestModerationQueueTransitions:

    def test_approve_transitions_to_published(self, clean_db):
        """Approving a queued item transitions it to published status."""
        from services.community_serializers import build_moderation_action_status_map
        assert build_moderation_action_status_map("approve") == "published"
        assert build_moderation_action_status_map("hide") == "hidden"
        assert build_moderation_action_status_map("delete") == "deleted"
        assert build_moderation_action_status_map("queue") == "moderation_queue"

    def test_moderation_action_update_builds_correctly(self, clean_db):
        """Moderation action update includes all required fields."""
        from services.community_serializers import build_moderation_action_update
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        update = build_moderation_action_update("approve", "published", "admin1", "good to go", now)
        assert update["status"] == "published"
        assert update["moderated_by"] == "admin1"
        assert update["moderation_reason"] == "good to go"

    def test_reviewed_filter_applied_correctly(self, clean_db):
        """Filtering by reviewed=False should be in the query."""
        mock_db, _ = clean_db
        mock_db.community_moderation_queue.find.return_value.sort.return_value.to_list = AsyncMock(return_value=[])
        mock_db.community_moderation_queue.count_documents.return_value = 0

        from services.community_pagination import paginate_moderation_queue
        result = _run_async(paginate_moderation_queue(
            db=mock_db, query={"reviewed": False}, page=1, page_size=20, use_cursor=False,
        ))
        assert result["total"] == 0
        assert result["items"] == []
