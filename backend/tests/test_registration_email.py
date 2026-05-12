"""Test registration email flow: password reset email, Brevo integration, error handling."""
import os
import pytest
from unittest.mock import patch, AsyncMock
from httpx import Response


# ── Unit tests for _send() ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_send_skips_when_no_api_key():
    from services.email_service import _send
    os.environ.pop("BREVO_API_KEY", None)
    result = await _send("test@example.com", "Test", "Subject", "<p>html</p>")
    assert result is False


@pytest.mark.asyncio
async def test_send_skips_when_no_from_email():
    from services.email_service import _send
    os.environ["BREVO_API_KEY"] = "test-key"
    with patch.dict(os.environ, {"EMAIL_FROM": ""}):
        result = await _send("test@example.com", "Test", "Subject", "<p>html</p>")
    assert result is False


@pytest.mark.asyncio
async def test_send_success():
    from services.email_service import _send
    os.environ["BREVO_API_KEY"] = "test-key"
    mock_response = Response(201, json={"messageId": "abc-123"})

    async def mock_post(*args, **kwargs):
        return mock_response

    with patch("httpx.AsyncClient.post", new=mock_post):
        result = await _send("test@example.com", "Test", "Subject", "<p>html</p>")
    assert result is True


@pytest.mark.asyncio
async def test_send_failure_status():
    from services.email_service import _send
    os.environ["BREVO_API_KEY"] = "test-key"
    mock_response = Response(400, json={"code": "bad_request", "message": "Invalid sender"})

    async def mock_post(*args, **kwargs):
        return mock_response

    with patch("httpx.AsyncClient.post", new=mock_post):
        result = await _send("test@example.com", "Test", "Subject", "<p>html</p>")
    assert result is False


@pytest.mark.asyncio
async def test_send_exception():
    from services.email_service import _send
    os.environ["BREVO_API_KEY"] = "test-key"

    async def mock_post(*args, **kwargs):
        raise ConnectionError("DNS resolution failed")

    with patch("httpx.AsyncClient.post", new=mock_post):
        result = await _send("test@example.com", "Test", "Subject", "<p>html</p>")
    assert result is False


# ── Unit tests for send_verification_email() ───────────────────────────────

@pytest.mark.asyncio
async def test_send_verification_email_raises_on_failure():
    from services.email_service import send_verification_email
    os.environ["BREVO_API_KEY"] = "test-key"
    os.environ["EMAIL_FROM"] = "test@example.com"
    os.environ["FRONTEND_URL"] = "http://localhost:3000"

    async def mock_post(*args, **kwargs):
        return Response(401, json={"code": "unauthorized"})

    with patch("httpx.AsyncClient.post", new=mock_post):
        with pytest.raises(RuntimeError, match="Failed to send verification email"):
            await send_verification_email({"email": "user@test.com", "name": "User"}, "token123")


@pytest.mark.asyncio
async def test_send_verification_email_success():
    from services.email_service import send_verification_email
    os.environ["BREVO_API_KEY"] = "test-key"
    os.environ["EMAIL_FROM"] = "test@example.com"
    os.environ["FRONTEND_URL"] = "http://localhost:3000"

    async def mock_post(*args, **kwargs):
        return Response(201, json={"messageId": "msg-456"})

    with patch("httpx.AsyncClient.post", new=mock_post):
        result = await send_verification_email({"email": "user@test.com", "name": "User"}, "token123")
    assert result is None  # function returns None on success (void)


# ── Unit tests for send_password_reset_email() ────────────────────────────

@pytest.mark.asyncio
async def test_send_password_reset_email_raises_on_failure():
    from services.email_service import send_password_reset_email
    os.environ["BREVO_API_KEY"] = "test-key"
    os.environ["EMAIL_FROM"] = "test@example.com"
    os.environ["FRONTEND_URL"] = "http://localhost:3000"

    async def mock_post(*args, **kwargs):
        return Response(403, json={"code": "sender_not_verified"})

    with patch("httpx.AsyncClient.post", new=mock_post):
        with pytest.raises(RuntimeError, match="Failed to send password reset email"):
            await send_password_reset_email({"email": "user@test.com", "name": "User"}, "resettoken")


# ── Integration test note ──────────────────────────────────────────────────

def test_brevo_config_check():
    """Check if Brevo is configured. This is informational, not a pass/fail test."""
    from services.email_service import _api_key, _from_email
    key = _api_key()
    if not key:
        pytest.skip("BREVO_API_KEY not set — skipping live integration checks")
    assert key, "BREVO_API_KEY should be non-empty"
    assert _from_email(), "EMAIL_FROM should be non-empty"
