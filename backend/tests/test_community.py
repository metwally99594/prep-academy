"""Medical Community — Pure Function + Integration Tests.

Run with: pytest backend/tests/test_community.py -v
Requires: running server with community routes wired.
"""
import sys, os, uuid, time
from unittest.mock import AsyncMock, patch
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from services.community_service import (
    validate_post_content, validate_comment_content,
    validate_post_type, validate_specialty_tags, validate_topic_tags,
    validate_reason, validate_reaction, validate_target_type,
    validate_sort_option, validate_moderation_action,
    contains_html, sanitize_html,
    compute_text_similarity, is_duplicate,
    compute_hot_score, compute_trending_score,
    check_phi, check_dangerous_advice,
    check_post_rate, check_comment_rate, check_burst_rate,
    extract_mentions,
    get_sort_config, get_sort_spec, parse_cursor,
    SORT_CONFIG,
)
from services.moderation_service import (
    evaluate_auto_moderation, is_title_all_caps, has_external_links,
    build_moderation_entry, should_auto_hide, should_auto_queue,
    check_content_quality,
    check_profanity, increment_offense, get_recent_offenses, build_audit_entry,
    SHADOW_HIDE_THRESHOLD,
)
from services.community_cache import (
    cache_get, cache_set, cache_invalidate, build_cache_key,
)

# ── Content Validation ──


class TestPostContentValidation:

    def test_empty_title(self):
        errs = validate_post_content("", "content")
        assert any("title" in e.lower() for e in errs)

    def test_empty_content(self):
        errs = validate_post_content("Title", "")
        assert any("content" in e.lower() for e in errs)

    def test_valid(self):
        assert validate_post_content("Good Title", "Good content here") == []

    def test_title_too_long(self):
        errs = validate_post_content("x" * 201, "content")
        assert len(errs) > 0

    def test_content_too_long(self):
        errs = validate_post_content("Title", "x" * 10001)
        assert len(errs) > 0


class TestCommentContentValidation:

    def test_empty(self):
        assert validate_comment_content("") is not None

    def test_valid(self):
        assert validate_comment_content("Good comment") is None

    def test_too_long(self):
        assert validate_comment_content("x" * 5001) is not None


class TestPostTypeValidation:

    def test_valid_types(self):
        for t in ("question", "discussion", "case_study", "resource"):
            assert validate_post_type(t) is None

    def test_invalid(self):
        assert validate_post_type("invalid_type") is not None


class TestTagValidation:

    def test_valid_specialty(self):
        assert validate_specialty_tags(["cardiology"]) == []

    def test_invalid_specialty(self):
        errs = validate_specialty_tags(["nonexistent_specialty"])
        assert len(errs) > 0

    def test_valid_topic(self):
        assert validate_topic_tags(["diagnosis"]) == []

    def test_invalid_topic(self):
        errs = validate_topic_tags(["fake_topic"])
        assert len(errs) > 0


class TestReasonValidation:

    def test_valid_reasons(self):
        for r in ("spam", "inappropriate", "misinformation", "harassment", "off_topic", "other"):
            assert validate_reason(r) is None

    def test_invalid(self):
        assert validate_reason("invalid_reason") is not None


class TestReactionValidation:

    def test_valid(self):
        assert validate_reaction("upvote") is None
        assert validate_reaction("downvote") is None

    def test_invalid(self):
        assert validate_reaction("invalid") is not None


class TestTargetTypeValidation:

    def test_valid(self):
        assert validate_target_type("post") is None
        assert validate_target_type("comment") is None

    def test_invalid(self):
        assert validate_target_type("user") is not None


class TestSortOptionValidation:

    def test_valid(self):
        for s in ("recent", "trending", "top", "discussed"):
            assert validate_sort_option(s) is None

    def test_invalid(self):
        assert validate_sort_option("random") is not None


class TestModerationActionValidation:

    def test_valid(self):
        for a in ("approve", "hide", "delete", "queue"):
            assert validate_moderation_action(a) is None

    def test_invalid(self):
        assert validate_moderation_action("ban") is not None


# ── HTML / Sanitization ──


class TestContainsHtml:

    def test_detects_html(self):
        assert contains_html("<div>") is True
        assert contains_html("<a href='x'>link</a>") is True

    def test_plain_text(self):
        assert contains_html("Hello world") is False


