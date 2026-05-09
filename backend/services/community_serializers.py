"""Serializers for community response types.

Extracted from routes/community.py for architecture cleanup.
Backward-compatible: all functions preserve existing response shapes.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from services.community_observability import Timer, get_correlation_id, log_cache_event


async def build_moderation_queue_item(
    item: dict,
    collection,
    get_user_name,
) -> dict:
    """Enrich a single moderation queue item with target preview and author info."""
    target_preview = None
    target_author_id = None
    target_author_name = None
    if item.get("target_id"):
        target = await collection.find_one(
            {"id": item["target_id"]},
            {"content": 1, "title": 1, "author_id": 1},
        )
        if target:
            preview_field = target.get("title") or target.get("content", "")
            target_preview = preview_field[:200]
            target_author_id = target.get("author_id")
            if target_author_id:
                target_author_name = await get_user_name(target_author_id)

    return {
        **item,
        "target_preview": target_preview,
        "target_author_id": target_author_id,
        "target_author_name": target_author_name,
    }


async def enrich_moderation_queue_items(items: list, db, get_user_name) -> list:
    """Enrich all moderation queue items with target preview and author info."""
    _timer = Timer()
    enriched = []
    for item in items:
        collection = db.community_posts if item.get("target_type") == "post" else db.community_comments
        enriched_item = await build_moderation_queue_item(item, collection, get_user_name)
        enriched.append(enriched_item)
    cid = get_correlation_id()
    import logging
    logging.getLogger(__name__).info(
        "serializer=enrich_queue items=%d duration_ms=%.1f correlation_id=%s",
        len(items), _timer.ms, cid or "-",
    )
    return enriched


def build_post_document(
    post_id: str,
    user_id: str,
    mod_result: dict,
    body,
    dup_of: Optional[str],
    now: str,
) -> dict:
    """Build the MongoDB document for a new community post."""
    return {
        "id": post_id,
        "author_id": user_id,
        "title": mod_result["sanitized_title"],
        "content": mod_result["sanitized_content"],
        "content_html": None,
        "specialty_tags": body.specialty_tags,
        "topic_tags": body.topic_tags,
        "type": body.type,
        "status": mod_result["status"],
        "moderation_reason": mod_result["moderation_reason"],
        "moderated_by": None,
        "moderated_at": None,
        "ai_moderation_result": None,
        "stats": {"view_count": 0, "upvote_count": 0, "downvote_count": 0, "comment_count": 0, "report_count": 0, "score": 0},
        "image_ids": body.image_ids,
        "duplicate_of": dup_of,
        "is_duplicate": dup_of is not None,
        "educational_safety_approved": True,
        "ai_summary": None,
        "ai_mcq_ids": [],
        "ai_flashcard_ids": [],
        "created_at": now,
        "updated_at": now,
    }


def build_comment_document(
    comment_id: str,
    post_id: str,
    parent_id: Optional[str],
    user_id: str,
    mod_result: dict,
    now: str,
) -> dict:
    """Build the MongoDB document for a new community comment."""
    return {
        "id": comment_id,
        "post_id": post_id,
        "parent_id": parent_id,
        "author_id": user_id,
        "content": mod_result["sanitized_content"],
        "status": mod_result["status"],
        "moderation_reason": mod_result["moderation_reason"],
        "stats": {"upvote_count": 0, "downvote_count": 0, "score": 0, "report_count": 0},
        "created_at": now,
        "updated_at": now,
    }


def build_moderation_action_status_map(action: str) -> str:
    """Map moderation action string to status string."""
    return {
        "approve": "published",
        "hide": "hidden",
        "delete": "deleted",
        "queue": "moderation_queue",
    }.get(action, "published")


def build_moderation_action_update(
    action: str,
    new_status: str,
    admin_id: str,
    reason: Optional[str],
    now: str,
) -> dict:
    """Build the update dict for a moderation action on a target."""
    update = {
        "status": new_status,
        "moderated_by": admin_id,
        "moderated_at": now,
        "updated_at": now,
    }
    if reason:
        update["moderation_reason"] = reason
    if new_status == "deleted":
        update["content"] = "[deleted]"
    return update


def build_deleted_post_update(now: str) -> dict:
    """Build the update dict for soft-deleting a post."""
    return {
        "status": "deleted",
        "content": "[deleted]",
        "content_html": None,
        "title": "[deleted]",
        "image_ids": [],
        "moderated_by": None,
        "moderated_at": None,
        "updated_at": now,
    }


def build_deleted_comment_update(comment: dict, now: str) -> dict:
    """Build the update dict for soft-deleting a comment."""
    return {
        "status": "deleted",
        "content": "[deleted]",
        "post_id": comment.get("post_id"),
        "parent_id": comment.get("parent_id"),
        "author_id": comment.get("author_id"),
        "updated_at": now,
    }


def build_community_stats_response(
    total_posts: int,
    total_comments: int,
    posts_today: int,
    comments_today: int,
    posts_this_week: int,
    comments_this_week: int,
    queue_pending: int,
    queue_by_severity: dict,
) -> dict:
    """Build the community stats response dict."""
    return {
        "total_posts": total_posts,
        "total_comments": total_comments,
        "posts_today": posts_today,
        "comments_today": comments_today,
        "posts_this_week": posts_this_week,
        "comments_this_week": comments_this_week,
        "moderation_queue_pending": queue_pending,
        "moderation_queue_by_severity": queue_by_severity,
    }

