"""Pagination response builders for community endpoints.

Extracted from routes/community.py.
Backward-compatible: preserves cursor and offset pagination behavior.
"""
from typing import Optional

from services.community_service import (
    get_sort_config, get_sort_spec, parse_cursor,
    batch_load_author_names, enrich_post_response, FEED_PROJECTION,
)
from services.community_observability import Timer


async def paginate_feed(
    db,
    query: dict,
    sort: str,
    page: int,
    page_size: int,
    cursor: Optional[str] = None,
    use_cursor: bool = False,
) -> dict:
    """Paginate feed results using cursor-based or offset-based pagination.

    Returns dict with: posts, total, page, page_size, next_cursor.
    Backward-compatible: same return shape as original inline code.
    """
    cfg = get_sort_config(sort)
    sort_field = cfg["field"]
    sort_spec = get_sort_spec(sort_field)

    posts = []
    total = 0
    next_cursor = None

    query_timer = Timer()
    with query_timer:
        if use_cursor:
            cursor_value = parse_cursor(cursor, cfg["coerce"])
            if cursor_value is None:
                from fastapi import HTTPException
                raise HTTPException(status_code=400, detail="Invalid cursor value for this sort mode")
            cursor_query = dict(query)
            cursor_query[sort_field] = {"$lt": cursor_value}
            posts = await db.community_posts.find(cursor_query, FEED_PROJECTION).sort(sort_spec).limit(page_size).to_list(length=page_size)
            total = len(posts)
            if len(posts) == page_size:
                next_cursor = str(posts[-1][sort_field])
        else:
            total = await db.community_posts.count_documents(query)
            posts = await db.community_posts.find(query, FEED_PROJECTION).sort(sort_spec).skip((page - 1) * page_size).limit(page_size).to_list(length=page_size)

    author_ids = list(set(p["author_id"] for p in posts if p.get("author_id")))
    author_names = await batch_load_author_names(author_ids)
    results = [enrich_post_response(p, author_names.get(p["author_id"], "Unknown")) for p in posts]

    return {
        "posts": results,
        "total": total,
        "page": page,
        "page_size": page_size,
        "next_cursor": next_cursor,
    }


async def paginate_moderation_queue(
    db,
    query: dict,
    page: int,
    page_size: int,
    cursor: Optional[str] = None,
    use_cursor: bool = False,
) -> dict:
    """Paginate moderation queue results using cursor or offset pagination.

    Returns dict with: items, total, page, page_size, next_cursor.
    Backward-compatible: preserves existing response shape.
    """
    next_cursor = None
    items = []

    query_timer = Timer()
    with query_timer:
        if use_cursor:
            try:
                cursor_ts = float(cursor)
            except (ValueError, TypeError):
                from fastapi import HTTPException
                raise HTTPException(status_code=400, detail="Invalid cursor — must be a Unix timestamp")
            query["created_at"] = {"$lt": cursor_ts}
            items = await db.community_moderation_queue.find(query).sort("created_at", -1).limit(page_size).to_list(length=page_size)
            total = len(items)
            if len(items) == page_size:
                next_cursor = str(items[-1]["created_at"])
        else:
            total = await db.community_moderation_queue.count_documents(query)
            items = await db.community_moderation_queue.find(query).sort("created_at", -1).skip((page - 1) * page_size).limit(page_size).to_list(length=page_size)

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "next_cursor": next_cursor,
    }


async def paginate_audit(
    db,
    page_size: int = 20,
    cursor: Optional[str] = None,
) -> dict:
    """Paginate moderation audit log using cursor pagination on created_at.

    Returns dict with: items, next_cursor.
    """
    query = {}
    next_cursor = None
    items = []

    if cursor:
        try:
            cursor_ts = float(cursor)
        except (ValueError, TypeError):
            from fastapi import HTTPException
            raise HTTPException(status_code=400, detail="Invalid cursor — must be a Unix timestamp")
        query["created_at"] = {"$lt": cursor_ts}

    items = await db.community_moderation_audit.find(query).sort("created_at", -1).limit(page_size).to_list(length=page_size)

    if len(items) == page_size:
        next_cursor = str(items[-1]["created_at"])

    return {
        "items": items,
        "next_cursor": next_cursor,
    }