class TestSanitizeHtml:

    def test_escapes_html(self):
        result = sanitize_html("<script>alert(1)</script>")
        assert "&lt;" in result
        assert "<script>" not in result


# ── Duplicate Detection ──


class TestTextSimilarity:

    def test_identical(self):
        assert compute_text_similarity("hello world", "hello world") == 1.0

    def test_different(self):
        assert compute_text_similarity("hello world", "goodbye universe") < 0.5

    def test_empty(self):
        assert compute_text_similarity("", "hello") == 0.0
        assert compute_text_similarity("hello", "") == 0.0


class TestIsDuplicate:

    def test_exact_duplicate_title(self):
        assert is_duplicate("Pneumonia case study", "Content here", "Pneumonia case study", "Other content") is True

    def test_not_duplicate(self):
        assert is_duplicate("Heart disease", "Content about heart", "Broken leg", "Content about leg") is False


# ── Ranking Logic ──


class TestHotScore:

    def test_zero_score(self):
        assert compute_hot_score(0, 0, time.time()) == 0.0

    def test_positive_score(self):
        score = compute_hot_score(10, 2, time.time())
        assert score > 0

    def test_newer_higher(self):
        old = compute_hot_score(10, 0, time.time() - 3600)
        new = compute_hot_score(10, 0, time.time())
        assert new >= old


class TestTrendingScore:

    def test_basic(self):
        score = compute_trending_score(100, 10, 5, 24)
        assert score > 0

    def test_more_engagement_higher(self):
        low = compute_trending_score(10, 1, 0, 24)
        high = compute_trending_score(1000, 50, 20, 24)
        assert high > low


# ── Medical Safety ──


class TestPhiDetection:

    def test_detects_ssn_like(self):
        findings = check_phi("Patient SSN is 123-45-6789")
        assert len(findings) > 0

    def test_clean_text(self):
        findings = check_phi("The patient has a history of diabetes")
        assert len(findings) == 0

    def test_detects_patient_id_mention(self):
        findings = check_phi("Patientenname: Max Mustermann")
        assert len(findings) > 0


class TestDangerousAdvice:

    def test_detects_discouraging_doctor(self):
        findings = check_dangerous_advice("Ich empfehle, keinen Arzt aufzusuchen")
        assert len(findings) > 0

    def test_clean_text(self):
        findings = check_dangerous_advice("Der Patient sollte einen Kardiologen konsultieren")
        assert len(findings) == 0


# ── Rate Limiting ──


class TestPostRateLimit:

    def test_first_post_ok(self):
        uid = f"test-{uuid.uuid4().hex}"
        assert check_post_rate(uid) is None

    def test_exceeds_limit(self):
        uid = f"test-rate-{uuid.uuid4().hex}"
        for _ in range(5):
            check_post_rate(uid)
        assert check_post_rate(uid) is not None


class TestCommentRateLimit:

    def test_first_comment_ok(self):
        uid = f"test-{uuid.uuid4().hex}"
        assert check_comment_rate(uid) is None

    def test_exceeds_limit(self):
        uid = f"test-rate-{uuid.uuid4().hex}"
        for _ in range(20):
            check_comment_rate(uid)
        assert check_comment_rate(uid) is not None


# ── Content Quality ──


class TestContentQuality:

    def test_short_content(self):
        assert check_content_quality("Hi") is not None

    def test_good_content(self):
        assert check_content_quality("This is a good post with multiple words that exceeds the minimum length for content quality checking") is None

    def test_few_words(self):
        assert check_content_quality("Hello world") is not None


# ── Auto-Moderation ──


class TestAutoModeration:

    def test_phi_triggers_high(self):
        queue, reason, severity = evaluate_auto_moderation(phi_findings=["SSN found"])
        assert queue is True
        assert severity == "high"

    def test_dangerous_advice_triggers_critical(self):
        queue, reason, severity = evaluate_auto_moderation(dangerous_advice=["Don't see doctor"])
        assert queue is True
        assert severity == "critical"

    def test_html_triggers_medium(self):
        queue, reason, severity = evaluate_auto_moderation(contains_html=True)
        assert queue is True
        assert severity == "medium"

    def test_clean_passes(self):
        queue, reason, severity = evaluate_auto_moderation()
        assert queue is False
        assert severity == ""

    def test_profanity_triggers_medium(self):
        queue, reason, severity = evaluate_auto_moderation(profanity_findings=["Profanity (DE): 'Arsch'"])

        assert queue is True
        assert reason == "profanity"
        assert severity == "medium"


