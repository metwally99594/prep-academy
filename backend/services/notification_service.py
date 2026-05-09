"""
Notification aggregation, creation, and query helpers.

Isolated from route logic — no request/response coupling.

Index recommendations (apply manually via mongosh):

  db.notifications.createIndex({user_id:1, created_at:-1})
  db.notifications.createIndex({user_id:1, read:1, created_at:-1})
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from services.community_observability import Timer


def _get_logger():
    from database import logger
    return logger


def _get_db():
    from database import db
    return db


NOTIFICATION_PROJECTION = {
    "_id": 0, "id": 1, "user_id": 1, "type": 1, "icon": 1,
    "title": 1, "message": 1, "read": 1, "aggregate_count": 1,
    "created_at": 1, "data": 1,
}


async def create_notification(
    user_id: str,
    notification_type: str,
    title: str,
    message: str,
    icon: str = "message-circle",
    data: Optional[dict] = None,
):
    """Create a single notification document."""
    try:
        db = _get_db()
        await db.notifications.insert_one({
            "id": uuid.uuid4().hex,
            "user_id": user_id,
            "type": notification_type,
            "icon": icon,
            "title": title,
            "message": message[:300],
            "read": False,
            "aggregate_count": 1,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "data": data or {},
        })
    except Exception as e:
        _get_logger().warning("notif=create_failed user_id=%s type=%s error=%s", user_id[:8], notification_type, e)


async def aggregate_notification(
    user_id: str,
    notification_type: str,
    title: str,
    message: str,
    aggregate_key: str,
    icon: str = "message-circle",
    data: Optional[dict] = None,
) -> Optional[str]:
    """Create or aggregate a notification. Merges with existing unread notification of same type+key."""
    _timer = Timer()
    db = _get_db()
    now = datetime.now(timezone.utc).isoformat()
    try:
        with _timer:
            existing = await db.notifications.find_one({
                "user_id": user_id,
                "type": notification_type,
                "data.aggregate_key": aggregate_key,
                "read": False,
            })
            if existing:
                count = existing.get("aggregate_count", 1) + 1
                await db.notifications.update_one(
                    {"id": existing["id"]},
                    {"$set": {
                        "aggregate_count": count,
                        "message": message[:300],
                        "updated_at": now,
                    }},
                )
                return existing["id"]
            notif_data = data or {}
            notif_data["aggregate_key"] = aggregate_key
            nid = uuid.uuid4().hex
            await db.notifications.insert_one({
                "id": nid,
                "user_id": user_id,
                "type": notification_type,
                "icon": icon,
                "title": title,
                "message": message[:300],
                "read": False,
                "aggregate_count": 1,
                "created_at": now,
                "data": notif_data,
            })
        return nid
    except Exception as e:
        _get_logger().warning("notif=aggregate_failed user_id=%s type=%s error=%s duration_ms=%.1f",
                              user_id[:8], notification_type, e, _timer.ms)
        return None


async def dispatch_comment_notifications(
    post_author_id: str,
    commenter_id: str,
    parent_author_id: Optional[str],
    sanitized_content: str,
    post_id: str,
    comment_id: str,
    parent_id: Optional[str],
    commenter_name: str,
):
    """Fire-and-forget notification dispatch for a new published comment."""
    import asyncio

    if post_author_id != commenter_id:
        asyncio.create_task(aggregate_notification(
            user_id=post_author_id,
            notification_type="community_comment",
            title="New comment on your post",
            message=sanitized_content[:200],
            aggregate_key=f"post:{post_id}",
            icon="message-circle",
            data={"target_type": "post", "target_id": post_id},
        ))
    if parent_id and parent_author_id and parent_author_id != commenter_id:
        asyncio.create_task(aggregate_notification(
            user_id=parent_author_id,
            notification_type="community_reply",
            title="Reply to your comment",
            message=sanitized_content[:200],
            aggregate_key=f"comment:{parent_id}",
            icon="message-square",
            data={"target_type": "comment", "target_id": comment_id, "post_id": post_id},
        ))
    asyncio.create_task(notify_mentioned_users(
        sanitized_content, commenter_id, commenter_name, "comment", comment_id,
    ))


async def notify_mentioned_users(content: str, actor_id: str, actor_name: str, target_type: str, target_id: str):
    """Notify users mentioned with @username in content. Does NOT notify the actor."""
    db = _get_db()
    from services.community_service import extract_mentions
    mentions = extract_mentions(content)
    if not mentions:
        return
    for username in mentions:
        mentioned_user = await db.users.find_one({"name": username})
        if not mentioned_user:
            continue
        if mentioned_user["id"] == actor_id:
            continue
        await create_notification(
            user_id=mentioned_user["id"],
            notification_type="community_mention",
            title=f"You were mentioned by {actor_name}",
            message=content[:200],
            icon="at-sign",
            data={"target_type": target_type, "target_id": target_id},
        )


def serialize_notification(n: dict) -> dict:
    """Lightweight serializer for notification documents."""
    return {
        "id": n.get("id"),
        "type": n.get("type"),
        "icon": n.get("icon", "message-circle"),
        "title": n.get("title"),
        "message": n.get("message"),
        "read": n.get("read", False),
        "aggregate_count": n.get("aggregate_count", 1),
        "created_at": n.get("created_at"),
        "data": n.get("data", {}),
    }


async def get_user_notifications(
    user_id: str,
    limit: int = 20,
    cursor: Optional[str] = None,
    include_read: bool = True,
) -> dict:
    """
    Get paginated notifications for a user.
    Uses deterministic cursor pagination with secondary sort on _id.
    Returns dict with notifications, next_cursor, unread_count.
    """
    _timer = Timer()
    db = _get_db()
    query = {"user_id": user_id}
    if not include_read:
        query["read"] = False

    if cursor:
        query["created_at"] = {"$lt": cursor}

    with _timer:
        items = await db.notifications.find(
            query, NOTIFICATION_PROJECTION
        ).sort("created_at", -1).to_list(length=limit + 1)

        has_more = len(items) > limit
        if has_more:
            items = items[:limit]

        next_cursor = items[-1]["created_at"] if has_more and items else None

        unread_count = await db.notifications.count_documents({
            "user_id": user_id, "read": False,
        })

    return {
        "notifications": [serialize_notification(n) for n in items],
        "next_cursor": next_cursor,
        "unread_count": unread_count,
    }


async def mark_all_read(user_id: str):
    """Mark all unread notifications as read."""
    db = _get_db()
    result = await db.notifications.update_many(
        {"user_id": user_id, "read": False},
        {"$set": {"read": True}},
    )
    _get_logger().info("notif=mark_all_read user_id=%s count=%d", user_id[:8], result.modified_count)
    return result.modified_count
