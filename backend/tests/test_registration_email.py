"""Test registration email flow: password reset email, Brevo integration, error handling."""
import os
import pytest
from unittest.mock import patch, AsyncMock
from httpx import Response

PRIMARY_DOMAIN = "https://prepacademy-med.com"


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


def test_frontend_url_defaults_to_primary_domain():
    from services.email_service import _frontend_url
    os.environ.pop("FRONTEND_URL", None)
    assert _frontend_url() == PRIMARY_DOMAIN


def test_frontend_url_blocks_vercel_domain_in_production():
    from services.email_service import _frontend_url

    with patch.dict(os.environ, {
        "ENVIRONMENT": "production",
        "FRONTEND_URL": "https://prep-academy-rho.vercel.app",
    }):
        assert _frontend_url() == PRIMARY_DOMAIN


@pytest.mark.asyncio
async def test_send_verification_email_uses_primary_domain_link():
    from services.email_service import send_verification_email

    os.environ["BREVO_API_KEY"] = "test-key"
    os.environ["FRONTEND_URL"] = PRIMARY_DOMAIN
    captured = {}

    async def mock_post(*args, **kwargs):
        captured["payload"] = kwargs["json"]
        return Response(201, json={"messageId": "msg-domain"})

    with patch("httpx.AsyncClient.post", new=mock_post):
        await send_verification_email({"email": "user@test.com", "name": "User"}, "token123")

    payload_text = "\n".join([
        captured["payload"]["htmlContent"],
        captured["payload"]["textContent"],
    ])
    assert f"{PRIMARY_DOMAIN}/verify-email?token=token123" in payload_text
    assert "vercel.app" not in payload_text


# ── Unit tests for send_password_reset_email() ────────────────────────────

@pytest.mark.asyncio
async def test_send_verification_email_rewrites_old_vercel_domain():
    from services.email_service import send_verification_email

    captured = {}

    async def mock_post(*args, **kwargs):
        captured["payload"] = kwargs["json"]
        return Response(201, json={"messageId": "msg-rewrite-domain"})

    with patch.dict(os.environ, {
        "BREVO_API_KEY": "test-key",
        "ENVIRONMENT": "production",
        "FRONTEND_URL": "https://prep-academy-rho.vercel.app",
    }):
        with patch("httpx.AsyncClient.post", new=mock_post):
            await send_verification_email({"email": "user@test.com", "name": "User"}, "token123")

    payload_text = "\n".join([
        captured["payload"]["htmlContent"],
        captured["payload"]["textContent"],
    ])
    assert f"{PRIMARY_DOMAIN}/verify-email?token=token123" in payload_text
    assert "vercel.app" not in payload_text


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


@pytest.mark.asyncio
async def test_send_password_reset_email_uses_primary_domain_link():
    from services.email_service import send_password_reset_email

    os.environ["BREVO_API_KEY"] = "test-key"
    os.environ["FRONTEND_URL"] = PRIMARY_DOMAIN
    captured = {}

    async def mock_post(*args, **kwargs):
        captured["payload"] = kwargs["json"]
        return Response(201, json={"messageId": "msg-reset-domain"})

    with patch("httpx.AsyncClient.post", new=mock_post):
        await send_password_reset_email({"email": "user@test.com", "name": "User"}, "resettoken")

    payload_text = "\n".join([
        captured["payload"]["htmlContent"],
        captured["payload"]["textContent"],
    ])
    assert f"{PRIMARY_DOMAIN}/reset-password?token=resettoken" in payload_text
    assert "vercel.app" not in payload_text


# ── Integration test note ──────────────────────────────────────────────────

def test_brevo_config_check():
    """Check if Brevo is configured. This is informational, not a pass/fail test."""
    from services.email_service import _api_key, sender_email
    key = _api_key()
    if not key:
        pytest.skip("BREVO_API_KEY not set — skipping live integration checks")
    assert key, "BREVO_API_KEY should be non-empty"
    assert sender_email() == "noreply@prepacademy-med.com"
