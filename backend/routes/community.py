"""Medical Community Routes: Posts, Comments, Reactions, Moderation, Feeds."""
from fastapi import APIRouter, HTTPException, Depends, Query
import uuid
import time
import asyncio
from datetime import datetime, timezone
from typing import Optional
from pymongo.errors import DuplicateKeyError

from database import db, logger
from models import (
    CommunityPostCreate, CommunityPostUpdate, CommunityPostResponse,
    CommunityPostListResponse, CommunityCommentCreate, CommunityCommentResponse,
    CommunityReaction, CommunityReport, CommunityFeedParams,
    ModerationAction,
)
from auth import get_current_user, get_admin_user
from services.community_service import (
    validate_post_content, validate_comment_content,
    validate_post_type, validate_specialty_tags, validate_topic_tags,
    validate_reason, validate_reaction, validate_target_type,
    validate_sort_option, validate_moderation_action,
    contains_html, sanitize_html,
    compute_text_similarity, is_duplicate,
    compute_hot_score, compute_trending_score,
    check_phi, check_dangerous_advice,
    check_post_rate, check_comment_rate, check_content_quality,
    check_burst_rate,
    extract_mentions,
)
from services.moderation_service import (
    evaluate_auto_moderation, is_title_all_caps, has_external_links,
    build_moderation_entry, should_auto_hide, should_auto_queue,
    check_profanity, increment_offense, build_audit_entry,
    AUTO_QUEUE_REASONS,
)

router = APIRouter(prefix="/api", tags=["community"])


async def _get_user_name(user_id: str) -> str:
    user = await db.users.find_one({"id": user_id}, {"name": 1})
    return user.get("name", "Unknown") if user else "Unknown"


async def _get_post_or_404(post_id: str) -> dict:
    post = await db.community_posts.find_one({"id": post_id})
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return post


async def _get_comment_or_404(comment_id: str) -> dict:
    comment = await db.community_comments.find_one({"id": comment_id})
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    return comment


def _visible_status_filter(user: dict) -> dict:
    """Return the status filter for post/comment queries based on user role."""
    if user.get("is_admin"):
        return {}
    return {"status": {"$in": ["published"]}}


async def _create_community_notification(
    user_id: str,
    notification_type: str,
    title: str,
    message: str,
    icon: str = "message-circle",
    data: Optional[dict] = None,
):
    """Create a notification for a community event."""
    try:
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
        logger.warning(f"Failed to create notification for {user_id}: {e}")


async def _aggregate_notification(
    user_id: str,
    notification_type: str,
    title: str,
    message: str,
    aggregate_key: str,
    icon: str = "message-circle",
    data: Optional[dict] = None,
):
    """Create or aggregate a notification. Merges with existing unread notification of same type+key."""
    now = datetime.now(timezone.utc).isoformat()
    try:
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
        logger.warning(f"Failed to aggregate notification for {user_id}: {e}")
        return None


async def _notify_mentioned_users(content: str, actor_id: str, actor_name: str, target_type: str, target_id: str):
    """Notify users mentioned with @username in content. Does NOT notify the actor."""
    mentions = extract_mentions(content)
    if not mentions:
        return
    for username in mentions:
        mentioned_user = await db.users.find_one({"name": username})
        if not mentioned_user:
            continue
        if mentioned_user["id"] == actor_id:
            continue
        await _create_community_notification(
            user_id=mentioned_user["id"],
            notification_type="community_mention",
            title=f"You were mentioned by {actor_name}",
            message=content[:200],
            icon="at-sign",
            data={"target_type": target_type, "target_id": target_id},
        )


# ── Posts ──