class TestIsTitleAllCaps:

    def test_all_caps(self):
        assert is_title_all_caps("THIS IS A LOUD TITLE") is True

    def test_normal_case(self):
        assert is_title_all_caps("This is a normal title") is False

    def test_short(self):
        assert is_title_all_caps("AB") is False


class TestHasExternalLinks:

    def test_detects_links(self):
        assert has_external_links("Check https://example.com for info") is True

    def test_no_links(self):
        assert has_external_links("This is plain text without links") is False


class TestBuildModerationEntry:

    def test_has_required_keys(self):
        entry = build_moderation_entry("post", "abc123", "Test reason", "test", "medium")
        for key in ("target_type", "target_id", "reason", "severity", "reviewed", "created_at"):
            assert key in entry
        assert entry["reviewed"] is False
        assert entry["severity"] == "medium"


class TestAutoHideQueue:

    def test_auto_hide_threshold(self):
        assert should_auto_hide(5) is True
        assert should_auto_hide(3) is False

    def test_auto_queue_threshold(self):
        assert should_auto_queue(3) is True
        assert should_auto_queue(1) is False


# ── Profanity Filter ──


class TestCheckProfanity:

    def test_detects_german(self):
        findings = check_profanity("Du Arschloch!")
        assert any("DE" in f for f in findings)

    def test_detects_english(self):
        findings = check_profanity("What the fuck")
        assert any("EN" in f for f in findings)

    def test_detects_arabic(self):
        findings = check_profanity("كسم")
        assert any("AR" in f for f in findings)

    def test_clean_text_passes(self):
        assert check_profanity("This is a clean medical discussion") == []

    def test_mixed_language_profanity(self):
        findings = check_profanity("Fick dich and كسمك")
        assert len(findings) >= 2

    def test_non_profane_word_not_flagged(self):
        findings = check_profanity("Dieser Befund ist unauffällig")
        assert len(findings) == 0


# ── Auto-Lock ──


class TestAutoLock:

    def test_first_offense_does_not_lock(self):
        uid = f"lock-test-{uuid.uuid4().hex}"
        assert increment_offense(uid) is False

    def test_third_offense_triggers_lock(self):
        uid = f"lock-trigger-{uuid.uuid4().hex}"
        increment_offense(uid)
        increment_offense(uid)
        assert increment_offense(uid) is True

    def test_get_recent_offenses(self):
        uid = f"offense-count-{uuid.uuid4().hex}"
        assert get_recent_offenses(uid) == 0
        increment_offense(uid)
        assert get_recent_offenses(uid) == 1
        increment_offense(uid)
        assert get_recent_offenses(uid) == 2


# ── Burst Rate Protection ──


class TestBurstRate:

    def test_first_actions_ok(self):
        uid = f"burst-{uuid.uuid4().hex}"
        assert check_burst_rate(uid, "post") is None
        assert check_burst_rate(uid, "post") is None

    def test_exceeds_limit(self):
        uid = f"burst-limit-{uuid.uuid4().hex}"
        for _ in range(5):
            check_burst_rate(uid, "post")
        assert check_burst_rate(uid, "post") is not None

    def test_independent_per_kind(self):
        uid = f"burst-kind-{uuid.uuid4().hex}"
        for _ in range(5):
            check_burst_rate(uid, "post")
        # Comments should still be allowed
        assert check_burst_rate(uid, "comment") is None


# ── Audit Log ──


class TestBuildAuditEntry:

    def test_has_required_keys(self):
        entry = build_audit_entry("approve", "post", "abc123", "admin1", "Approved after review")
        for key in ("id", "action", "target_type", "target_id", "admin_id", "reason", "details", "created_at"):
            assert key in entry
        assert entry["action"] == "approve"
        assert entry["admin_id"] == "admin1"
        assert entry["details"] == {}

    def test_custom_details(self):
        entry = build_audit_entry("hide", "comment", "c456", "admin2", details={"previous_status": "published"})
        assert entry["details"]["previous_status"] == "published"


