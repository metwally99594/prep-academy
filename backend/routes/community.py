"""Medical Community Routes: Posts, Comments, Reactions, Moderation, Feeds."""
from fastapi import APIRouter, HTTPException, Depends, Query, UploadFile, File
import uuid
import asyncio
import base64
from datetime import datetime, timezone
from typing import Optional

from database import db, logger
from models import (
    CommunityPostCreate, CommunityPostUpdate,
    CommunityPostListResponse, CommunityCommentCreate,
    CommunityReaction, CommunityReport,
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
    check_post_rate, check_comment_rate,
    check_burst_rate,
    batch_load_author_names, enrich_post_response, enrich_comment_response,
    get_user_name, get_post_or_404, get_comment_or_404,
    visible_status_filter, build_feed_query,
    handle_reaction_toggle, find_duplicate_post,
    FEED_PROJECTION,
)
from services.moderation_service import (
    evaluate_auto_moderation, is_title_all_caps, has_external_links,
    build_moderation_entry, should_auto_hide, should_auto_queue,
    check_profanity, increment_offense, build_audit_entry,
    check_content_quality,
    AUTO_QUEUE_REASONS,
)
from services.community_cache import cache_get, cache_set, cache_invalidate, build_cache_key
from services.community_serializers import (
    build_post_document, build_comment_document,
    build_deleted_post_update, build_deleted_comment_update,
    build_moderation_action_status_map, build_moderation_action_update,
    build_community_stats_response,
    enrich_moderation_queue_items,
)
from services.community_feed_query import (
    build_report_document,
)
from services.community_pagination import (
    paginate_feed, paginate_moderation_queue, paginate_audit,
)
from services.community_feed_query import (
    build_stats_queries, build_trending_query,
)
from services.community_moderation_orchestrator import (
    orchestrate_post_moderation, orchestrate_comment_moderation,
    handle_moderation_queue_insert, handle_report_moderation,
)
from services.notification_service import (
    aggregate_notification, notify_mentioned_users,
    get_user_notifications, mark_all_read,
    dispatch_comment_notifications,
)
from services.community_observability import (
    Timer, get_correlation_id,
    log_moderation_action, log_notification_event,
    log_cache_event, log_feed_event,
)

router = APIRouter(prefix="/api", tags=["community"])


# ── Index recommendations (apply manually via mongosh) ──
# See services/community_index_audit.py for full analysis + bottleneck report.
# Key additions beyond what server.py already creates:
#   db.notifications.createIndex({user_id:1, created_at:-1})
#   db.notifications.createIndex({user_id:1, read:1, created_at:-1})
#   db.community_moderation_audit.createIndex({created_at:-1})





def _cache_invalidate_logged():
    cache_invalidate()
    logger.info("cache=invalidate")





# ── Posts ──


@router.post("/community/posts")
async def create_post(body: CommunityPostCreate, user: dict = Depends(get_current_user)):
    _timer = Timer()
    cid = get_correlation_id() or "-"
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

    with _timer:
        user_doc = await db.users.find_one({"id": user["id"]})
        mod_result = await orchestrate_post_moderation(body.title, body.content, user["id"], user_doc)

        dup_of = await find_duplicate_post(db, body.title, body.content)

        now = datetime.now(timezone.utc).isoformat()
        post_id = uuid.uuid4().hex

        post_doc = build_post_document(
            post_id=post_id,
            user_id=user["id"],
            mod_result=mod_result,
            body=body,
            dup_of=dup_of,
            now=now,
        )
        await db.community_posts.insert_one(post_doc)
        _cache_invalidate_logged()

        if mod_result["should_queue"] and not mod_result["is_shadow_hidden"]:
            await handle_moderation_queue_insert(
                "post", post_id,
                mod_result["moderation_reason"] or mod_result["reason_key"],
                mod_result["reason_key"], mod_result["severity"],
                user["id"],
            )

        asyncio.create_task(notify_mentioned_users(body.content, user["id"], user.get("name", "Unknown"), "post", post_id))

    logger.info("post=created id=%s user=%s status=%s duration_ms=%.1f correlation_id=%s",
                post_id[:8], user["id"][:8], mod_result["status"], _timer.ms, cid)
    return {"id": post_id, "status": mod_result["status"], "is_duplicate": dup_of is not None, "created_at": now}


