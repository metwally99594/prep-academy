"""
Moderation Orchestration — coordinates all moderation checks, shadow-hide decisions,
reason selection, escalation, and queue management for the community.

Route handlers call orchestrate_post_moderation() / orchestrate_comment_moderation()
and get back a result dict with status, moderation_reason, etc.
"""
import time
import re as _re
import uuid as _uuid
from datetime import datetime, timezone
from typing import Optional

from database import logger
from services.community_observability import Timer, get_correlation_id, log_moderation_action
from services.moderation_service import (
    evaluate_auto_moderation, is_title_all_caps, has_external_links,
    build_moderation_entry, check_profanity, check_emoji_spam,
    check_repeated_links, track_user_link, check_suspicious_account,
    increment_offense, get_recent_offenses,
    AUTO_QUEUE_REASONS, MODERATOR_REASON_TEMPLATES, SHADOW_HIDE_THRESHOLD,
)
from services.community_service import (
    contains_html, sanitize_html, check_phi, check_dangerous_advice,
    is_duplicate,
)

_URL_RE = _re.compile(r"https?://(?:[^\s])+")


def _compute_user_age(user_doc: dict) -> float:
    created_at = user_doc.get("created_at", "")
    if not created_at:
        return 999.0
    try:
        epoch = time.mktime(
            datetime.strptime(created_at[:19], "%Y-%m-%dT%H:%M:%S").timetuple()
        )
        return (time.time() - epoch) / 86400
    except (ValueError, OSError):
        return 999.0


def _compute_is_new(user_age_days: float) -> bool:
    return user_age_days < 7


def _collect_link_spam_findings(text: str, user_id: str) -> list[str]:
    findings: list[str] = []
    for url in _URL_RE.findall(text):
        if track_user_link(user_id, url):
            findings.append(f"Repeated link spam: {url}")
            break
    return findings


def _select_reason(reason_key: str, fallback: str = "") -> str:
    """Select human-readable reason, trying templates first."""
    return MODERATOR_REASON_TEMPLATES.get(
        reason_key, AUTO_QUEUE_REASONS.get(reason_key, fallback or reason_key)
    )


def _determine_status(
    should_queue: bool,
    is_shadow_hidden: bool,
):
    """Determine final status, reason_key, severity, and should_queue flag.

    When shadow-hidden, should_queue is forced False — hidden content
    must not appear in the moderation queue (silent shadow-ban).

    Backward-compatible: all existing callers get the same (status, reason_key, severity)
    tuple unpacking; callers that need the overridden should_queue can read index 3.
    """
    if is_shadow_hidden:
        return "hidden", "suspicious_account", "low", False
    if should_queue:
        return "moderation_queue", "", "", True
    return "published", "", "", False


async def orchestrate_post_moderation(
    title: str,
    content: str,
    user_id: str,
    user_doc: dict,
) -> dict:
    """
    Run ALL moderation checks for a new post.
    Returns dict with:
      sanitized_title, sanitized_content, dup_of, status, moderation_reason,
      reason_key, severity, should_queue, is_shadow_hidden, created_epoch
    """
    _timer = Timer()
    with _timer:
        sanitized_title = sanitize_html(title)
        sanitized_content = sanitize_html(content)
        has_raw_html = contains_html(title) or contains_html(content)
        phi = check_phi(content)
        dangerous = check_dangerous_advice(content)
        caps_check = is_title_all_caps(title)
        ext_links = has_external_links(content)
        profanity = check_profanity(f"{title} {content}")
        emoji = check_emoji_spam(content)
        repeated_links = check_repeated_links(content)
        link_spam = _collect_link_spam_findings(content, user_id)

        user_age = _compute_user_age(user_doc)
        is_new = _compute_is_new(user_age)
        offenses = get_recent_offenses(user_id)
        suspicious = check_suspicious_account(user_age, offenses)
        shadow_hidden = offenses >= SHADOW_HIDE_THRESHOLD

        should_queue, reason_key, severity = evaluate_auto_moderation(
            is_new_user=is_new,
            contains_html=has_raw_html,
            phi_findings=phi,
            dangerous_advice=dangerous,
            has_external_links=ext_links,
            title_is_all_caps=caps_check,
            profanity_findings=profanity,
            emoji_findings=emoji,
            link_findings=repeated_links or link_spam,
            suspicious_account_reason=suspicious,
        )

        status, final_reason_key, final_severity, should_queue = _determine_status(should_queue, shadow_hidden)
        reason_key = final_reason_key or reason_key
        severity = final_severity or severity

        moderation_reason = _select_reason(reason_key) if status in ("moderation_queue", "hidden") else None

    cid = get_correlation_id()
    logger.info("mod_action=orchestrate_post user=%s duration_ms=%.1f status=%s sh=%s correlation_id=%s",
                user_id[:8], _timer.ms, status, shadow_hidden, cid or "-")

    return {
        "sanitized_title": sanitized_title,
        "sanitized_content": sanitized_content,
        "status": status,
        "moderation_reason": moderation_reason,
        "reason_key": reason_key,
        "severity": severity,
        "should_queue": should_queue,
        "is_shadow_hidden": shadow_hidden,
    }