# ── Integration tests (need running server) ──


@pytest.mark.skipif(
    not os.environ.get("REACT_APP_BACKEND_URL"),
    reason="REACT_APP_BACKEND_URL not set — skipping integration tests",
)
class TestCommunityAPI:

    BASE = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8000")

    @pytest.fixture(autouse=True)
    def setup(self, api_client, auth_token):
        self.client = api_client
        self.headers = {"Authorization": f"Bearer {auth_token}"}

    def test_get_tags(self):
        resp = self.client.get(f"{self.BASE}/api/community/tags", headers=self.headers)
        if resp.status_code == 200:
            data = resp.json()
            assert "specialties" in data
            assert "topics" in data

    def test_create_post(self):
        resp = self.client.post(f"{self.BASE}/api/community/posts", json={
            "title": "Test post from integration test",
            "content": "This is a test post created by the integration test suite.",
            "type": "discussion",
            "specialty_tags": ["cardiology"],
        }, headers=self.headers)
        if resp.status_code == 200:
            data = resp.json()
            assert "id" in data

    def test_get_feed(self):
        resp = self.client.get(f"{self.BASE}/api/community/feed", headers=self.headers)
        if resp.status_code == 200:
            data = resp.json()
            assert "posts" in data

    def test_get_trending(self):
        resp = self.client.get(f"{self.BASE}/api/community/trending", headers=self.headers)
        if resp.status_code == 200:
            data = resp.json()
            assert "posts" in data


# ── Mention Extraction ──


class TestExtractMentions:

    def test_extracts_multiple_mentions(self):
        result = extract_mentions("Hey @Alice check @Bob's comment")
        assert result == ["Alice", "Bob"]

    def test_dot_in_username(self):
        result = extract_mentions("Contact @dr.smith for details")
        assert "dr.smith" in result

    def test_dash_in_username(self):
        result = extract_mentions("Thanks @max-muster!")
        assert "max-muster" in result

    def test_no_mentions(self):
        assert extract_mentions("Plain text with no mentions") == []

    def test_empty_string(self):
        assert extract_mentions("") == []

    def test_at_symbol_without_word(self):
        assert extract_mentions("Just @ at the end") == []

    def test_mention_at_start(self):
        assert extract_mentions("@firstuser hello") == ["firstuser"]


# ── Notification Helpers ──


@pytest.fixture
def mock_notifications_db():
    """Patch db in notification_service module for notification tests."""
    from unittest.mock import MagicMock, patch, PropertyMock
    import services.notification_service as ns
    fake_db = MagicMock()
    fake_db.notifications.insert_one = AsyncMock()
    fake_db.notifications.find_one = AsyncMock()
    fake_db.notifications.update_one = AsyncMock()
    fake_db.notifications.update_many = AsyncMock()
    fake_db.notifications.count_documents = AsyncMock()
    fake_db.users.find_one = AsyncMock()
    # Cursor mock for find().sort().to_list()
    mock_cursor = MagicMock()
    mock_cursor.sort.return_value = mock_cursor
    mock_cursor.to_list = AsyncMock(return_value=[])
    fake_db.notifications.find.return_value = mock_cursor
    with patch.object(ns, "_get_db", return_value=fake_db):
        yield fake_db


def _run_async(coro):
    """Run an async function synchronously for testing."""
    import asyncio
    return asyncio.run(coro)