ALLOWED_MEDIA_TYPES = {
    "image/jpeg", "image/png", "image/webp", "image/gif",
    "video/mp4", "video/webm", "video/quicktime",
}
MAX_MEDIA_SIZE = 50 * 1024 * 1024  # 50 MB


@router.post("/community/upload")
async def upload_community_media(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    if file.content_type not in ALLOWED_MEDIA_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported media type '{file.content_type}'")

    contents = await file.read()
    if len(contents) > MAX_MEDIA_SIZE:
        raise HTTPException(status_code=400, detail=f"File too large ({len(contents)} bytes, max 50 MB)")

    encoded = base64.b64encode(contents).decode()
    media_type = "image" if file.content_type.startswith("image/") else "video"
    data_uri = f"data:{file.content_type};base64,{encoded}"

    media_id = uuid.uuid4().hex
    now = datetime.now(timezone.utc).isoformat()
    media_doc = {
        "id": media_id,
        "user_id": user["id"],
        "filename": file.filename or "untitled",
        "mime_type": file.content_type,
        "media_type": media_type,
        "size_bytes": len(contents),
        "data_uri": data_uri,
        "created_at": now,
    }
    await db.community_media.insert_one(media_doc)

    return {
        "id": media_id,
        "filename": media_doc["filename"],
        "mime_type": media_doc["mime_type"],
        "media_type": media_type,
        "size_bytes": media_doc["size_bytes"],
        "data_uri": data_uri,
    }


@router.get("/community/media/{media_id}")
async def get_community_media(media_id: str, user: dict = Depends(get_current_user)):
    media = await db.community_media.find_one({"id": media_id}, {"_id": 0})
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")
    return media


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
    _timer = Timer()
    cid = get_correlation_id()
    sort_err = validate_sort_option(sort)
    if sort_err:
        raise HTTPException(status_code=400, detail=sort_err)
    page_size = min(page_size, 50)

    cache_key = build_cache_key("feed", sort=sort, specialty=specialty, topic=topic, post_type=post_type, search=search, page=page, page_size=page_size, cursor=cursor)
    with _timer:
        cached = cache_get(cache_key)
    log_cache_event(logger, "get", cache_key=cache_key, duration_ms=_timer.ms, correlation_id=cid, hit=str(cached is not None))
    if cached is not None:
        log_feed_event(logger, "cached_hit", sort=sort, page_size=page_size, result_count=len(cached.get("posts", [])), correlation_id=cid)
        return CommunityPostListResponse(**cached)

    with _timer:
        query = build_feed_query(specialty, topic, post_type, search)
        use_cursor_pagination = cursor is not None and cursor != ""

        paginated = await paginate_feed(
            db=db, query=query, sort=sort,
            page=page, page_size=page_size,
            cursor=cursor, use_cursor=use_cursor_pagination,
        )
        response = CommunityPostListResponse(**paginated)
        cache_set(cache_key, response.model_dump())

    log_feed_event(logger, "built", sort=sort, page_size=page_size, result_count=len(paginated["posts"]), duration_ms=_timer.ms, cached=False, correlation_id=cid)
    return response


@router.get("/community/posts/{post_id}")
async def get_post(post_id: str, user: dict = Depends(get_current_user)):
    _timer = Timer()
    cid = get_correlation_id() or "-"
    with _timer:
        post = await get_post_or_404(post_id)

        await db.community_posts.update_one({"id": post_id}, {"$inc": {"stats.view_count": 1}})

        comments = await db.community_comments.find(
            {"post_id": post_id, **visible_status_filter(user)}
        ).sort("created_at", 1).to_list(length=200)

        comment_author_ids = list(set(c["author_id"] for c in comments if c.get("author_id")))
        comment_author_names = await batch_load_author_names(comment_author_ids)

        enriched_comments = [enrich_comment_response(c, comment_author_names.get(c["author_id"], "Unknown")) for c in comments]

        user_reaction = await db.community_reactions.find_one(
            {"user_id": user["id"], "target_type": "post", "target_id": post_id},
        )

        response = {
            "post": enrich_post_response(post, await get_user_name(post["author_id"])),
            "comments": enriched_comments,
            "user_reaction": user_reaction["reaction"] if user_reaction else None,
        }

    logger.info("post=get id=%s duration_ms=%.1f correlation_id=%s", post_id[:8], _timer.ms, cid)
    return response


@router.put("/community/posts/{post_id}")
async def update_post(post_id: str, body: CommunityPostUpdate, user: dict = Depends(get_current_user)):
    _timer = Timer()
    cid = get_correlation_id() or "-"
    post = await get_post_or_404(post_id)
    if post["author_id"] != user["id"] and not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Not authorized to edit this post")
    if post["status"] == "deleted":
        raise HTTPException(status_code=400, detail="Cannot edit deleted post")

    with _timer:
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

    logger.info("post=updated id=%s duration_ms=%.1f correlation_id=%s", post_id[:8], _timer.ms, cid)
    return {"status": "ok"}


@router.delete("/community/posts/{post_id}")
async def delete_post(post_id: str, user: dict = Depends(get_current_user)):
    _timer = Timer()
    cid = get_correlation_id() or "-"
    post = await get_post_or_404(post_id)
    if post["author_id"] != user["id"] and not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Not authorized to delete this post")

    with _timer:
        now = datetime.now(timezone.utc).isoformat()
        await db.community_posts.update_one(
            {"id": post_id},
            {"$set": build_deleted_post_update(now)},
        )

    logger.info("post=deleted id=%s author=%s duration_ms=%.1f correlation_id=%s", post_id[:8], user["id"][:8], _timer.ms, cid)
    return {"status": "ok"}


# ── Comments ──


@router.post("/community/comments")
async def create_comment(body: CommunityCommentCreate, user: dict = Depends(get_current_user)):
    _timer = Timer()
    cid = get_correlation_id() or "-"
    post = await get_post_or_404(body.post_id)
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

    parent = None
    if body.parent_id:
        parent = await get_comment_or_404(body.parent_id)
        if parent["post_id"] != body.post_id:
            raise HTTPException(status_code=400, detail="Parent comment not in this post")

    with _timer:
        user_doc = await db.users.find_one({"id": user["id"]})
        mod_result = await orchestrate_comment_moderation(body.content, user["id"], user_doc)

        now = datetime.now(timezone.utc).isoformat()
        comment_id = uuid.uuid4().hex

        comment_doc = build_comment_document(
            comment_id=comment_id,
            post_id=body.post_id,
            parent_id=body.parent_id,
            user_id=user["id"],
            mod_result=mod_result,
            now=now,
        )
        await db.community_comments.insert_one(comment_doc)
        await db.community_posts.update_one(
            {"id": body.post_id},
            {"$inc": {"stats.comment_count": 1}},
        )
        _cache_invalidate_logged()

        if mod_result["should_queue"] and not mod_result["is_shadow_hidden"]:
            await handle_moderation_queue_insert(
                "comment", comment_id,
                mod_result["moderation_reason"] or mod_result["reason_key"],
                mod_result["reason_key"], mod_result["severity"],
                user["id"],
            )

    if mod_result["status"] == "published":
        dispatch_comment_notifications(
            post_author_id=post["author_id"],
            commenter_id=user["id"],
            parent_author_id=parent["author_id"] if parent else None,
            sanitized_content=mod_result["sanitized_content"],
            post_id=body.post_id,
            comment_id=comment_id,
            parent_id=body.parent_id,
            commenter_name=user.get("name", "Unknown"),
        )
        log_notification_event(logger, "comment_created", user_id=user["id"], notification_type="community_comment",
                               correlation_id=get_correlation_id(), post_id=body.post_id[:8])

    logger.info("comment=created id=%s post=%s status=%s duration_ms=%.1f correlation_id=%s",
                comment_id[:8], body.post_id[:8], mod_result["status"], _timer.ms, cid)
    return {"id": comment_id, "status": mod_result["status"], "created_at": now}


@router.delete("/community/comments/{comment_id}")
async def delete_comment(comment_id: str, user: dict = Depends(get_current_user)):
    _timer = Timer()
    cid = get_correlation_id() or "-"
    comment = await get_comment_or_404(comment_id)
    if comment["author_id"] != user["id"] and not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Not authorized to delete this comment")

    with _timer:
        now = datetime.now(timezone.utc).isoformat()
        await db.community_comments.update_one(
            {"id": comment_id},
            {"$set": build_deleted_comment_update(comment, now)},
        )
        await db.community_posts.update_one(
            {"id": comment["post_id"]},
            {"$inc": {"stats.comment_count": -1}},
        )
    logger.info("comment=deleted id=%s post=%s duration_ms=%.1f correlation_id=%s", comment_id[:8], comment["post_id"][:8], _timer.ms, cid)
    return {"status": "ok"}


# ── Reactions ──


@router.post("/community/reactions")
async def toggle_reaction(body: CommunityReaction, user: dict = Depends(get_current_user)):
    _timer = Timer()
    cid = get_correlation_id()
    target_type_err = validate_target_type(body.target_type)
    if target_type_err:
        raise HTTPException(status_code=400, detail=target_type_err)
    reaction_err = validate_reaction(body.reaction)
    if reaction_err:
        raise HTTPException(status_code=400, detail=reaction_err)

    with _timer:
        result = await handle_reaction_toggle(
            user_id=user["id"],
            target_type=body.target_type,
            target_id=body.target_id,
            reaction=body.reaction,
        )
        if not result["found"]:
            raise HTTPException(status_code=404, detail=f"{body.target_type} not found")

        _cache_invalidate_logged()

        if result["had_race"]:
            logger.info("reaction=race_resolved user=%s target=%s correlation_id=%s", user["id"][:8], body.target_id[:8], cid)

        collection = db.community_posts if body.target_type == "post" else db.community_comments
        updated = await collection.find_one({"id": body.target_id}, {"stats": 1})

        if result["target_author_id"] != user["id"]:
            asyncio.create_task(aggregate_notification(
                user_id=result["target_author_id"],
                notification_type="community_reaction",
                title=f"{user.get('name', 'Someone')} {body.reaction}d your {body.target_type}",
                message="",
                aggregate_key=f"reaction:{body.target_type}:{body.target_id}",
                icon="thumbs-up" if body.reaction == "upvote" else "thumbs-down",
                data={"target_type": body.target_type, "target_id": body.target_id, "reaction": body.reaction},
            ))

    logger.info("reaction=completed user=%s target=%s reaction=%s duration_ms=%.1f correlation_id=%s",
                user["id"][:8], body.target_id[:8], body.reaction, _timer.ms, cid)
    return {"status": "ok", "stats": updated.get("stats", {}) if updated else {}}


# ── Reports ──


@router.post("/community/reports")
async def create_report(body: CommunityReport, user: dict = Depends(get_current_user)):
    _timer = Timer()
    cid = get_correlation_id() or "-"
    target_type_err = validate_target_type(body.target_type)
    if target_type_err:
        raise HTTPException(status_code=400, detail=target_type_err)
    reason_err = validate_reason(body.reason)
    if reason_err:
        raise HTTPException(status_code=400, detail=reason_err)

    with _timer:
        now = datetime.now(timezone.utc).isoformat()
        report_id = uuid.uuid4().hex

        await db.community_reports.insert_one(build_report_document(
            report_id=report_id,
            user_id=user["id"],
            target_type=body.target_type,
            target_id=body.target_id,
            reason=body.reason,
            description=body.description,
            now=now,
        ))

        collection = db.community_posts if body.target_type == "post" else db.community_comments
        await collection.update_one(
            {"id": body.target_id},
            {"$inc": {"stats.report_count": 1}},
        )

        await handle_report_moderation(body.target_type, body.target_id, body.reason)

    logger.info("report=created id=%s target=%s reason=%s duration_ms=%.1f correlation_id=%s",
                report_id[:8], body.target_id[:8], body.reason, _timer.ms, cid)
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
    _timer = Timer()
    cid = get_correlation_id() or "-"
    query: dict = {}
    if severity:
        query["severity"] = severity
    if reviewed is not None:
        query["reviewed"] = reviewed

    with _timer:
        use_cursor = cursor is not None and cursor != ""

        paginated = await paginate_moderation_queue(
            db=db, query=query, page=page, page_size=page_size,
            cursor=cursor, use_cursor=use_cursor,
        )

        enriched = await enrich_moderation_queue_items(
            items=paginated["items"], db=db, get_user_name=get_user_name,
        )

        result = {
            "items": enriched if enriched else paginated["items"],
            "total": paginated["total"],
            "page": paginated["page"],
            "page_size": paginated["page_size"],
            "next_cursor": paginated["next_cursor"],
        }

    logger.info("mod_queue=listed severity=%s reviewed=%s items=%d duration_ms=%.1f correlation_id=%s",
                severity or "all", reviewed if reviewed is not None else "all", paginated["total"], _timer.ms, cid)
    return result


@router.post("/community/moderation/action")
async def take_moderation_action(body: ModerationAction, admin: dict = Depends(get_admin_user)):
    _timer = Timer()
    cid = get_correlation_id()
    action_err = validate_moderation_action(body.action)
    if action_err:
        raise HTTPException(status_code=400, detail=action_err)
    target_type_err = validate_target_type(body.target_type)
    if target_type_err:
        raise HTTPException(status_code=400, detail=target_type_err)

    with _timer:
        now = datetime.now(timezone.utc).isoformat()
        collection = db.community_posts if body.target_type == "post" else db.community_comments

        target = await collection.find_one({"id": body.target_id})
        if not target:
            raise HTTPException(status_code=404, detail=f"{body.target_type} not found")

        new_status = build_moderation_action_status_map(body.action)
        update = build_moderation_action_update(body.action, new_status, admin["id"], body.reason, now)
        if new_status == "deleted" and body.target_type == "post":
            update["title"] = "[deleted]"

        await collection.update_one({"id": body.target_id}, {"$set": update})

        await db.community_moderation_queue.update_one(
            {"target_type": body.target_type, "target_id": body.target_id},
            {"$set": {
                "reviewed": True,
                "reviewed_by": admin["id"],
                "reviewed_at": now,
                "action_taken": body.action,
            }},
        )

        _cache_invalidate_logged()
        try:
            audit_entry = build_audit_entry(body.action, body.target_type, body.target_id, admin["id"], body.reason, {"previous_status": target.get("status")})
            await db.community_moderation_audit.insert_one(audit_entry)
        except Exception as e:
            logger.warning("mod_action=audit_failed error=%s", e)

    log_moderation_action(logger, body.action, body.target_type, body.target_id,
                          admin_id=admin["id"], duration_ms=_timer.ms, correlation_id=cid)
    return {"status": "ok", "new_status": new_status}


@router.get("/community/moderation/audit")
async def get_moderation_audit(
    page_size: int = Query(20, ge=1, le=100),
    cursor: Optional[str] = Query(None),
    admin: dict = Depends(get_admin_user),
):
    _timer = Timer()
    cid = get_correlation_id() or "-"
    with _timer:
        result = await paginate_audit(db=db, page_size=page_size, cursor=cursor)
        admin_ids = list(set(item.get("admin_id") for item in result["items"] if item.get("admin_id")))
        admin_names = await batch_load_author_names(admin_ids) if admin_ids else {}
        for item in result["items"]:
            item["admin_name"] = admin_names.get(item.get("admin_id"), "Unknown")

    logger.info("mod_audit=listed items=%d duration_ms=%.1f correlation_id=%s",
                len(result["items"]), _timer.ms, cid)
    return result


# ── User's posts ──


@router.get("/community/my-posts")
async def get_my_posts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: dict = Depends(get_current_user),
):
    _timer = Timer()
    cid = get_correlation_id() or "-"
    with _timer:
        query = {"author_id": user["id"]}
        total = await db.community_posts.count_documents(query)
        posts = await db.community_posts.find(query).sort("created_at", -1).skip((page - 1) * page_size).limit(page_size).to_list(length=page_size)
        results = [enrich_post_response(p, user.get("name", "Unknown")) for p in posts]
        response = CommunityPostListResponse(posts=results, total=total, page=page, page_size=page_size)

    logger.info("my_posts=listed user=%s total=%d duration_ms=%.1f correlation_id=%s", user["id"][:8], total, _timer.ms, cid)
    return response


