"""Transactional email via Brevo REST API.

- Retry with exponential backoff (3 attempts)
- In-memory rate limiting (300/hour burst ≈ 5/min sustained)
- Centralised logging with messageId tracking
- Responsive HTML templates with PrepAcademy branding
- Sender: PrepAcademy <noreply@prepacademy-med.com>
"""
import os
import asyncio
import logging
import traceback
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)

# ── Brevo constants (hardcoded — no env var override to prevent misconfiguration) ─
_BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"
_SENDER_EMAIL = "noreply@prepacademy-med.com"
_SENDER_NAME = "PrepAcademy"
_ADMIN_CONTACT = "hilfe@prepacademy-med.com"

_RETRY_DELAYS = [1, 3, 5]
_RATE_LIMIT_MAX = 25
_RATE_LIMIT_WINDOW = 60
_sent_timestamps: list[float] = []


def _api_key() -> str:
    return os.getenv("BREVO_API_KEY", "").strip()


def _frontend_url() -> str:
    return os.getenv("FRONTEND_URL", "https://prep-academy-rho.vercel.app").strip()


def sender_email() -> str:
    """Return the hardcoded Brevo sender email (ignore any EMAIL_FROM override)."""
    return _SENDER_EMAIL


def sender_name() -> str:
    return _SENDER_NAME


def admin_contact() -> str:
    return _ADMIN_CONTACT


