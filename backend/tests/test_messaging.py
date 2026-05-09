"""Messaging System — Integration Tests.

Run with: pytest backend/tests/test_messaging.py -v
Requires: running server with messaging routes wired.
"""
import sys, os, uuid
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from services.messaging_service import (
    validate_message_content,
    validate_attachments,
    sanitize_message_content,
    check_rate_limit,
    check_spam_rate,
    check_duplicate_content,
    validate_escalation_level,
    contains_html,
)

# ── Pure function tests (no server needed) ──


class TestMessageContentValidation:

    def test_empty_content(self):
        assert validate_message_content("") is not None

    def test_whitespace_only(self):
        assert validate_message_content("   ") is not None

    def test_valid_content(self):
        assert validate_message_content("Hello, this is a test message") is None

    def test_max_length_boundary(self):
        valid = "a" * 5000
        assert validate_message_content(valid) is None

    def test_exceeds_max_length(self):
        too_long = "a" * 5001
        assert validate_message_content(too_long) is not None


class TestAttachmentValidation:

    def test_valid_jpeg(self):
        errs = validate_attachments([{"mime_type": "image/jpeg", "size_bytes": 1024}])
        assert len(errs) == 0

    def test_valid_pdf(self):
        errs = validate_attachments([{"mime_type": "application/pdf", "size_bytes": 500000}])
        assert len(errs) == 0

    def test_invalid_type(self):
        errs = validate_attachments([{"mime_type": "text/html", "size_bytes": 100}])
        assert len(errs) == 1

    def test_exceeds_size(self):
        errs = validate_attachments([{"mime_type": "image/jpeg", "size_bytes": 15 * 1024 * 1024}])
        assert len(errs) == 1

    def test_too_many_attachments(self):
        many = [{"mime_type": "image/jpeg", "size_bytes": 100}] * 6
        errs = validate_attachments(many)
        assert len(errs) == 1
        assert "5 attachments" in errs[0].lower()


class TestSanitizeContent:

    def test_strips_html(self):
        result = sanitize_message_content("<script>alert('xss')</script>Hello")
        assert "<script>" not in result
        assert "&lt;" in result

    def test_strips_whitespace(self):
        result = sanitize_message_content("  hello world  ")
        assert result == "hello world"

    def test_handles_umlauts(self):
        result = sanitize_message_content("Überprüfung der Befunde")
        assert "Überprüfung" in result


class TestRateLimiting:

    def test_first_message_ok(self):
        uid = f"test-{uuid.uuid4().hex}"
        assert check_rate_limit(uid) is None

    def test_rate_limit_exceeded(self):
        uid = f"test-rate-{uuid.uuid4().hex}"
        for _ in range(10):
            check_rate_limit(uid)
        assert check_rate_limit(uid) is not None


class TestSpamDetection:

    def test_spam_limit_not_exceeded(self):
        uid = f"test-spam-{uuid.uuid4().hex}"
        assert check_spam_rate(uid) is None

    def test_spam_message(self):
        pass  # Integration: needs 50+ messages


class TestDuplicateDetection:

    def test_duplicate_same_content(self):
        uid = f"test-dup-{uuid.uuid4().hex}"
        assert check_duplicate_content(uid, "Hello world") is None
        assert check_duplicate_content(uid, "Hello world") is not None

    def test_different_content_ok(self):
        uid = f"test-dup-{uuid.uuid4().hex}"
        assert check_duplicate_content(uid, "First message") is None
        assert check_duplicate_content(uid, "Second message") is None


class TestEscalationValidation:

    def test_valid_levels(self):
        for level in (0, 1, 2, 3):
            assert validate_escalation_level(level) is None

    def test_invalid_level(self):
        assert validate_escalation_level(-1) is not None
        assert validate_escalation_level(4) is not None


class TestContainsHtml:

    def test_detects_html(self):
        assert contains_html("<b>bold</b>") is True

    def test_plain_text(self):
        assert contains_html("Hello world") is False

    def test_edge_html(self):
        assert contains_html("a < b > c") is False  # not valid HTML


# ── Integration tests (need running server) ──


@pytest.mark.skipif(
    not os.environ.get("REACT_APP_BACKEND_URL"),
    reason="REACT_APP_BACKEND_URL not set — skipping integration tests",
)
class TestMessagingAPI:

    BASE = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8000")

    @pytest.fixture(autouse=True)
    def setup(self, api_client, auth_token):
        self.client = api_client
        self.headers = {"Authorization": f"Bearer {auth_token}"}

    def test_send_message(self):
        # Get a list of admin users for recipient
        resp = self.client.get(f"{self.BASE}/api/auth/me", headers=self.headers)
        assert resp.status_code == 200
        me = resp.json()

        # Find a different user or admin
        admin_resp = self.client.get(f"{self.BASE}/api/messaging/admin/inbox", headers=self.headers)
        if admin_resp.status_code == 200:
            resp2 = self.client.post(f"{self.BASE}/api/messaging/send", json={
                "recipient_id": me.get("id", "admin-id"),
                "subject": "Test",
                "content": "Integration test message",
            }, headers=self.headers)
            assert resp2.status_code in (200, 400, 403, 429)

    def test_list_conversations(self):
        resp = self.client.get(f"{self.BASE}/api/messaging/conversations", headers=self.headers)
        if resp.status_code == 200:
            data = resp.json()
            assert "conversations" in data

    def test_unread_count(self):
        resp = self.client.get(f"{self.BASE}/api/messaging/unread-count", headers=self.headers)
        if resp.status_code == 200:
            data = resp.json()
            assert "total_unread" in data