async def orchestrate_comment_moderation(
    content: str,
    user_id: str,
    user_doc: dict,
) -> dict:
    """
    Run ALL moderation checks for a new comment.
    Returns dict with sanitized_content, status, moderation_reason, etc.
    """
    _timer = Timer()
    with _timer:
        sanitized = sanitize_html(content)
        phi = check_phi(content)
        dangerous = check_dangerous_advice(content)
        profanity = check_profanity(content)
        emoji = check_emoji_spam(content)
        repeated_links = check_repeated_links(content)
        link_spam = _collect_link_spam_findings(content, user_id)
        raw_html = contains_html(content)

        user_age = _compute_user_age(user_doc)
        offenses = get_recent_offenses(user_id)
        suspicious = check_suspicious_account(user_age, offenses)
        shadow_hidden = offenses >= SHADOW_HIDE_THRESHOLD

        should_queue, reason_key, severity = evaluate_auto_moderation(
            phi_findings=phi,
            dangerous_advice=dangerous,
            contains_html=raw_html,
            profanity_findings=profanity,
            emoji_findings=emoji,
            link_findings=repeated_links or link_spam,
            suspicious_account_reason=suspicious,
        )

        status, final_reason_key, final_severity, should_queue = _determine_status(should_queue, shadow_hidden)
        reason_key = final_reason_key or reason_key
        severity = final_severity or severity

        moderation_reason = _select_reason(reason_key) if status in ("moderation_queue", "hidden") else None

    cid = get_correlation_id()
    logger.info("mod_action=orchestrate_comment user=%s duration_ms=%.1f status=%s sh=%s correlation_id=%s",
                user_id[:8], _timer.ms, status, shadow_hidden, cid or "-")

    return {
        "sanitized_content": sanitized,
        "status": status,
        "moderation_reason": moderation_reason,
        "reason_key": reason_key,
        "severity": severity,
        "should_queue": should_queue,
        "is_shadow_hidden": shadow_hidden,
    }


async def handle_moderation_queue_insert(
    target_type: str,
    target_id: str,
    reason: str,
    reason_key: str,
    severity: str,
    user_id: str,
):
    """Insert moderation queue entry and track offense. Logs structuredly."""
    entry = build_moderation_entry(target_type, target_id, reason, reason_key, severity)
    try:
        from database import db
        await db.community_moderation_queue.insert_one(entry)
        if increment_offense(user_id):
            logger.info(
                "mod_action=auto_lock_triggered user_id=%s target_type=%s target_id=%s",
                user_id[:8], target_type, target_id,
            )
    except Exception as e:
        logger.warning("mod_action=queue_insert_failed target_type=%s error=%s", target_type, e)


async def handle_report_moderation(
    target_type: str,
    target_id: str,
    reason: str,
):
    """Check report thresholds and auto-hide or auto-queue. Logs structuredly."""
    from database import db
    from services.moderation_service import should_auto_hide, should_auto_queue
    collection = db.community_posts if target_type == "post" else db.community_comments
    target = await collection.find_one({"id": target_id}, {"stats": 1})
    if not target:
        return
    report_count = (target.get("stats", {}) or {}).get("report_count", 0)
    if should_auto_hide(report_count):
        await collection.update_one(
            {"id": target_id},
            {"$set": {"status": "hidden"}},
        )
        logger.info("mod_action=auto_hide target_type=%s target_id=%s reports=%d", target_type, target_id, report_count)
    elif should_auto_queue(report_count):
        existing = await db.community_moderation_queue.find_one(
            {"target_type": target_type, "target_id": target_id}
        )
        if not existing:
            entry = build_moderation_entry(target_type, target_id, f"Reported ({reason})", "multiple_reports", "medium")
            await db.community_moderation_queue.insert_one(entry)
            logger.info("mod_action=auto_queue target_type=%s target_id=%s reports=%d", target_type, target_id, report_count)