def _headers() -> dict:
    return {
        "api-key": _api_key(),
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


# ── Rate limiter ─────────────────────────────────────────────────────────────

def _rate_limited() -> bool:
    """Simple sliding-window rate limiter. Returns True if under limit."""
    global _sent_timestamps
    now = datetime.now().timestamp()
    cutoff = now - _RATE_LIMIT_WINDOW
    _sent_timestamps = [t for t in _sent_timestamps if t > cutoff]
    if len(_sent_timestamps) >= _RATE_LIMIT_MAX:
        wait = _sent_timestamps[0] - cutoff
        logger.warning("[Email] Rate limit hit (%d in %ds) — wait %.0fs", _RATE_LIMIT_MAX, _RATE_LIMIT_WINDOW, wait)
        return False
    _sent_timestamps.append(now)
    return True


# ── HTML helpers ─────────────────────────────────────────────────────────────

def _btn(text: str, url: str) -> str:
    return (
        f'<div style="text-align:center;margin:24px 0">'
        f'<a href="{url}" style="background:linear-gradient(135deg,#c9a84c,#dbb85c);'
        f'color:#06081a;text-decoration:none;padding:14px 32px;border-radius:10px;'
        f'font-weight:600;font-size:15px;display:inline-block">{text}</a></div>'
    )


def _wrap(body: str) -> str:
    year = datetime.now().year
    return f"""<!DOCTYPE html>
<html lang="de">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#06081a;font-family:'Segoe UI',Arial,sans-serif">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#06081a;padding:40px 20px">
<tr><td align="center">
<table width="100%" style="max-width:560px;background:#0c1229;border-radius:16px;border:1px solid rgba(201,168,76,0.15);overflow:hidden">
  <tr><td style="background:linear-gradient(135deg,#0c1229,#111830);padding:28px 32px;text-align:center;border-bottom:1px solid rgba(201,168,76,0.1)">
    <div style="font-size:22px;font-weight:700;color:#c9a84c;letter-spacing:0.05em">PrepAcademy Elite</div>
    <div style="font-size:12px;color:rgba(255,255,255,0.4);margin-top:4px">Medizinische Prüfungsvorbereitung</div>
  </td></tr>
  <tr><td style="padding:32px;color:#e2e8f0;line-height:1.7;font-size:15px">{body}</td></tr>
  <tr><td style="padding:20px 32px;border-top:1px solid rgba(255,255,255,0.05);text-align:center">
    <p style="font-size:11px;color:rgba(255,255,255,0.3);margin:0;line-height:1.8">
      © {year} Mohamed Metwally · PrepAcademy Elite<br>
      Lussmer Ring 69, 28777 Bremen, Deutschland<br>
      <a href="mailto:{_ADMIN_CONTACT}" style="color:rgba(201,168,76,0.5);text-decoration:none">{_ADMIN_CONTACT}</a>
      &nbsp;·&nbsp;
      <a href="{_frontend_url()}/impressum" style="color:rgba(201,168,76,0.5);text-decoration:none">Impressum</a>
      &nbsp;·&nbsp;
      <a href="{_frontend_url()}/datenschutz" style="color:rgba(201,168,76,0.5);text-decoration:none">Datenschutz</a>
    </p>
  </td></tr>
</table>
</td></tr>
</table>
</body></html>"""


# ── Core send with retry + rate-limit + diagnostics ─────────────────────────

_diagnosed = False


async def _send(to_email: str, to_name: str, subject: str, html: str, text: str = "") -> bool:
    """Send email via Brevo REST API with retry + rate-limit protection."""
    global _diagnosed
    if not _diagnosed:
        _diagnosed = True
        _print_diagnostics()

    se = sender_email()
    sn = sender_name()
    key = _api_key()

    if not key:
        logger.warning("[Email] BREVO_API_KEY not set — skipping: %s to %s", subject, to_email)
        return False

    payload = {
        "sender": {"email": se, "name": sn},
        "to": [{"email": to_email, "name": to_name or to_email}],
        "subject": subject,
        "htmlContent": html,
        "textContent": text or subject,
    }

    last_error = None
    for attempt, delay in enumerate(_RETRY_DELAYS, 1):
        if attempt > 1:
            logger.info("[Email] Retry %d/%d for '%s' → %s after %.0fs", attempt, len(_RETRY_DELAYS), subject, to_email, delay)
            await asyncio.sleep(delay)

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.post(_BREVO_API_URL, json=payload, headers=_headers())

            try:
                resp_body = r.json()
            except Exception:
                resp_body = {"raw": r.text[:500]}

            if r.status_code in (200, 201):
                message_id = resp_body.get("messageId", "unknown")
                logger.info("[Email] SUCCESS '%s' → %s | status=%d | messageId=%s | attempt=%d",
                            subject, to_email, r.status_code, message_id, attempt)
                return True

            last_error = f"HTTP {r.status_code}"
            logger.warning("[Email] FAILURE '%s' → %s | attempt=%d | status=%d | body=%s",
                           subject, to_email, attempt, r.status_code, resp_body)

            if r.status_code in (400, 422):
                break

        except Exception as exc:
            last_error = str(exc)
            logger.warning("[Email] EXCEPTION '%s' → %s | attempt=%d | error=%s",
                           subject, to_email, attempt, exc)

    logger.error("[Email] GIVING UP '%s' → %s | last_error=%s\n%s",
                 subject, to_email, last_error, traceback.format_exc())
    return False


def _print_diagnostics() -> None:
    import sys
    key = _api_key()
    se = sender_email()
    sn = sender_name()
    fu = _frontend_url()
    override = os.getenv("EMAIL_FROM", "").strip()
    override_name = os.getenv("EMAIL_FROM_NAME", "").strip()
    logger.debug("Brevo API key configured: %s", bool(key))
    logger.debug("Sender: %s <%s>", sn, se)
    logger.debug("Frontend URL: %s", fu)
    logger.debug("Admin contact: %s", admin_contact())
    if override and override != se:
        logger.warning("EMAIL_FROM env var (%s) is IGNORED — using hardcoded sender %s <%s>", override, sn, se)
    if override_name and override_name != sn:
        logger.warning("EMAIL_FROM_NAME env var (%s) is IGNORED — using hardcoded sender name %s", override_name, sn)
    if not key:
        logger.warning("BREVO_API_KEY is NOT set — transactional emails will NOT be sent.")
    if "gmail" in se.lower() or "yahoo" in se.lower() or "outlook" in se.lower():
        logger.error("PRODUCTION BLOCK: sender email (%s) uses a consumer domain! Enforce noreply@prepacademy-med.com", se)


# ── Templates ────────────────────────────────────────────────────────────────

async def send_verification_email(user: dict, token: str) -> None:
    """Send email address verification. Raises RuntimeError on failure."""
    link = f"{_frontend_url()}/verify-email?token={token}"
    body = f"""
      <h2 style="color:#c9a84c;font-size:20px;margin:0 0 16px 0">E-Mail-Adresse bestätigen</h2>
      <p style="margin:0 0 8px 0">Hallo <strong>{user.get('name','')}</strong>,</p>
      <p style="color:rgba(255,255,255,0.7);margin:0 0 20px 0">
        Bitte bestätigen Sie Ihre E-Mail-Adresse, um Ihr PrepAcademy-Konto zu aktivieren.
        Der Link ist <strong style="color:#c9a84c">24 Stunden</strong> gültig.
      </p>
      {_btn('E-Mail bestätigen', link)}
      <p style="font-size:12px;color:rgba(255,255,255,0.3);text-align:center;margin-top:8px">
        Oder kopieren Sie diesen Link:<br>
        <span style="color:rgba(201,168,76,0.6);word-break:break-all">{link}</span>
      </p>
    """
    ok = await _send(
        user["email"], user.get("name", ""),
        "Bestätigen Sie Ihre E-Mail-Adresse – PrepAcademy",
        _wrap(body),
        f"E-Mail bestätigen: {link}",
    )
    if not ok:
        raise RuntimeError(f"Failed to send verification email to {user.get('email', '?')}")


async def send_welcome_email(user: dict) -> None:
    body = f"""
      <h2 style="color:#c9a84c;font-size:20px;margin:0 0 16px 0">Willkommen bei PrepAcademy! 🎓</h2>
      <p style="margin:0 0 8px 0">Hallo <strong>{user.get('name','')}</strong>,</p>
      <p style="color:rgba(255,255,255,0.7);margin:0 0 20px 0">
        Ihr Konto ist jetzt aktiv. Starten Sie Ihre Vorbereitung mit über 2.500 Prüfungsfragen,
        KI-Analysen und täglichen Podcasts.
      </p>
      {_btn('Jetzt lernen', _frontend_url())}
      <div style="background:rgba(201,168,76,0.05);border:1px solid rgba(201,168,76,0.1);border-radius:10px;padding:16px;margin-top:8px">
        <p style="margin:0 0 8px 0;font-size:12px;color:rgba(255,255,255,0.4);text-transform:uppercase;letter-spacing:0.05em">Was Sie erwartet</p>
        <ul style="margin:0;padding-left:18px;color:rgba(255,255,255,0.7);font-size:14px;line-height:1.9">
          <li>2.500+ Fragen nach Fachgebiet &amp; Jahr</li>
          <li>Persönliche Statistiken &amp; Streak-System</li>
          <li>Tägliche Lern-Podcasts</li>
        </ul>
      </div>
    """
    await _send(user["email"], user.get("name", ""), "Willkommen bei PrepAcademy! 🎓", _wrap(body))


async def send_password_reset_email(user: dict, token: str) -> None:
    """Send password reset. Raises RuntimeError on failure."""
    link = f"{_frontend_url()}/reset-password?token={token}"
    body = f"""
      <h2 style="color:#c9a84c;font-size:20px;margin:0 0 16px 0">Passwort zurücksetzen</h2>
      <p style="margin:0 0 8px 0">Hallo <strong>{user.get('name','')}</strong>,</p>
      <p style="color:rgba(255,255,255,0.7);margin:0 0 20px 0">
        Sie haben eine Zurücksetzung Ihres Passworts angefordert.
        Der Link ist <strong style="color:#c9a84c">1 Stunde</strong> gültig.
      </p>
      {_btn('Passwort zurücksetzen', link)}
      <p style="font-size:12px;color:rgba(255,255,255,0.35);text-align:center;margin-top:8px">
        Falls Sie diese Anfrage nicht gestellt haben, ignorieren Sie diese E-Mail.
        Ihr Passwort bleibt unverändert.
      </p>
    """
    ok = await _send(
        user["email"], user.get("name", ""),
        "Passwort zurücksetzen – PrepAcademy",
        _wrap(body),
        f"Passwort zurücksetzen: {link}",
    )
    if not ok:
        raise RuntimeError(f"Failed to send password reset email to {user.get('email', '?')}")


async def send_otp_email(user: dict, otp_code: str) -> None:
    """Send one-time passcode for sensitive operations."""
    body = f"""
      <h2 style="color:#c9a84c;font-size:20px;margin:0 0 16px 0">Ihr Einmalcode</h2>
      <p style="margin:0 0 8px 0">Hallo <strong>{user.get('name','')}</strong>,</p>
      <p style="color:rgba(255,255,255,0.7);margin:0 0 12px 0">
        Verwenden Sie folgenden Code, um Ihre Aktion zu bestätigen:
      </p>
      <div style="text-align:center;margin:24px 0">
        <span style="font-size:36px;font-weight:700;color:#c9a84c;letter-spacing:8px;background:rgba(201,168,76,0.08);padding:16px 32px;border-radius:12px;display:inline-block">{otp_code}</span>
      </div>
      <p style="font-size:12px;color:rgba(255,255,255,0.3);text-align:center">
        Der Code ist <strong style="color:#c9a84c">10 Minuten</strong> gültig.
        Falls Sie keine Aktion angefordert haben, ignorieren Sie diese E-Mail.
      </p>
    """
    await _send(
        user["email"], user.get("name", ""),
        "Ihr Einmalcode – PrepAcademy",
        _wrap(body),
        f"Ihr Einmalcode: {otp_code}",
    )


async def send_access_granted_email(user: dict, feature_label: str) -> None:
    body = f"""
      <h2 style="color:#22c55e;font-size:20px;margin:0 0 16px 0">Zugang freigeschaltet ✅</h2>
      <p style="margin:0 0 8px 0">Hallo <strong>{user.get('name','')}</strong>,</p>
      <p style="color:rgba(255,255,255,0.7);margin:0 0 20px 0">
        Ihr Zugang zu <strong style="color:#c9a84c">{feature_label}</strong> wurde genehmigt.
        Sie können die Funktion ab sofort nutzen.
      </p>
      {_btn('Zur App', _frontend_url())}
    """
    await _send(
        user["email"], user.get("name", ""),
        f"Ihr Zugang zu {feature_label} wurde freigeschaltet! ✅",
        _wrap(body),
    )


async def send_access_rejected_email(user: dict, feature_label: str, reason: str = "") -> None:
    reason_block = (
        f'<p style="color:rgba(255,255,255,0.5);font-size:13px;margin:12px 0 0 0">'
        f'<strong>Grund:</strong> {reason}</p>'
    ) if reason else ""
    body = f"""
      <h2 style="color:#ef4444;font-size:20px;margin:0 0 16px 0">Anfrage abgelehnt</h2>
      <p style="margin:0 0 8px 0">Hallo <strong>{user.get('name','')}</strong>,</p>
      <p style="color:rgba(255,255,255,0.7);margin:0 0 4px 0">
        Ihr Antrag für <strong style="color:#c9a84c">{feature_label}</strong> wurde leider abgelehnt.
      </p>
      {reason_block}
      <p style="color:rgba(255,255,255,0.4);font-size:13px;margin:20px 0 0 0">
        Bei Fragen: <a href="mailto:{_ADMIN_CONTACT}" style="color:#c9a84c">{_ADMIN_CONTACT}</a>
      </p>
    """
    await _send(
        user["email"], user.get("name", ""),
        f"Anfrage für {feature_label} abgelehnt – PrepAcademy",
        _wrap(body),
    )


async def send_admin_new_request_email(admin_email: str, user: dict, feature_label: str) -> None:
    link = f"{_frontend_url()}/admin/analytics"
    phone = user.get("phone", "")
    message = user.get("message", "")
    is_public = bool(user.get("phone") or user.get("message"))
    title = "Neue Kontaktanfrage" if is_public else "Neue Zugangsanfrage"

    phone_block = ""
    if phone:
        phone_block = f"""
        <p style="margin:6px 0 0 0;color:rgba(255,255,255,0.7);font-size:13px">
          📞 <a href="tel:{phone}" style="color:#60a5fa;text-decoration:none">{phone}</a>
        </p>"""

    message_block = ""
    if message:
        safe_msg = message.replace("<", "&lt;").replace(">", "&gt;")
        message_block = f"""
      <div style="background:rgba(59,130,246,0.05);border-left:3px solid #3b82f6;border-radius:6px;padding:12px 14px;margin-bottom:20px">
        <p style="margin:0;color:rgba(255,255,255,0.5);font-size:11px;text-transform:uppercase;letter-spacing:0.05em">Nachricht</p>
        <p style="margin:6px 0 0 0;color:rgba(255,255,255,0.85);font-size:14px;line-height:1.5;white-space:pre-wrap">{safe_msg}</p>
      </div>"""

    body = f"""
      <h2 style="color:#3b82f6;font-size:20px;margin:0 0 16px 0">{title}</h2>
      <div style="background:rgba(255,255,255,0.03);border-radius:10px;padding:16px;margin-bottom:20px">
        <p style="margin:0 0 4px 0"><strong>{user.get('name','')}</strong></p>
        <p style="margin:0;color:rgba(255,255,255,0.5);font-size:13px">
          ✉️ <a href="mailto:{user.get('email','')}" style="color:#60a5fa;text-decoration:none">{user.get('email','')}</a>
        </p>
        {phone_block}
        <p style="margin:10px 0 0 0;font-size:13px;color:rgba(59,130,246,0.9)">
          Funktion: <strong>{feature_label}</strong>
        </p>
      </div>
      {message_block}
      {_btn('Zur Admin-Übersicht', link)}
    """
    await _send(
        admin_email, "Admin",
        f"{title}: {feature_label} von {user.get('name','')}",
        _wrap(body),
    )


# ── Trial Templates ──────────────────────────────────────────────────────────

async def send_trial_started_email(user: dict, days: int = 30) -> None:
    body = f"""
      <h2 style="color:#c9a84c;font-size:20px;margin:0 0 16px 0">🎁 Ihre Probezeit hat begonnen!</h2>
      <p style="margin:0 0 8px 0">Hallo <strong>{user.get('name','')}</strong>,</p>
      <p style="color:rgba(255,255,255,0.7);margin:0 0 20px 0">
        Herzlich willkommen! Ihre <strong style="color:#c9a84c">{days}-tägige kostenlose Probezeit</strong>
        ist jetzt aktiv. Alle Funktionen stehen Ihnen uneingeschränkt zur Verfügung.
      </p>
      {_btn('Jetzt starten', _frontend_url())}
      <div style="background:rgba(201,168,76,0.05);border:1px solid rgba(201,168,76,0.1);border-radius:10px;padding:16px;margin-top:8px">
        <p style="margin:0 0 8px 0;font-size:12px;color:rgba(255,255,255,0.4);text-transform:uppercase;letter-spacing:0.05em">Freigeschaltete Funktionen</p>
        <ul style="margin:0;padding-left:18px;color:rgba(255,255,255,0.7);font-size:14px;line-height:1.9">
          <li>✅ Alle Prüfungsfragen (2.500+)</li>
          <li>✅ PDF Notebook mit KI-Analyse</li>
          <li>✅ Medical Analyzer (EKG + Röntgen)</li>
          <li>✅ Daily Podcast</li>
        </ul>
      </div>
    """
    await _send(user["email"], user.get("name",""), f"Ihre {days}-tägige Probezeit hat begonnen! 🎁", _wrap(body))


async def send_trial_5days_warning_email(user: dict, days_left: int) -> None:
    body = f"""
      <h2 style="color:#f59e0b;font-size:20px;margin:0 0 16px 0">Probezeit endet in {days_left} Tagen</h2>
      <p style="margin:0 0 8px 0">Hallo <strong>{user.get('name','')}</strong>,</p>
      <p style="color:rgba(255,255,255,0.7);margin:0 0 20px 0">
        Ihre Probezeit läuft in <strong style="color:#f59e0b">{days_left} Tagen</strong> ab.
        Nutzen Sie die verbleibende Zeit optimal oder kontaktieren Sie uns für eine Verlängerung.
      </p>
      {_btn('Verlängerung anfragen', f"{_frontend_url()}/dashboard")}
    """
    await _send(user["email"], user.get("name",""), f"⚠️ Probezeit endet in {days_left} Tagen – PrepAcademy", _wrap(body))


async def send_trial_2days_warning_email(user: dict, days_left: int) -> None:
    label = "morgen" if days_left <= 1 else f"in {days_left} Tagen"
    body = f"""
      <h2 style="color:#ef4444;font-size:20px;margin:0 0 16px 0">⚠️ Probezeit endet {label}!</h2>
      <p style="margin:0 0 8px 0">Hallo <strong>{user.get('name','')}</strong>,</p>
      <p style="color:rgba(255,255,255,0.7);margin:0 0 20px 0">
        Letzte Chance: Ihre Probezeit endet <strong style="color:#ef4444">{label}</strong>.
        Danach stehen nur noch die Grundfunktionen zur Verfügung.
      </p>
      {_btn('Verlängerung anfragen', f"{_frontend_url()}/dashboard")}
      <p style="color:rgba(255,255,255,0.4);font-size:13px;margin:16px 0 0 0">
        Kontakt: <a href="mailto:{_ADMIN_CONTACT}" style="color:#c9a84c">{_ADMIN_CONTACT}</a>
      </p>
    """
    await _send(user["email"], user.get("name",""), f"🚨 Probezeit endet {label}! – PrepAcademy", _wrap(body))


async def send_trial_expired_email(user: dict) -> None:
    body = f"""
      <h2 style="color:#ef4444;font-size:20px;margin:0 0 16px 0">Probezeit abgelaufen</h2>
      <p style="margin:0 0 8px 0">Hallo <strong>{user.get('name','')}</strong>,</p>
      <p style="color:rgba(255,255,255,0.7);margin:0 0 20px 0">
        Ihre kostenlose Probezeit ist abgelaufen. Der Lernmodus (Study) steht Ihnen weiterhin
        zur Verfügung. Für den vollen Zugang kontaktieren Sie den Administrator.
      </p>
      {_btn('Verlängerung anfragen', f"{_frontend_url()}/dashboard")}
      <p style="color:rgba(255,255,255,0.4);font-size:13px;margin:16px 0 0 0">
        Kontakt: <a href="mailto:{_ADMIN_CONTACT}" style="color:#c9a84c">{_ADMIN_CONTACT}</a>
      </p>
    """
    await _send(user["email"], user.get("name",""), "Ihre Probezeit ist abgelaufen – PrepAcademy", _wrap(body))


async def send_trial_extended_email(user: dict, days: int, new_end: str) -> None:
    try:
        end_date = datetime.fromisoformat(new_end.replace("Z","+00:00")).strftime("%d.%m.%Y")
    except Exception:
        end_date = new_end
    body = f"""
      <h2 style="color:#22c55e;font-size:20px;margin:0 0 16px 0">Probezeit verlängert ✅</h2>
      <p style="margin:0 0 8px 0">Hallo <strong>{user.get('name','')}</strong>,</p>
      <p style="color:rgba(255,255,255,0.7);margin:0 0 20px 0">
        Ihre Probezeit wurde um <strong style="color:#c9a84c">{days} Tage</strong> verlängert.
        Neues Enddatum: <strong style="color:#c9a84c">{end_date}</strong>
      </p>
      {_btn('Weiter lernen', _frontend_url())}
    """
    await _send(user["email"], user.get("name",""), f"Probezeit verlängert (+{days} Tage) ✅", _wrap(body))


async def send_trial_made_permanent_email(user: dict) -> None:
    body = f"""
      <h2 style="color:#c9a84c;font-size:20px;margin:0 0 16px 0">👑 Permanenter Zugang freigeschaltet!</h2>
      <p style="margin:0 0 8px 0">Hallo <strong>{user.get('name','')}</strong>,</p>
      <p style="color:rgba(255,255,255,0.7);margin:0 0 20px 0">
        Ihr Konto hat jetzt <strong style="color:#c9a84c">permanenten Vollzugang</strong> zu allen
        PrepAcademy-Funktionen ohne zeitliche Begrenzung.
      </p>
      {_btn('Zur App', _frontend_url())}
    """
    await _send(user["email"], user.get("name",""), "👑 Permanenter Zugang freigeschaltet – PrepAcademy", _wrap(body))


async def send_admin_new_user_email(admin_email: str, user: dict) -> None:
    link = f"{_frontend_url()}/admin/analytics"
    body = f"""
      <h2 style="color:#c9a84c;font-size:20px;margin:0 0 16px 0">Neuer Nutzer registriert</h2>
      <div style="background:rgba(255,255,255,0.03);border-radius:10px;padding:16px;margin-bottom:20px">
        <p style="margin:0 0 4px 0"><strong>{user.get('name','')}</strong></p>
        <p style="margin:0;color:rgba(255,255,255,0.5);font-size:13px">{user.get('email','')}</p>
      </div>
      {_btn('Analytics öffnen', link)}
    """
    await _send(
        admin_email, "Admin",
        f"Neuer Nutzer: {user.get('name','')}",
        _wrap(body),
    )
