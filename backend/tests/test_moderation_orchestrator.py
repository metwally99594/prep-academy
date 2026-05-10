"""Tests for community_moderation_orchestrator.py.

Run with: pytest backend/tests/test_moderation_orchestrator.py -v
"""
import os, sys, uuid, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Set env vars BEFORE any database import
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")

from unittest.mock import AsyncMock, MagicMock, patch
import pytest


@pytest.fixture(autouse=True)
def mock_db_and_logger():
    """Mock database.db and database.logger before each test.

    The orchestrator imports from database at module level, so we patch
    both db and logger to avoid needing a real MongoDB connection.
    """
    with patch("database.logger") as mock_log, \
         patch("database.db") as mock_db:
        mock_db.community_moderation_queue.insert_one = AsyncMock()
        mock_db.community_posts.find_one = AsyncMock()
        mock_db.community_comments.find_one = AsyncMock()
        mock_db.community_posts.update_one = AsyncMock()
        mock_db.community_comments.update_one = AsyncMock()
        yield mock_db, mock_log


@pytest.fixture
def old_user_doc():
    return {"created_at": "2020-01-01T00:00:00"}


@pytest.fixture
def new_user_doc():
    return {"created_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())}


@pytest.fixture
def clean_content():
    return "What is the best approach to treat hypertension in diabetic patients?"


def _run_async(coro):
    import asyncio
    return asyncio.run(coro)


class TestOrchestratePostModeration:

    def test_clean_post_publishes(self, clean_content, old_user_doc):
        from services.community_moderation_orchestrator import orchestrate_post_moderation

        result = _run_async(orchestrate_post_moderation(
            title="Hypertension Management",
            content=clean_content,
            user_id="user123",
            user_doc=old_user_doc,
        ))
        assert result["status"] == "published"
        assert result["should_queue"] is False
        assert result["is_shadow_hidden"] is False

    def test_phi_triggers_queue(self, old_user_doc):
        from services.community_moderation_orchestrator import orchestrate_post_moderation

        result = _run_async(orchestrate_post_moderation(
            title="Patient case",
            content="Patient SSN is 123-45-6789 and has diabetes",
            user_id="user123",
            user_doc=old_user_doc,
        ))
        assert result["status"] == "moderation_queue"
        assert result["should_queue"] is True
        assert "PHI" in (result["moderation_reason"] or "")

    def test_dangerous_advice_triggers_critical_queue(self, old_user_doc):
        from services.community_moderation_orchestrator import orchestrate_post_moderation

        result = _run_async(orchestrate_post_moderation(
            title="Treatment advice",
            content="Ich empfehle, keinen Arzt aufzusuchen bei diesen Symptomen",
            user_id="user123",
            user_doc=old_user_doc,
        ))
        assert result["status"] == "moderation_queue"
        assert result["should_queue"] is True

    def test_profanity_triggers_queue(self, old_user_doc):
        from services.community_moderation_orchestrator import orchestrate_post_moderation

        result = _run_async(orchestrate_post_moderation(
            title="Frustrated post",
            content="This is fucking ridiculous, these guidelines are wrong",
            user_id="user123",
            user_doc=old_user_doc,
        ))
        assert result["status"] == "moderation_queue"
        assert result["should_queue"] is True

    def test_all_caps_title_triggers_queue(self, old_user_doc):
        from services.community_moderation_orchestrator import orchestrate_post_moderation

        result = _run_async(orchestrate_post_moderation(
            title="THIS IS A VERY LOUD TITLE ABOUT MEDICINE",
            content="Normal content about medicine",
            user_id="user123",
            user_doc=old_user_doc,
        ))
        assert result["should_queue"] is True

    def test_sanitizes_html_in_content(self, old_user_doc):
        from services.community_moderation_orchestrator import orchestrate_post_moderation

        result = _run_async(orchestrate_post_moderation(
            title="Safe title",
            content="<script>alert('xss')</script>Normal content",
            user_id="user123",
            user_doc=old_user_doc,
        ))
        assert "&lt;" in result["sanitized_content"]
        assert "<script>" not in result["sanitized_content"]

    def test_queues_when_new_user_posts_links(self, new_user_doc):
        from services.community_moderation_orchestrator import orchestrate_post_moderation

        result = _run_async(orchestrate_post_moderation(
            title="Great resource",
            content="Check out https://example.com for more info",
            user_id="newuser123",
            user_doc=new_user_doc,
        ))
        assert result["should_queue"] is True

    def test_shadow_hides_when_offenses_exceed_threshold(self, old_user_doc):
        from services.moderation_service import increment_offense, SHADOW_HIDE_THRESHOLD
        from services.community_moderation_orchestrator import orchestrate_post_moderation

        uid = f"shadow-test-{uuid.uuid4().hex}"
        for _ in range(SHADOW_HIDE_THRESHOLD):
            increment_offense(uid)

        result = _run_async(orchestrate_post_moderation(
            title="Another post",
            content="Just some content",
            user_id=uid,
            user_doc=old_user_doc,
        ))
        assert result["is_shadow_hidden"] is True
        assert result["status"] == "hidden"
        assert result["should_queue"] is False

    def test_shadow_hidden_posts_get_hidden_status_not_queued(self, old_user_doc):
        from services.moderation_service import increment_offense, SHADOW_HIDE_THRESHOLD
        from services.community_moderation_orchestrator import orchestrate_post_moderation

        uid = f"shadow-queue-{uuid.uuid4().hex}"
        for _ in range(SHADOW_HIDE_THRESHOLD):
            increment_offense(uid)

        result = _run_async(orchestrate_post_moderation(
            title="Contains profanity",
            content="This is fucking ridiculous",
            user_id=uid,
            user_doc=old_user_doc,
        ))
        assert result["is_shadow_hidden"] is True
        assert result["status"] == "hidden"
        assert result["should_queue"] is False

    def test_moderation_reason_set_when_queued(self, old_user_doc):
        from services.community_moderation_orchestrator import orchestrate_post_moderation

        result = _run_async(orchestrate_post_moderation(
            title="PHI case",
            content="Patient SSN is 123-45-6789",
            user_id="user123",
            user_doc=old_user_doc,
        ))
        assert result["moderation_reason"] is not None
        assert len(result["moderation_reason"]) > 0

    def test_moderation_reason_none_when_published(self, clean_content, old_user_doc):
        from services.community_moderation_orchestrator import orchestrate_post_moderation

        result = _run_async(orchestrate_post_moderation(
            title="Normal post",
            content=clean_content,
            user_id="user123",
            user_doc=old_user_doc,
        ))
        assert result["moderation_reason"] is None


class TestOrchestrateCommentModeration:

    def test_clean_comment_publishes(self, old_user_doc):
        from services.community_moderation_orchestrator import orchestrate_comment_moderation

        result = _run_async(orchestrate_comment_moderation(
            content="Great post, thanks for sharing!",
            user_id="user123",
            user_doc=old_user_doc,
        ))
        assert result["status"] == "published"
        assert result["should_queue"] is False

    def test_profanity_comment_triggers_queue(self, old_user_doc):
        from services.community_moderation_orchestrator import orchestrate_comment_moderation

        result = _run_async(orchestrate_comment_moderation(
            content="This is fucking stupid",
            user_id="user123",
            user_doc=old_user_doc,
        ))
        assert result["should_queue"] is True

    def test_comment_sanitizes_html(self, old_user_doc):
        from services.community_moderation_orchestrator import orchestrate_comment_moderation

        result = _run_async(orchestrate_comment_moderation(
            content="<b>bold</b> and <script>alert(1)</script>",
            user_id="user123",
            user_doc=old_user_doc,
        ))
        assert "&lt;" in result["sanitized_content"]
        assert "<b>" not in result["sanitized_content"]

    def test_comment_shadow_hidden_when_offenses_exceed(self, old_user_doc):
        from services.moderation_service import increment_offense, SHADOW_HIDE_THRESHOLD
        from services.community_moderation_orchestrator import orchestrate_comment_moderation

        uid = f"shadow-comment-{uuid.uuid4().hex}"
        for _ in range(SHADOW_HIDE_THRESHOLD):
            increment_offense(uid)

        result = _run_async(orchestrate_comment_moderation(
            content="Normal comment",
            user_id=uid,
            user_doc=old_user_doc,
        ))
        assert result["is_shadow_hidden"] is True
        assert result["status"] == "hidden"

    def test_comment_empty_content_returns_published(self, old_user_doc):
        from services.community_moderation_orchestrator import orchestrate_comment_moderation

        result = _run_async(orchestrate_comment_moderation(
            content="",
            user_id="user123",
            user_doc=old_user_doc,
        ))
        assert result["status"] == "published"


class TestHandleModerationQueueInsert:

    def test_inserts_queue_entry(self, mock_db_and_logger):
        mock_db, mock_log = mock_db_and_logger
        from services.community_moderation_orchestrator import handle_moderation_queue_insert

        _run_async(handle_moderation_queue_insert(
            target_type="post",
            target_id="post123",
            reason="Contains profanity",
            reason_key="profanity",
            severity="medium",
            user_id="user123",
        ))

        mock_db.community_moderation_queue.insert_one.assert_called_once()
        args = mock_db.community_moderation_queue.insert_one.call_args[0][0]
        assert args["target_type"] == "post"
        assert args["target_id"] == "post123"
        assert args["severity"] == "medium"
        assert args["reviewed"] is False

    def test_logs_on_db_error(self, mock_db_and_logger):
        mock_db, mock_log = mock_db_and_logger
        from services.community_moderation_orchestrator import handle_moderation_queue_insert

        mock_db.community_moderation_queue.insert_one.side_effect = Exception("DB error")

        _run_async(handle_moderation_queue_insert(
            target_type="post", target_id="p1",
            reason="test", reason_key="test", severity="low",
            user_id="u1",
        ))
        mock_log.warning.assert_called()


class TestHandleReportModeration:

    def test_auto_hides_at_threshold(self, mock_db_and_logger):
        mock_db, _ = mock_db_and_logger
        mock_db.community_posts.find_one.return_value = {
            "stats": {"report_count": 5}
        }
        from services.community_moderation_orchestrator import handle_report_moderation

        _run_async(handle_report_moderation(
            target_type="post", target_id="post123", reason="spam",
        ))

        mock_db.community_posts.update_one.assert_called_once()
        args = mock_db.community_posts.update_one.call_args
        assert args[0][1]["$set"]["status"] == "hidden"

    def test_auto_queues_at_lower_threshold(self, mock_db_and_logger):
        mock_db, _ = mock_db_and_logger
        mock_db.community_posts.find_one.return_value = {
            "stats": {"report_count": 3}
        }
        mock_db.community_moderation_queue.find_one.return_value = None
        from services.community_moderation_orchestrator import handle_report_moderation

        _run_async(handle_report_moderation(
            target_type="post", target_id="post456", reason="inappropriate",
        ))

        mock_db.community_moderation_queue.insert_one.assert_called_once()

    def test_does_not_duplicate_queue_entry(self, mock_db_and_logger):
        mock_db, _ = mock_db_and_logger
        mock_db.community_posts.find_one.return_value = {
            "stats": {"report_count": 3}
        }
        mock_db.community_moderation_queue.find_one.return_value = {"id": "existing"}
        from services.community_moderation_orchestrator import handle_report_moderation

        _run_async(handle_report_moderation(
            target_type="post", target_id="post456", reason="spam",
        ))

        mock_db.community_moderation_queue.insert_one.assert_not_called()

    def test_skips_when_target_not_found(self, mock_db_and_logger):
        mock_db, _ = mock_db_and_logger
        mock_db.community_posts.find_one.return_value = None
        from services.community_moderation_orchestrator import handle_report_moderation

        _run_async(handle_report_moderation(
            target_type="post", target_id="nonexistent", reason="spam",
        ))

        mock_db.community_posts.update_one.assert_not_called()


# ── Reaction Toggle (extracted to community_service) ──


class TestHandleReactionToggle:

    def test_first_upvote_inserts_reaction(self, mock_db_and_logger):
        mock_db, _ = mock_db_and_logger
        mock_db.community_posts.find_one.return_value = {"author_id": "author123"}
        mock_db.community_reactions.find_one.return_value = None
        from services.community_service import handle_reaction_toggle

        result = _run_async(handle_reaction_toggle(
            user_id="user123",
            target_type="post",
            target_id="post123",
            reaction="upvote",
        ))

        assert result["found"] is True
        assert result["delta"] == 1
        assert result["score_delta"] == 1
        assert result["had_race"] is False
        assert result["target_author_id"] == "author123"
        mock_db.community_reactions.insert_one.assert_called_once()

    def test_remove_reaction_on_duplicate(self, mock_db_and_logger):
        mock_db, _ = mock_db_and_logger
        mock_db.community_posts.find_one.return_value = {"author_id": "author123"}
        mock_db.community_reactions.find_one.return_value = {
            "id": "reaction1", "reaction": "upvote",
        }
        from services.community_service import handle_reaction_toggle

        result = _run_async(handle_reaction_toggle(
            user_id="user123",
            target_type="post",
            target_id="post123",
            reaction="upvote",
        ))

        assert result["delta"] == -1
        assert result["score_delta"] == -1
        mock_db.community_reactions.delete_one.assert_called_once()

    def test_switch_from_upvote_to_downvote(self, mock_db_and_logger):
        mock_db, _ = mock_db_and_logger
        mock_db.community_posts.find_one.return_value = {"author_id": "author123"}
        mock_db.community_reactions.find_one.return_value = {
            "id": "reaction1", "reaction": "upvote",
        }
        from services.community_service import handle_reaction_toggle

        result = _run_async(handle_reaction_toggle(
            user_id="user123",
            target_type="post",
            target_id="post123",
            reaction="downvote",
        ))

        assert result["delta"] == -1  # downvote value is -1
        assert result["score_delta"] == -2  # switching: -1 (remove up) + -1 (add down) = -2
        mock_db.community_reactions.update_one.assert_called_once()

    def test_returns_not_found_when_target_missing(self, mock_db_and_logger):
        mock_db, _ = mock_db_and_logger
        mock_db.community_posts.find_one.return_value = None
        from services.community_service import handle_reaction_toggle

        result = _run_async(handle_reaction_toggle(
            user_id="user123",
            target_type="post",
            target_id="nonexistent",
            reaction="upvote",
        ))

        assert result["found"] is False

    def test_reaction_on_comment(self, mock_db_and_logger):
        mock_db, _ = mock_db_and_logger
        mock_db.community_comments.find_one.return_value = {"author_id": "author123"}
        mock_db.community_reactions.find_one.return_value = None
        from services.community_service import handle_reaction_toggle

        result = _run_async(handle_reaction_toggle(
            user_id="user123",
            target_type="comment",
            target_id="comment123",
            reaction="upvote",
        ))

        assert result["found"] is True
        mock_db.community_comments.find_one.assert_called_once()

    def test_score_update_for_switch(self, mock_db_and_logger):
        mock_db, _ = mock_db_and_logger
        mock_db.community_posts.find_one.return_value = {"author_id": "author123"}
        mock_db.community_reactions.find_one.return_value = {
            "id": "r1", "reaction": "downvote",
        }
        from services.community_service import handle_reaction_toggle

        result = _run_async(handle_reaction_toggle(
            user_id="user123",
            target_type="post",
            target_id="post123",
            reaction="upvote",
        ))

        assert result["delta"] == 1
        assert result["score_delta"] == 2
        # Old downvote removed: inc stats.downvote_count by -1, stats.score by +1
        # New upvote added: inc stats.upvote_count by +1, stats.score by +1
        # Total score delta: +2