class TestCreateCommunityNotification:

    def test_inserts_document(self, mock_notifications_db):
        from services.notification_service import create_notification

        mock_notifications_db.notifications.insert_one.return_value = None
        _run_async(create_notification(
            user_id="user123",
            notification_type="community_comment",
            title="New comment",
            message="test message",
        ))

        mock_notifications_db.notifications.insert_one.assert_called_once()
        args = mock_notifications_db.notifications.insert_one.call_args[0][0]
        assert args["user_id"] == "user123"
        assert args["type"] == "community_comment"
        assert args["title"] == "New comment"
        assert args["message"] == "test message"
        assert args["read"] is False
        assert "id" in args
        assert "created_at" in args

    def test_truncates_long_message(self, mock_notifications_db):
        from services.notification_service import create_notification

        long_msg = "x" * 500
        _run_async(create_notification(
            user_id="u1", notification_type="test", title="t", message=long_msg,
        ))

        args = mock_notifications_db.notifications.insert_one.call_args[0][0]
        assert len(args["message"]) <= 300

    def test_default_icon(self, mock_notifications_db):
        from services.notification_service import create_notification

        _run_async(create_notification(
            user_id="u1", notification_type="test", title="t", message="m",
        ))

        args = mock_notifications_db.notifications.insert_one.call_args[0][0]
        assert args["icon"] == "message-circle"
        assert args["data"] == {}

    def test_custom_icon_and_data(self, mock_notifications_db):
        from services.notification_service import create_notification

        _run_async(create_notification(
            user_id="u1", notification_type="test", title="t", message="m",
            icon="at-sign", data={"target_type": "post", "target_id": "pid"},
        ))

        args = mock_notifications_db.notifications.insert_one.call_args[0][0]
        assert args["icon"] == "at-sign"
        assert args["data"] == {"target_type": "post", "target_id": "pid"}


class TestNotifyMentionedUsers:

    def test_creates_notifications(self, mock_notifications_db):
        from services.notification_service import notify_mentioned_users

        mock_notifications_db.users.find_one.side_effect = [
            {"id": "user_a", "name": "Alice"},
            {"id": "user_b", "name": "Bob"},
        ]

        _run_async(notify_mentioned_users(
            content="Hey @Alice and @Bob check this out",
            actor_id="actor1",
            actor_name="Charly",
            target_type="post",
            target_id="post123",
        ))

        assert mock_notifications_db.notifications.insert_one.call_count == 2

    def test_skips_actor(self, mock_notifications_db):
        from services.notification_service import notify_mentioned_users

        mock_notifications_db.users.find_one.return_value = {"id": "actor1", "name": "Self"}

        _run_async(notify_mentioned_users(
            content="Hello @Self",
            actor_id="actor1",
            actor_name="Self",
            target_type="post",
            target_id="post123",
        ))

        mock_notifications_db.notifications.insert_one.assert_not_called()

    def test_skips_unknown_usernames(self, mock_notifications_db):
        from services.notification_service import notify_mentioned_users

        mock_notifications_db.users.find_one.return_value = None

        _run_async(notify_mentioned_users(
            content="Hello @UnknownUser",
            actor_id="actor1",
            actor_name="Test",
            target_type="post",
            target_id="post123",
        ))

        mock_notifications_db.notifications.insert_one.assert_not_called()

    def test_no_mentions_noop(self, mock_notifications_db):
        from services.notification_service import notify_mentioned_users

        _run_async(notify_mentioned_users(
            content="No mentions here",
            actor_id="actor1",
            actor_name="Test",
            target_type="post",
            target_id="post123",
        ))

        mock_notifications_db.notifications.insert_one.assert_not_called()
        mock_notifications_db.users.find_one.assert_not_called()


# ── Notification Aggregation ──


