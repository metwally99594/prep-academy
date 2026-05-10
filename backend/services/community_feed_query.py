"""Feed and notification query builders for community endpoints.

Extracted from routes/community.py for architecture cleanup.
Backward-compatible: preserves all query shapes and filter behavior.
"""
from datetime import datetime, timezone
from typing import Optional


def build_stats_queries(
    db,
) -> dict:
    """Build the common timestamp bounds used in community stats queries.

    Returns dict with: today_start, week_ago.
    """
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    week_ago = datetime.fromtimestamp(now.timestamp() - 86400 * 7, tz=timezone.utc).isoformat()
    return {"today_start": today_start, "week_ago": week_ago}


def build_trending_query(hours: int) -> dict:
    """Build the created_at filter for trending queries."""
    cutoff = datetime.now(timezone.utc).timestamp() - hours * 3600
    since = datetime.fromtimestamp(cutoff, tz=timezone.utc).isoformat()
    return {"created_at": {"$gte": since}}


def build_notification_query(
    user_id: str,
    cursor: Optional[str] = None,
    include_read: bool = True,
) -> dict:
    """Build the MongoDB query dict for fetching user notifications."""
    query = {"user_id": user_id}
    if not include_read:
        query["read"] = False
    if cursor:
        query["created_at"] = {"$lt": cursor}
    return query


def build_my_posts_query(user_id: str) -> dict:
    """Build the query dict for fetching a user's own posts."""
    return {"author_id": user_id}


def build_report_document(
    report_id: str,
    user_id: str,
    target_type: str,
    target_id: str,
    reason: str,
    description: Optional[str],
    now: str,
) -> dict:
    """Build the MongoDB document for a new report."""
    return {
        "id": report_id,
        "reporter_id": user_id,
        "target_type": target_type,
        "target_id": target_id,
        "reason": reason,
        "description": description,
        "status": "open",
        "resolved_by": None,
        "resolved_at": None,
        "created_at": now,
    }