# ── Trending endpoint ──


@router.get("/community/trending")
async def get_trending(
    hours: int = Query(24, ge=1, le=168),
    limit: int = Query(20, ge=1, le=50),
    user: dict = Depends(get_current_user),
):
    _timer = Timer()
    limit = min(limit, 50)
    cache_key = build_cache_key("trending", hours=hours, limit=limit)
    cached = cache_get(cache_key)
    if cached is not None:
        log_cache_event(logger, "hit", cache_key=cache_key, correlation_id=get_correlation_id())
        return cached

    with _timer:
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
            posts = await db.community_posts.aggregate(pipeline).to_list(length=limit)
        except Exception:
            posts = await db.community_posts.find(
                {"status": "published", "created_at": {"$gte": since}},
                {"_id": 1, "id": 1, "author_id": 1, "title": 1, "content": 1,
                 "specialty_tags": 1, "topic_tags": 1, "type": 1, "status": 1,
                 "stats": 1, "image_ids": 1, "is_duplicate": 1, "duplicate_of": 1,
                 "ai_summary": 1, "educational_safety_approved": 1,
                 "created_at": 1, "updated_at": 1},
            ).sort("stats.score", -1).limit(limit).to_list(length=limit)

        author_ids = list(set(p["author_id"] for p in posts if p.get("author_id")))
        author_names = await batch_load_author_names(author_ids)
        results = [enrich_post_response(p, author_names.get(p["author_id"], "Unknown")) for p in posts]

        response = {"posts": results}
        cache_set(cache_key, response)

    log_cache_event(logger, "set", cache_key=cache_key, duration_ms=_timer.ms, correlation_id=get_correlation_id())
    return response