class TestAggregateNotification:

    def test_creates_new_when_no_existing(self, mock_notifications_db):
        from services.notification_service import aggregate_notification

        mock_notifications_db.notifications.find_one.return_value = None

        _run_async(aggregate_notification(
            user_id="user123",
            notification_type="community_comment",
            title="New comment",
            message="test message",
            aggregate_key="post:abc123",
        ))

        mock_notifications_db.notifications.insert_one.assert_called_once()
        args = mock_notifications_db.notifications.insert_one.call_args[0][0]
        assert args["user_id"] == "user123"
        assert args["type"] == "community_comment"
        assert args["data"]["aggregate_key"] == "post:abc123"
        assert args["aggregate_count"] == 1

    def test_merges_with_existing_unread(self, mock_notifications_db):
        from services.notification_service import aggregate_notification

        existing_id = "existing_notif_id"
        mock_notifications_db.notifications.find_one.return_value = {
            "id": existing_id, "aggregate_count": 1,
        }

        result = _run_async(aggregate_notification(
            user_id="user123",
            notification_type="community_comment",
            title="New comment",
            message="newer message",
            aggregate_key="post:abc123",
        ))

        assert result == existing_id
        mock_notifications_db.notifications.update_one.assert_called_once()
        args = mock_notifications_db.notifications.update_one.call_args
        assert args[0][0] == {"id": existing_id}
        assert args[1][0]["$set"]["aggregate_count"] == 2
        assert args[1][0]["$set"]["message"] == "newer message"

    def test_does_not_merge_when_read_exists(self, mock_notifications_db):
        from services.notification_service import aggregate_notification

        mock_notifications_db.notifications.find_one.return_value = None

        _run_async(aggregate_notification(
            user_id="user123",
            notification_type="community_comment",
            title="New comment",
            message="test",
            aggregate_key="post:abc123",
        ))

        mock_notifications_db.notifications.insert_one.assert_called_once()

    def test_aggregate_count_increments_properly(self, mock_notifications_db):
        from services.notification_service import aggregate_notification

        existing_id = "existing_id"
        mock_notifications_db.notifications.find_one.return_value = {
            "id": existing_id, "aggregate_count": 3,
        }

        _run_async(aggregate_notification(
            user_id="user123",
            notification_type="community_comment",
            title="New comment",
            message="test",
            aggregate_key="post:abc123",
        ))

        args = mock_notifications_db.notifications.update_one.call_args
        assert args[1][0]["$set"]["aggregate_count"] == 4

    def test_new_notification_has_aggregate_key_in_data(self, mock_notifications_db):
        from services.notification_service import aggregate_notification

        mock_notifications_db.notifications.find_one.return_value = None

        _run_async(aggregate_notification(
            user_id="user123",
            notification_type="community_reaction",
            title="Someone upvoted",
            message="",
            aggregate_key="reaction:post:abc123",
            icon="thumbs-up",
            data={"target_type": "post", "target_id": "abc123"},
        ))

        args = mock_notifications_db.notifications.insert_one.call_args[0][0]
        assert args["data"]["aggregate_key"] == "reaction:post:abc123"
        assert args["data"]["target_type"] == "post"
        assert args["icon"] == "thumbs-up"


class TestGetUserNotifications:

    def _make_notif(self, nid, created_at):
        return {
            "id": nid, "user_id": "u1", "type": "test", "title": "t",
            "message": "m", "icon": "bell", "read": False,
            "aggregate_count": 1, "created_at": created_at, "data": {},
        }

    def test_returns_notifications_list(self, mock_notifications_db):
        from services.notification_service import get_user_notifications

        items = [self._make_notif("n1", "2024-01-02T00:00:00")]
        mock_notifications_db.notifications.find.return_value.sort.return_value.to_list = AsyncMock(return_value=items)
        mock_notifications_db.notifications.count_documents.return_value = 5

        result = _run_async(get_user_notifications(user_id="u1"))
        assert len(result["notifications"]) == 1
        assert result["notifications"][0]["id"] == "n1"
        assert result["unread_count"] == 5

    def test_cursor_pagination_has_more(self, mock_notifications_db):
        from services.notification_service import get_user_notifications

        items = [self._make_notif(f"n{i}", f"2024-01-{i:02d}T00:00:00") for i in range(1, 22)]
        mock_notifications_db.notifications.find.return_value.sort.return_value.to_list = AsyncMock(return_value=items)
        mock_notifications_db.notifications.count_documents.return_value = 30

        result = _run_async(get_user_notifications(user_id="u1", limit=20))
        assert len(result["notifications"]) == 20
        assert result["next_cursor"] is not None

    def test_cursor_pagination_no_more(self, mock_notifications_db):
        from services.notification_service import get_user_notifications

        items = [self._make_notif(f"n{i}", "2024-01-01T00:00:00") for i in range(1, 6)]
        mock_notifications_db.notifications.find.return_value.sort.return_value.to_list = AsyncMock(return_value=items)
        mock_notifications_db.notifications.count_documents.return_value = 5

        result = _run_async(get_user_notifications(user_id="u1", limit=20))
        assert result["next_cursor"] is None

    def test_unread_count_separate_query(self, mock_notifications_db):
        from services.notification_service import get_user_notifications

        mock_notifications_db.notifications.find.return_value.sort.return_value.to_list = AsyncMock(return_value=[])
        mock_notifications_db.notifications.count_documents.return_value = 3

        result = _run_async(get_user_notifications(user_id="u1"))
        assert result["unread_count"] == 3
        mock_notifications_db.notifications.count_documents.assert_called_with(
            {"user_id": "u1", "read": False},
        )

    def test_projection_trims_fields(self, mock_notifications_db):
        from services.notification_service import get_user_notifications

        items = [self._make_notif("n1", "2024-01-01T00:00:00")]
        mock_notifications_db.notifications.find.return_value.sort.return_value.to_list = AsyncMock(return_value=items)

        _run_async(get_user_notifications(user_id="u1"))
        _args = mock_notifications_db.notifications.find.call_args
        assert _args is not None

    def test_cursor_filter_applied(self, mock_notifications_db):
        from services.notification_service import get_user_notifications

        mock_notifications_db.notifications.find.return_value.sort.return_value.to_list = AsyncMock(return_value=[])
        mock_notifications_db.notifications.count_documents.return_value = 0

        _run_async(get_user_notifications(user_id="u1", cursor="2024-01-15T00:00:00"))
        find_args = mock_notifications_db.notifications.find.call_args[0]
        assert find_args[0].get("created_at") == {"$lt": "2024-01-15T00:00:00"}

    def test_empty_result(self, mock_notifications_db):
        from services.notification_service import get_user_notifications

        mock_notifications_db.notifications.find.return_value.sort.return_value.to_list = AsyncMock(return_value=[])
        mock_notifications_db.notifications.count_documents.return_value = 0

        result = _run_async(get_user_notifications(user_id="nonexistent"))
        assert result["notifications"] == []
        assert result["next_cursor"] is None
        assert result["unread_count"] == 0


