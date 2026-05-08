"""Transactional email via Brevo REST API (uses httpx — no extra dependency)."""
import os
import logging
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)

_BREVO_URL = "https://api.brevo.com/v3/smtp/email"
_FRONTEND = os.getenv("FRONTEND_URL", "https://prep-academy-rho.vercel.app")
_FROM_EMAIL = os.getenv("EMAIL_FROM", "mohamedmetwle99@gmail.com")
_FROM_NAME = os.getenv("EMAIL_FROM_NAME", "PrepAcademy")


def _headers() -> dict:
    return {
        "api-key": os.getenv("BREVO_API_KEY", ""),
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


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
      <a href="{_FRONTEND}/impressum" style="color:rgba(201,168,76,0.5);text-decoration:none">Impressum</a>
      &nbsp;·&nbsp;
      <a href="{_FRONTEND}/datenschutz" style="color:rgba(201,168,76,0.5);text-decoration:none">Datenschutz</a>
    </p>
  </td></tr>
</table>
</td></tr>
</table>
</body></html>"""


async def _send(to_email: str, to_name: str, subject: str, html: str, text: str = "") -> None:
    key = os.getenv("BREVO_API_KEY", "")
    if not key:
        logger.warning("[Email] BREVO_API_KEY not set — skipping: %s", subject)
        return
    payload = {
        "sender": {"email": _FROM_EMAIL, "name": _FROM_NAME},
        "to": [{"email": to_email, "name": to_name or to_email}],
        "subject": subject,
        "htmlContent": html,
        "textContent": text or subject,
    }
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(_BREVO_URL, json=payload, headers=_headers())
        if r.status_code not in (200, 201):
            logger.error("[Email] Brevo %s for '%s': %s", r.status_code, subject, r.text[:300])
        else:
            logger.info("[Email] Sent '%s' → %s", subject, to_email)
    except Exception as exc:
        logger.error("[Email] Send failed (%s): %s", subject, exc)


# ── Templates ──────────────────────────────────────────────────────────────

async def send_verification_email(user: dict, token: str) -> None:
    link = f"{_FRONTEND}/verify-email?token={token}"
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
    await _send(
        user["email"], user.get("name", ""),
        "Bestätigen Sie Ihre E-Mail-Adresse – PrepAcademy",
        _wrap(body),
        f"E-Mail bestätigen: {link}",
    )


async def send_welcome_email(user: dict) -> None:
    body = f"""
      <h2 style="color:#c9a84c;font-size:20px;margin:0 0 16px 0">Willkommen bei PrepAcademy! 🎓</h2>
      <p style="margin:0 0 8px 0">Hallo <strong>{user.get('name','')}</strong>,</p>
      <p style="color:rgba(255,255,255,0.7);margin:0 0 20px 0">
        Ihr Konto ist jetzt aktiv. Starten Sie Ihre Vorbereitung mit über 2.500 Prüfungsfragen,
        KI-Analysen und täglichen Podcasts.
      </p>
      {_btn('Jetzt lernen', _FRONTEND)}
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
    link = f"{_FRONTEND}/reset-password?token={token}"
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
    await _send(
        user["email"], user.get("name", ""),
        "Passwort zurücksetzen – PrepAcademy",
        _wrap(body),
        f"Passwort zurücksetzen: {link}",
    )


async def send_access_granted_email(user: dict, feature_label: str) -> None:
    body = f"""
      <h2 style="color:#22c55e;font-size:20px;margin:0 0 16px 0">Zugang freigeschaltet ✅</h2>
      <p style="margin:0 0 8px 0">Hallo <strong>{user.get('name','')}</strong>,</p>
      <p style="color:rgba(255,255,255,0.7);margin:0 0 20px 0">
        Ihr Zugang zu <strong style="color:#c9a84c">{feature_label}</strong> wurde genehmigt.
        Sie können die Funktion ab sofort nutzen.
      </p>
      {_btn('Zur App', _FRONTEND)}
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
        Bei Fragen:
        <a href="mailto:mohamedmetwle99@gmail.com" style="color:#c9a84c">mohamedmetwle99@gmail.com</a>
      </p>
    """
    await _send(
        user["email"], user.get("name", ""),
        f"Anfrage für {feature_label} abgelehnt – PrepAcademy",
        _wrap(body),
    )


async def send_admin_new_request_email(admin_email: str, user: dict, feature_label: str) -> None:
    link = f"{_FRONTEND}/admin/analytics"
    body = f"""
      <h2 style="color:#c9a84c;font-size:20px;margin:0 0 16px 0">Neue Zugangsanfrage</h2>
      <div style="background:rgba(255,255,255,0.03);border-radius:10px;padding:16px;margin-bottom:20px">
        <p style="margin:0 0 4px 0"><strong>{user.get('name','')}</strong></p>
        <p style="margin:0;color:rgba(255,255,255,0.5);font-size:13px">{user.get('email','')}</p>
        <p style="margin:8px 0 0 0;font-size:13px;color:rgba(201,168,76,0.8)">
          Funktion: <strong>{feature_label}</strong>
        </p>
      </div>
      {_btn('Zur Admin-Übersicht', link)}
    """
    await _send(
        admin_email, "Admin",
        f"Neue Zugangsanfrage: {feature_label} von {user.get('name','')}",
        _wrap(body),
    )


async def send_admin_new_user_email(admin_email: str, user: dict) -> None:
    link = f"{_FRONTEND}/admin/analytics"
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