# ── Community Stats ──


@router.get("/community/stats")
async def get_community_stats(user: dict = Depends(get_current_user)):
    _timer = Timer()
    cid = get_correlation_id() or "-"
    cache_key = build_cache_key("stats")
    cached = cache_get(cache_key)
    if cached is not None:
        log_cache_event(logger, "hit", cache_key=cache_key, correlation_id=cid)
        return cached

    with _timer:
        bounds = build_stats_queries(db)

        total_posts = await db.community_posts.count_documents({"status": "published"})
        total_comments = await db.community_comments.count_documents({"status": "published"})
        posts_today = await db.community_posts.count_documents({"status": "published", "created_at": {"$gte": bounds["today_start"]}})
        comments_today = await db.community_comments.count_documents({"status": "published", "created_at": {"$gte": bounds["today_start"]}})
        posts_this_week = await db.community_posts.count_documents({"status": "published", "created_at": {"$gte": bounds["week_ago"]}})
        comments_this_week = await db.community_comments.count_documents({"status": "published", "created_at": {"$gte": bounds["week_ago"]}})

        queue_pending = await db.community_moderation_queue.count_documents({"reviewed": False})
        queue_by_severity = {
            s: await db.community_moderation_queue.count_documents({"reviewed": False, "severity": s})
            for s in ("critical", "high", "medium", "low")
        }

        response = build_community_stats_response(
            total_posts=total_posts,
            total_comments=total_comments,
            posts_today=posts_today,
            comments_today=comments_today,
            posts_this_week=posts_this_week,
            comments_this_week=comments_this_week,
            queue_pending=queue_pending,
            queue_by_severity=queue_by_severity,
        )
        cache_set(cache_key, response, ttl=60)

    log_cache_event(logger, "set", cache_key=cache_key, duration_ms=_timer.ms, correlation_id=cid)
    return response