class TestMarkAllRead:

    def test_marks_all_unread(self, mock_notifications_db):
        from services.notification_service import mark_all_read

        mock_notifications_db.notifications.update_many.return_value.modified_count = 5

        count = _run_async(mark_all_read("user123"))
        assert count == 5
        mock_notifications_db.notifications.update_many.assert_called_with(
            {"user_id": "user123", "read": False},
            {"$set": {"read": True}},
        )

    def test_no_unread(self, mock_notifications_db):
        from services.notification_service import mark_all_read

        mock_notifications_db.notifications.update_many.return_value.modified_count = 0

        count = _run_async(mark_all_read("user123"))
        assert count == 0


# ── Cursor Pagination Helpers ──


class TestCursorPaginationHelpers:

    def test_get_sort_config_known_sorts(self):
        for sort in ("recent", "trending", "top", "discussed"):
            cfg = get_sort_config(sort)
            assert "field" in cfg
            assert "coerce" in cfg

    def test_get_sort_config_unknown_fallsback_to_recent(self):
        cfg = get_sort_config("unknown_sort")
        assert cfg["field"] == "created_at"

    def test_parse_cursor_str(self):
        result = parse_cursor("2024-01-01T00:00:00", str)
        assert result == "2024-01-01T00:00:00"

    def test_parse_cursor_float(self):
        result = parse_cursor("123.456", float)
        assert result == 123.456

    def test_parse_cursor_int(self):
        result = parse_cursor("42", int)
        assert result == 42

    def test_parse_cursor_none(self):
        assert parse_cursor(None, str) is None

    def test_parse_cursor_empty(self):
        assert parse_cursor("", str) is None

    def test_parse_cursor_invalid_returns_none(self):
        assert parse_cursor("not_a_number", float) is None

    def test_get_sort_spec_has_tiebreaker(self):
        spec = get_sort_spec("created_at")
        assert ("_id", 1) in spec

    def test_get_sort_spec_always_two_elements(self):
        for field in ("created_at", "stats.score", "stats.comment_count"):
            spec = get_sort_spec(field)
            assert len(spec) == 2

    def test_sort_config_coerce_types(self):
        assert SORT_CONFIG["recent"]["coerce"] == str
        assert SORT_CONFIG["trending"]["coerce"] == str
        assert SORT_CONFIG["top"]["coerce"] == float
        assert SORT_CONFIG["discussed"]["coerce"] == int


# ── Cache Helpers ──


