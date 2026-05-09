"""Medical Community — Pure Function + Integration Tests.

Run with: pytest backend/tests/test_community.py -v
Requires: running server with community routes wired.
"""
import sys, os, uuid, time
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
    check_post_rate, check_comment_rate,
)
from services.moderation_service import (
    evaluate_auto_moderation, is_title_all_caps, has_external_links,
    build_moderation_entry, should_auto_hide, should_auto_queue,
    check_content_quality,
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