@router.post("/community/posts")
async def create_post(body: CommunityPostCreate, user: dict = Depends(get_current_user)):
    # Validate
    content_errs = validate_post_content(body.title, body.content)
    if content_errs:
        raise HTTPException(status_code=400, detail="; ".join(content_errs))

    type_err = validate_post_type(body.type)
    if type_err:
        raise HTTPException(status_code=400, detail=type_err)

    spec_errs = validate_specialty_tags(body.specialty_tags)
    if spec_errs:
        raise HTTPException(status_code=400, detail="; ".join(spec_errs))

    topic_errs = validate_topic_tags(body.topic_tags)
    if topic_errs:
        raise HTTPException(status_code=400, detail="; ".join(topic_errs))

    rate_err = check_post_rate(user["id"])
    if rate_err:
        raise HTTPException(status_code=429, detail=rate_err)

    burst_err = check_burst_rate(user["id"], "post")
    if burst_err:
        raise HTTPException(status_code=429, detail=burst_err)

    quality_err = check_content_quality(body.content)
    if quality_err:
        raise HTTPException(status_code=400, detail=quality_err)

    # Sanitize
    sanitized_title = sanitize_html(body.title)
    sanitized_content = sanitize_html(body.content)
    has_raw_html = contains_html(body.title) or contains_html(body.content)
    phi_findings = check_phi(body.content)
    dangerous_advice = check_dangerous_advice(body.content)
    title_caps = is_title_all_caps(body.title)
    ext_links = has_external_links(body.content)
    profanity_findings = check_profanity(f"{body.title} {body.content}")

    # Check for duplicates
    dup_of = None
    similar = await db.community_posts.find({
        "status": "published",
    }).sort("created_at", -1).limit(20).to_list(length=20)

    for existing in similar:
        if is_duplicate(body.title, body.content, existing.get("title", ""), existing.get("content", "")):
            dup_of = existing["id"]
            break

    # Auto-moderation
    user_doc = await db.users.find_one({"id": user["id"]})
    is_new_user = user_doc.get("created_at", "") > (datetime.now(timezone.utc).isoformat() if False else "")
    created_epoch = time.mktime(datetime.strptime(user_doc.get("created_at", "2025-01-01T00:00:00")[:19], "%Y-%m-%dT%H:%M:%S").timetuple()) if user_doc.get("created_at") else 0
    is_new = (time.time() - created_epoch) < 86400 * 7  # first week

    should_queue, reason_key, severity = evaluate_auto_moderation(
        is_new_user=is_new,
        contains_html=has_raw_html,
        phi_findings=phi_findings,
        dangerous_advice=dangerous_advice,
        has_external_links=ext_links,
        title_is_all_caps=title_caps,
        profanity_findings=profanity_findings,
    )

    status = "moderation_queue" if should_queue else "published"
    now = datetime.now(timezone.utc).isoformat()
    post_id = uuid.uuid4().hex

    post_doc = {
        "id": post_id,
        "author_id": user["id"],
        "title": sanitized_title,
        "content": sanitized_content,
        "content_html": None,
        "specialty_tags": body.specialty_tags,
        "topic_tags": body.topic_tags,
        "type": body.type,
        "status": status,
        "moderation_reason": AUTO_QUEUE_REASONS.get(reason_key) if should_queue else None,
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
    await db.community_posts.insert_one(post_doc)

    # Moderation queue entry if flagged
    if should_queue:
        entry = build_moderation_entry("post", post_id, AUTO_QUEUE_REASONS.get(reason_key, reason_key), reason_key, severity)
        try:
            await db.community_moderation_queue.insert_one(entry)
            # Track offense count for auto-lock
            if increment_offense(user["id"]):
                logger.info(f"Auto-lock threshold reached for user {user['id'][:8]}")
        except Exception as e:
            logger.warning(f"Failed to create moderation entry: {e}")

    # Notify @mentioned users
    asyncio.create_task(_notify_mentioned_users(body.content, user["id"], user.get("name", "Unknown"), "post", post_id))

    return {
        "id": post_id,
        "status": status,
        "is_duplicate": dup_of is not None,
        "created_at": now,
    }


@router.get("/community/feed")
async def get_feed(
    specialty: Optional[str] = Query(None),
    topic: Optional[str] = Query(None),
    post_type: Optional[str] = Query(None, alias="type"),
    sort: str = Query("recent"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    cursor: Optional[str] = Query(None),
    user: dict = Depends(get_current_user),
):
    sort_err = validate_sort_option(sort)
    if sort_err:
        raise HTTPException(status_code=400, detail=sort_err)

    query = {"status": "published"}
    if specialty:
        query["specialty_tags"] = specialty
    if topic:
        query["topic_tags"] = topic
    if post_type:
        type_err = validate_post_type(post_type)
        if type_err:
            raise HTTPException(status_code=400, detail=type_err)
        query["type"] = post_type
    if search:
        query["$text"] = {"$search": search}

    sort_config = {
        "recent": {"field": "created_at", "coerce": str},
        "trending": {"field": "created_at", "coerce": str},
        "top": {"field": "stats.score", "coerce": float},
        "discussed": {"field": "stats.comment_count", "coerce": int},
    }
    cfg = sort_config.get(sort, sort_config["recent"])
    sort_field = cfg["field"]
    sort_spec = [(sort_field, -1), ("_id", 1)]

    use_cursor_pagination = cursor is not None and cursor != ""

    if use_cursor_pagination:
        try:
            cursor_value = cfg["coerce"](cursor)
        except (ValueError, TypeError):
            raise HTTPException(status_code=400, detail="Invalid cursor value for this sort mode")
        query[sort_field] = {"$lt": cursor_value}
        db_cursor = db.community_posts.find(query).sort(sort_spec).limit(page_size)
        posts = await db_cursor.to_list(length=page_size)

        total = len(posts)
        next_cursor = str(posts[-1][sort_field]) if len(posts) == page_size else None
    else:
        total = await db.community_posts.count_documents(query)
        db_cursor = db.community_posts.find(query).sort(sort_spec).skip((page - 1) * page_size).limit(page_size)
        posts = await db_cursor.to_list(length=page_size)
        next_cursor = None

    # Batch load author names (fixes N+1)
    author_ids = list(set(p["author_id"] for p in posts if p.get("author_id")))
    author_names: dict[str, str] = {}
    if author_ids:
        user_cursor = db.users.find({"id": {"$in": author_ids}}, {"name": 1, "id": 1})
        async for user_doc in user_cursor:
            author_names[user_doc["id"]] = user_doc.get("name", "Unknown")

    results = []
    for p in posts:
        author_name = author_names.get(p["author_id"], "Unknown")
        results.append(CommunityPostResponse(
            id=p["id"],
            author_id=p["author_id"],
            author_name=author_name,
            title=p["title"],
            content=p["content"],
            content_html=p.get("content_html"),
            specialty_tags=p.get("specialty_tags", []),
            topic_tags=p.get("topic_tags", []),
            type=p.get("type", "discussion"),
            status=p.get("status", "published"),
            stats=p.get("stats", {}),
            image_ids=p.get("image_ids", []),
            is_duplicate=p.get("is_duplicate", False),
            duplicate_of=p.get("duplicate_of"),
            ai_summary=p.get("ai_summary"),
            educational_safety_approved=p.get("educational_safety_approved", False),
            created_at=p.get("created_at", ""),
            updated_at=p.get("updated_at", ""),
        ))

    return CommunityPostListResponse(posts=results, total=total, page=page, page_size=page_size, next_cursor=next_cursor)


@router.get("/community/posts/{post_id}")
async def get_post(post_id: str, user: dict = Depends(get_current_user)):
    post = await _get_post_or_404(post_id)
    author_name = await _get_user_name(post["author_id"])

    # Increment view count
    await db.community_posts.update_one({"id": post_id}, {"$inc": {"stats.view_count": 1}})

    # Get comments
    comments_cursor = db.community_comments.find({
        "post_id": post_id,
        **_visible_status_filter(user),
    }).sort("created_at", 1)
    comments = await comments_cursor.to_list(length=200)

    # Batch load comment author names (fixes N+1)
    comment_author_ids = list(set(c["author_id"] for c in comments if c.get("author_id")))
    comment_author_names: dict[str, str] = {}
    if comment_author_ids:
        user_cursor = db.users.find({"id": {"$in": comment_author_ids}}, {"name": 1, "id": 1})
        async for user_doc in user_cursor:
            comment_author_names[user_doc["id"]] = user_doc.get("name", "Unknown")

    enriched_comments = []
    for c in comments:
        enriched_comments.append(CommunityCommentResponse(
            id=c["id"],
            post_id=c["post_id"],
            parent_id=c.get("parent_id"),
            author_id=c["author_id"],
            author_name=comment_author_names.get(c["author_id"], "Unknown"),
            content=c["content"],
            status=c.get("status", "published"),
            stats=c.get("stats", {}),
            created_at=c.get("created_at", ""),
            updated_at=c.get("updated_at", ""),
        ))

    # Check user's reaction
    user_reaction = await db.community_reactions.find_one({
        "user_id": user["id"], "target_type": "post", "target_id": post_id,
    })

    return {
        "post": CommunityPostResponse(
            id=post["id"],
            author_id=post["author_id"],
            author_name=author_name,
            title=post["title"],
            content=post["content"],
            content_html=post.get("content_html"),
            specialty_tags=post.get("specialty_tags", []),
            topic_tags=post.get("topic_tags", []),
            type=post.get("type", "discussion"),
            status=post.get("status", "published"),
            stats=post.get("stats", {}),
            image_ids=post.get("image_ids", []),
            is_duplicate=post.get("is_duplicate", False),
            duplicate_of=post.get("duplicate_of"),
            ai_summary=post.get("ai_summary"),
            educational_safety_approved=post.get("educational_safety_approved", False),
            created_at=post.get("created_at", ""),
            updated_at=post.get("updated_at", ""),
        ),
        "comments": enriched_comments,
        "user_reaction": user_reaction["reaction"] if user_reaction else None,
    }


@router.put("/community/posts/{post_id}")
async def update_post(post_id: str, body: CommunityPostUpdate, user: dict = Depends(get_current_user)):
    post = await _get_post_or_404(post_id)
    if post["author_id"] != user["id"] and not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Not authorized to edit this post")
    if post["status"] == "deleted":
        raise HTTPException(status_code=400, detail="Cannot edit deleted post")

    update: dict = {"updated_at": datetime.now(timezone.utc).isoformat()}
    if body.title is not None:
        update["title"] = sanitize_html(body.title)
    if body.content is not None:
        update["content"] = sanitize_html(body.content)
    if body.specialty_tags is not None:
        errs = validate_specialty_tags(body.specialty_tags)
        if errs:
            raise HTTPException(status_code=400, detail="; ".join(errs))
        update["specialty_tags"] = body.specialty_tags
    if body.topic_tags is not None:
        errs = validate_topic_tags(body.topic_tags)
        if errs:
            raise HTTPException(status_code=400, detail="; ".join(errs))
        update["topic_tags"] = body.topic_tags

    await db.community_posts.update_one({"id": post_id}, {"$set": update})
    return {"status": "ok"}


@router.delete("/community/posts/{post_id}")
async def delete_post(post_id: str, user: dict = Depends(get_current_user)):
    post = await _get_post_or_404(post_id)
    if post["author_id"] != user["id"] and not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Not authorized to delete this post")

    now = datetime.now(timezone.utc).isoformat()
    await db.community_posts.update_one(
        {"id": post_id},
        {"$set": {"status": "deleted", "content": "[deleted]", "title": "[deleted]", "updated_at": now}},
    )
    return {"status": "ok"}


# ── Comments ──


@router.post("/community/comments")
async def create_comment(body: CommunityCommentCreate, user: dict = Depends(get_current_user)):
    post = await _get_post_or_404(body.post_id)
    if post["status"] != "published":
        raise HTTPException(status_code=400, detail="Cannot comment on non-published post")

    content_err = validate_comment_content(body.content)
    if content_err:
        raise HTTPException(status_code=400, detail=content_err)

    rate_err = check_comment_rate(user["id"])
    if rate_err:
        raise HTTPException(status_code=429, detail=rate_err)

    burst_err = check_burst_rate(user["id"], "comment")
    if burst_err:
        raise HTTPException(status_code=429, detail=burst_err)

    # Validate parent if provided
    parent = None
    if body.parent_id:
        parent = await _get_comment_or_404(body.parent_id)
        if parent["post_id"] != body.post_id:
            raise HTTPException(status_code=400, detail="Parent comment not in this post")

    sanitized = sanitize_html(body.content)
    phi_findings = check_phi(body.content)
    dangerous_advice = check_dangerous_advice(body.content)
    profanity_findings = check_profanity(body.content)
    should_queue, reason_key, severity = evaluate_auto_moderation(
        phi_findings=phi_findings,
        dangerous_advice=dangerous_advice,
        contains_html=contains_html(body.content),
        profanity_findings=profanity_findings,
    )

    status = "moderation_queue" if should_queue else "published"
    now = datetime.now(timezone.utc).isoformat()
    comment_id = uuid.uuid4().hex

    comment_doc = {
        "id": comment_id,
        "post_id": body.post_id,
        "parent_id": body.parent_id,
        "author_id": user["id"],
        "content": sanitized,
        "status": status,
        "moderation_reason": AUTO_QUEUE_REASONS.get(reason_key) if should_queue else None,
        "stats": {"upvote_count": 0, "downvote_count": 0, "score": 0, "report_count": 0},
        "created_at": now,
        "updated_at": now,
    }
    await db.community_comments.insert_one(comment_doc)

    # Update post comment count
    await db.community_posts.update_one(
        {"id": body.post_id},
        {"$inc": {"stats.comment_count": 1}},
    )

    # Moderation queue if flagged
    if should_queue:
        entry = build_moderation_entry("comment", comment_id, AUTO_QUEUE_REASONS.get(reason_key, reason_key), reason_key, severity)
        try:
            await db.community_moderation_queue.insert_one(entry)
            # Track offense count for auto-lock
            if increment_offense(user["id"]):
                logger.info(f"Auto-lock threshold reached for user {user['id'][:8]}")
        except Exception as e:
            logger.warning(f"Failed to create moderation entry: {e}")

    # Notifications (only for published comments)
    if status == "published":
        # Notify post author (aggregated)
        if post["author_id"] != user["id"]:
            asyncio.create_task(_aggregate_notification(
                user_id=post["author_id"],
                notification_type="community_comment",
                title="New comment on your post",
                message=sanitized[:200],
                aggregate_key=f"post:{body.post_id}",
                icon="message-circle",
                data={"target_type": "post", "target_id": body.post_id},
            ))
        # Notify parent comment author on reply (aggregated)
        if parent and parent["author_id"] != user["id"]:
            asyncio.create_task(_aggregate_notification(
                user_id=parent["author_id"],
                notification_type="community_reply",
                title="Reply to your comment",
                message=sanitized[:200],
                aggregate_key=f"comment:{body.parent_id}",
                icon="message-square",
                data={"target_type": "comment", "target_id": comment_id, "post_id": body.post_id},
            ))
        # Notify @mentioned users
        asyncio.create_task(_notify_mentioned_users(sanitized, user["id"], user.get("name", "Unknown"), "comment", comment_id))

    return {"id": comment_id, "status": status, "created_at": now}


@router.delete("/community/comments/{comment_id}")
async def delete_comment(comment_id: str, user: dict = Depends(get_current_user)):
    comment = await _get_comment_or_404(comment_id)
    if comment["author_id"] != user["id"] and not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Not authorized to delete this comment")

    now = datetime.now(timezone.utc).isoformat()
    await db.community_comments.update_one(
        {"id": comment_id},
        {"$set": {"status": "deleted", "content": "[deleted]", "updated_at": now}},
    )
    await db.community_posts.update_one(
        {"id": comment["post_id"]},
        {"$inc": {"stats.comment_count": -1}},
    )
    return {"status": "ok"}


# ── Reactions ──


@router.post("/community/reactions")
async def toggle_reaction(body: CommunityReaction, user: dict = Depends(get_current_user)):
    target_type_err = validate_target_type(body.target_type)
    if target_type_err:
        raise HTTPException(status_code=400, detail=target_type_err)
    reaction_err = validate_reaction(body.reaction)
    if reaction_err:
        raise HTTPException(status_code=400, detail=reaction_err)

    reaction_value = 1 if body.reaction == "upvote" else -1
    score_field = "upvote_count" if body.reaction == "upvote" else "downvote_count"

    collection = db.community_posts if body.target_type == "post" else db.community_comments
    target = await collection.find_one({"id": body.target_id}, {"author_id": 1})
    if not target:
        raise HTTPException(status_code=404, detail=f"{body.target_type} not found")
    target_author_id = target["author_id"]

    existing = await db.community_reactions.find_one({
        "user_id": user["id"],
        "target_type": body.target_type,
        "target_id": body.target_id,
    })

    if existing:
        if existing["reaction"] == body.reaction:
            # Remove reaction (toggle off)
            await db.community_reactions.delete_one({"id": existing["id"]})
            delta = -reaction_value
            inc_field = score_field
            score_delta = -reaction_value
        else:
            # Change reaction
            old_score_field = "upvote_count" if existing["reaction"] == "upvote" else "downvote_count"
            await db.community_reactions.update_one(
                {"id": existing["id"]},
                {"$set": {"reaction": body.reaction}},
            )
            delta = reaction_value
            score_delta = reaction_value * 2
            inc_field = score_field
            # Decrement old
            await collection.update_one(
                {"id": body.target_id},
                {"$inc": {f"stats.{old_score_field}": -1, "stats.score": -reaction_value if existing["reaction"] == "upvote" else 1}},
            )
    else:
        # New reaction
        try:
            await db.community_reactions.insert_one({
                "id": uuid.uuid4().hex,
                "user_id": user["id"],
                "target_type": body.target_type,
                "target_id": body.target_id,
                "reaction": body.reaction,
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
        except DuplicateKeyError:
            # Race: another request created this reaction first. Re-read to get its state.
            existing = await db.community_reactions.find_one({
                "user_id": user["id"],
                "target_type": body.target_type,
                "target_id": body.target_id,
            })
            if existing and existing["reaction"] == body.reaction:
                # Already has this reaction — toggle off instead
                await db.community_reactions.delete_one({"id": existing["id"]})
                delta = -reaction_value
                score_delta = -reaction_value
                inc_field = score_field
            else:
                # The other request already toggled/removed — no-op for stats
                delta = 0
                score_delta = 0
                inc_field = score_field
        else:
            delta = reaction_value
            score_delta = reaction_value
            inc_field = score_field

    await collection.update_one(
        {"id": body.target_id},
        {"$inc": {f"stats.{inc_field}": delta, "stats.score": score_delta}},
    )

    # Get updated counts
    updated = await collection.find_one({"id": body.target_id}, {"stats": 1, "author_id": 1})

    # Notify target author (aggregated)
    if target_author_id != user["id"]:
        asyncio.create_task(_aggregate_notification(
            user_id=target_author_id,
            notification_type="community_reaction",
            title=f"{user.get('name', 'Someone')} {body.reaction}d your {body.target_type}",
            message="",
            aggregate_key=f"reaction:{body.target_type}:{body.target_id}",
            icon="thumbs-up" if body.reaction == "upvote" else "thumbs-down",
            data={"target_type": body.target_type, "target_id": body.target_id, "reaction": body.reaction},
        ))

    return {"status": "ok", "stats": updated.get("stats", {}) if updated else {}}


# ── Reports ──


@router.post("/community/reports")
async def create_report(body: CommunityReport, user: dict = Depends(get_current_user)):
    target_type_err = validate_target_type(body.target_type)
    if target_type_err:
        raise HTTPException(status_code=400, detail=target_type_err)
    reason_err = validate_reason(body.reason)
    if reason_err:
        raise HTTPException(status_code=400, detail=reason_err)

    now = datetime.now(timezone.utc).isoformat()
    report_id = uuid.uuid4().hex

    await db.community_reports.insert_one({
        "id": report_id,
        "reporter_id": user["id"],
        "target_type": body.target_type,
        "target_id": body.target_id,
        "reason": body.reason,
        "description": body.description,
        "status": "open",
        "resolved_by": None,
        "resolved_at": None,
        "created_at": now,
    })

    # Update report count on target
    collection = db.community_posts if body.target_type == "post" else db.community_comments
    await collection.update_one(
        {"id": body.target_id},
        {"$inc": {"stats.report_count": 1}},
    )

    # Check auto-moderation thresholds
    target = await collection.find_one({"id": body.target_id}, {"stats": 1})
    report_count = (target.get("stats", {}) or {}).get("report_count", 0) if target else 1
    if should_auto_hide(report_count):
        await collection.update_one(
            {"id": body.target_id},
            {"$set": {"status": "hidden"}},
        )
    elif should_auto_queue(report_count):
        entry = build_moderation_entry(body.target_type, body.target_id, f"Reported ({body.reason})", "multiple_reports", "medium")
        try:
            existing = await db.community_moderation_queue.find_one({"target_type": body.target_type, "target_id": body.target_id})
            if not existing:
                await db.community_moderation_queue.insert_one(entry)
        except Exception as e:
            logger.warning(f"Failed to create moderation entry: {e}")

    return {"status": "ok", "report_id": report_id}


# ── Moderation (admin) ──


@router.get("/community/moderation/queue")
async def get_moderation_queue(
    severity: Optional[str] = Query(None),
    reviewed: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    cursor: Optional[str] = Query(None),
    admin: dict = Depends(get_admin_user),
):
    query: dict = {}
    if severity:
        query["severity"] = severity
    if reviewed is not None:
        query["reviewed"] = reviewed

    use_cursor = cursor is not None and cursor != ""
    next_cursor: Optional[str] = None

    if use_cursor:
        try:
            cursor_ts = float(cursor)
        except (ValueError, TypeError):
            raise HTTPException(status_code=400, detail="Invalid cursor — must be a Unix timestamp")
        query["created_at"] = {"$lt": cursor_ts}
        db_cursor = db.community_moderation_queue.find(query).sort("created_at", -1).limit(page_size)
        items = await db_cursor.to_list(length=page_size)
        total = len(items)
        if len(items) == page_size:
            next_cursor = str(items[-1]["created_at"])
    else:
        total = await db.community_moderation_queue.count_documents(query)
        db_cursor = db.community_moderation_queue.find(query).sort("created_at", -1).skip((page - 1) * page_size).limit(page_size)
        items = await db_cursor.to_list(length=page_size)

    # Enrich items with target content preview + author name
    enriched = []
    for item in items:
        target_preview = None
        target_author_id = None
        target_author_name = None
        collection = db.community_posts if item.get("target_type") == "post" else db.community_comments
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
                    target_author_name = await _get_user_name(target_author_id)

        enriched.append({
            **item,
            "target_preview": target_preview,
            "target_author_id": target_author_id,
            "target_author_name": target_author_name,
        })

    return {
        "items": enriched if enriched else items,
        "total": total,
        "page": page if not use_cursor else 0,
        "page_size": page_size,
        "next_cursor": next_cursor,
    }


@router.post("/community/moderation/action")
async def take_moderation_action(body: ModerationAction, admin: dict = Depends(get_admin_user)):
    action_err = validate_moderation_action(body.action)
    if action_err:
        raise HTTPException(status_code=400, detail=action_err)
    target_type_err = validate_target_type(body.target_type)
    if target_type_err:
        raise HTTPException(status_code=400, detail=target_type_err)

    now = datetime.now(timezone.utc).isoformat()
    collection = db.community_posts if body.target_type == "post" else db.community_comments

    target = await collection.find_one({"id": body.target_id})
    if not target:
        raise HTTPException(status_code=404, detail=f"{body.target_type} not found")

    status_map = {
        "approve": "published",
        "hide": "hidden",
        "delete": "deleted",
        "queue": "moderation_queue",
    }
    new_status = status_map.get(body.action, "published")

    update: dict = {
        "status": new_status,
        "moderated_by": admin["id"],
        "moderated_at": now,
        "updated_at": now,
    }
    if body.reason:
        update["moderation_reason"] = body.reason
    if new_status == "deleted":
        update["content"] = "[deleted]"
        if body.target_type == "post":
            update["title"] = "[deleted]"

    await collection.update_one({"id": body.target_id}, {"$set": update})

    # Update moderation queue entry
    await db.community_moderation_queue.update_one(
        {"target_type": body.target_type, "target_id": body.target_id},
        {"$set": {
            "reviewed": True,
            "reviewed_by": admin["id"],
            "reviewed_at": now,
            "action_taken": body.action,
        }},
    )

    # Audit log entry
    try:
        audit_entry = build_audit_entry(body.action, body.target_type, body.target_id, admin["id"], body.reason, {"previous_status": target.get("status")})
        await db.community_moderation_audit.insert_one(audit_entry)
    except Exception as e:
        logger.warning(f"Failed to create audit entry: {e}")

    return {"status": "ok", "new_status": new_status}


# ── User's posts ──


@router.get("/community/my-posts")
async def get_my_posts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: dict = Depends(get_current_user),
):
    query = {"author_id": user["id"]}
    total = await db.community_posts.count_documents(query)
    cursor = db.community_posts.find(query).sort("created_at", -1).skip((page - 1) * page_size).limit(page_size)
    posts = await cursor.to_list(length=page_size)

    results = []
    for p in posts:
        results.append(CommunityPostResponse(
            id=p["id"],
            author_id=p["author_id"],
            author_name=user.get("name", "Unknown"),
            title=p["title"],
            content=p["content"],
            specialty_tags=p.get("specialty_tags", []),
            topic_tags=p.get("topic_tags", []),
            type=p.get("type", "discussion"),
            status=p.get("status", "published"),
            stats=p.get("stats", {}),
            image_ids=p.get("image_ids", []),
            is_duplicate=p.get("is_duplicate", False),
            duplicate_of=p.get("duplicate_of"),
            ai_summary=p.get("ai_summary"),
            educational_safety_approved=p.get("educational_safety_approved", False),
            created_at=p.get("created_at", ""),
            updated_at=p.get("updated_at", ""),
        ))

    return CommunityPostListResponse(posts=results, total=total, page=page, page_size=page_size)


# ── Trending endpoint ──


@router.get("/community/trending")
async def get_trending(
    hours: int = Query(24, ge=1, le=168),
    limit: int = Query(20, ge=1, le=50),
    user: dict = Depends(get_current_user),
):
    """Return hot/trending posts based on engagement velocity."""
    cutoff = datetime.now(timezone.utc).timestamp() - hours * 3600
    since = datetime.fromtimestamp(cutoff, tz=timezone.utc).isoformat()

    pipeline = [
        {"$match": {"status": "published", "created_at": {"$gte": since}}},
        {"$addFields": {
            "hot_score": {
                "$function": {
                    "body": "function(up, down, created) { var score = up - down; if (score <= 0) return 0; var age = (Date.now() - new Date(created).getTime()) / 3600000; return Math.max(0, Math.log10(Math.max(score, 1)) + score / Math.max(age + 2, 1)); }",
                    "args": ["$stats.upvote_count", "$stats.downvote_count", "$created_at"],
                    "lang": "js",
                }
            }
        }},
        {"$sort": {"hot_score": -1}},
        {"$limit": limit},
    ]

    try:
        cursor = db.community_posts.aggregate(pipeline)
        posts = await cursor.to_list(length=limit)
    except Exception:
        # Fallback: sort by score
        cursor = db.community_posts.find({"status": "published", "created_at": {"$gte": since}}).sort("stats.score", -1).limit(limit)
        posts = await cursor.to_list(length=limit)

    # Batch load author names (fixes N+1)
    author_ids = list(set(p["author_id"] for p in posts if p.get("author_id")))
    author_names: dict[str, str] = {}
    if author_ids:
        user_cursor = db.users.find({"id": {"$in": author_ids}}, {"name": 1, "id": 1})
        async for user_doc in user_cursor:
            author_names[user_doc["id"]] = user_doc.get("name", "Unknown")

    results = []
    for p in posts:
        results.append(CommunityPostResponse(
            id=p["id"],
            author_id=p["author_id"],
            author_name=author_names.get(p["author_id"], "Unknown"),
            title=p["title"],
            content=p["content"],
            specialty_tags=p.get("specialty_tags", []),
            topic_tags=p.get("topic_tags", []),
            type=p.get("type", "discussion"),
            status=p.get("status", "published"),
            stats=p.get("stats", {}),
            image_ids=p.get("image_ids", []),
            is_duplicate=p.get("is_duplicate", False),
            duplicate_of=p.get("duplicate_of"),
            ai_summary=p.get("ai_summary"),
            educational_safety_approved=p.get("educational_safety_approved", False),
            created_at=p.get("created_at", ""),
            updated_at=p.get("updated_at", ""),
        ))

    return {"posts": results}


# ── Community Stats ──


@router.get("/community/stats")
async def get_community_stats(user: dict = Depends(get_current_user)):
    """Aggregate community activity counters."""
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    week_ago = datetime.fromtimestamp(now.timestamp() - 86400 * 7, tz=timezone.utc).isoformat()

    total_posts = await db.community_posts.count_documents({"status": "published"})
    total_comments = await db.community_comments.count_documents({"status": "published"})
    posts_today = await db.community_posts.count_documents({"status": "published", "created_at": {"$gte": today_start}})
    comments_today = await db.community_comments.count_documents({"status": "published", "created_at": {"$gte": today_start}})
    posts_this_week = await db.community_posts.count_documents({"status": "published", "created_at": {"$gte": week_ago}})
    comments_this_week = await db.community_comments.count_documents({"status": "published", "created_at": {"$gte": week_ago}})

    queue_pending = await db.community_moderation_queue.count_documents({"reviewed": False})
    queue_by_severity = {
        s: await db.community_moderation_queue.count_documents({"reviewed": False, "severity": s})
        for s in ("critical", "high", "medium", "low")
    }

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


# ── Tags (known lists) ──


@router.get("/community/tags")
async def get_known_tags(user: dict = Depends(get_current_user)):
    from services.community_service import KNOWN_SPECIALTIES, KNOWN_TOPICS
    return {
        "specialties": sorted(KNOWN_SPECIALTIES),
        "topics": sorted(KNOWN_TOPICS),
        "post_types": ["question", "discussion", "case_study", "resource"],
    }