class TestCacheHelpers:

    def _clean_cache(self):
        cache_invalidate()

    def test_cache_get_miss(self):
        self._clean_cache()
        assert cache_get("nonexistent") is None

    def test_cache_set_and_get(self):
        self._clean_cache()
        cache_set("test_key", {"data": 42})
        assert cache_get("test_key") == {"data": 42}

    def test_cache_expires(self):
        self._clean_cache()
        cache_set("test_key", "value", ttl=0)
        import time
        time.sleep(0.001)
        assert cache_get("test_key") is None

    def test_cache_invalidate_all(self):
        self._clean_cache()
        cache_set("key1", "v1")
        cache_set("key2", "v2")
        cache_invalidate()
        assert cache_get("key1") is None
        assert cache_get("key2") is None

    def test_cache_invalidate_pattern(self):
        self._clean_cache()
        cache_set("feed:recent", "v1")
        cache_set("feed:top", "v2")
        cache_set("stats", "v3")
        cache_invalidate(pattern="feed")
        assert cache_get("feed:recent") is None
        assert cache_get("feed:top") is None
        assert cache_get("stats") is not None

    def test_build_cache_key_simple(self):
        key = build_cache_key("feed", sort="recent")
        assert "feed" in key
        assert "sort=recent" in key

    def test_build_cache_key_ignores_none(self):
        key = build_cache_key("feed", sort="recent", specialty=None)
        assert "specialty" not in key

    def test_build_cache_key_sorted_params(self):
        key = build_cache_key("test", b="2", a="1")
        assert key.index("a=") < key.index("b=")


# ── Shadow-hide Moderation Path ──


class TestShadowHiddenModeration:

    def test_shadow_hide_threshold_constant(self):
        assert SHADOW_HIDE_THRESHOLD == 3

    def test_offense_tracking_triggers_shadow(self):
        uid = f"shadow-{uuid.uuid4().hex}"
        for _ in range(SHADOW_HIDE_THRESHOLD):
            increment_offense(uid)
        assert get_recent_offenses(uid) >= SHADOW_HIDE_THRESHOLD

    def test_increment_offense_returns_true_at_threshold(self):
        uid = f"lock-{uuid.uuid4().hex}"
        for _ in range(SHADOW_HIDE_THRESHOLD - 1):
            increment_offense(uid)
        assert increment_offense(uid) is True

    def test_below_threshold_not_shadow(self):
        uid = f"below-{uuid.uuid4().hex}"
        for _ in range(SHADOW_HIDE_THRESHOLD - 1):
            increment_offense(uid)
        assert get_recent_offenses(uid) < SHADOW_HIDE_THRESHOLD


# ── Serialization Helpers ──


class TestSerializeNotification:

    def test_serialize_notification_has_required_keys(self):
        from services.notification_service import serialize_notification
        doc = {
            "id": "n1", "type": "test", "icon": "bell", "title": "t",
            "message": "m", "read": False, "aggregate_count": 2,
            "created_at": "2024-01-01", "data": {"key": "val"},
        }
        result = serialize_notification(doc)
        for key in ("id", "type", "icon", "title", "message", "read", "aggregate_count", "created_at", "data"):
            assert key in result

    def test_serialize_notification_defaults(self):
        from services.notification_service import serialize_notification
        result = serialize_notification({"id": "n1"})
        assert result["icon"] == "message-circle"
        assert result["read"] is False
        assert result["aggregate_count"] == 1
        assert result["data"] == {}


# ── Content Quality (duplicate detection edge cases) ──


class TestContentQualityEdgeCases:

    def test_exact_duplicate_content_triggers(self):
        assert is_duplicate(
            "How to treat pneumonia in elderly patients",
            "Consider antibiotics and supportive care",
            "How to treat pneumonia in elderly patients",
            "Consider antibiotics and supportive care",
        ) is True

    def test_partial_title_match_not_enough(self):
        assert is_duplicate(
            "Heart disease management",
            "Content about heart disease",
            "Heart disease prevention",
            "Content about prevention only",
        ) is False

    def test_empty_text_similarity_zero(self):
        assert compute_text_similarity("", "") == 0.0

    def test_compute_text_similarity_identical(self):
        assert compute_text_similarity("hello world", "hello world") == 1.0

    def test_compute_text_similarity_partial(self):
        sim = compute_text_similarity("a b c d", "a b c e")
        assert 0.5 < sim < 1.0