# ── Notification Center ──


@router.get("/community/notifications")
async def get_community_notifications(
    limit: int = Query(20, ge=1, le=100),
    cursor: Optional[str] = Query(None),
    user: dict = Depends(get_current_user),
):
    _timer = Timer()
    cid = get_correlation_id() or "-"
    with _timer:
        result = await get_user_notifications(user_id=user["id"], limit=limit, cursor=cursor)
    log_notification_event(logger, "list", user_id=user["id"], count=len(result.get("notifications", [])),
                           duration_ms=_timer.ms, correlation_id=cid)
    return result


@router.post("/community/notifications/mark-all-read")
async def mark_all_notifications_read(user: dict = Depends(get_current_user)):
    _timer = Timer()
    cid = get_correlation_id() or "-"
    with _timer:
        count = await mark_all_read(user["id"])
    log_notification_event(logger, "mark_all_read", user_id=user["id"], count=count,
                           duration_ms=_timer.ms, correlation_id=cid)
    return {"status": "ok", "modified_count": count}


# ── Tags (known lists) ──


@router.get("/community/tags")
async def get_known_tags(user: dict = Depends(get_current_user)):
    from services.community_service import KNOWN_SPECIALTIES, KNOWN_TOPICS
    return {
        "specialties": sorted(KNOWN_SPECIALTIES),
        "topics": sorted(KNOWN_TOPICS),
        "post_types": ["question", "discussion", "case_study", "resource"],
    }
