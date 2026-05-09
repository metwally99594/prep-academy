"""Messaging Routes: User ↔ Admin conversation system."""
from fastapi import APIRouter, HTTPException, Depends, Request
import uuid
from datetime import datetime, timezone
from typing import Optional

from database import db, logger
from models import (
    MessageSend, ConversationResponse, ConversationListResponse,
    EscalationUpdate, ConversationTagsUpdate,
)
from auth import get_current_user, get_admin_user
from services.messaging_service import (
    validate_message_content,
    validate_attachments,
    sanitize_message_content,
    check_rate_limit,
    check_spam_rate,
    check_duplicate_content,
    validate_escalation_level,
    contains_html,
)

router = APIRouter(prefix="/api", tags=["messaging"])


async def _get_user_name(user_id: str) -> str:
    user = await db.users.find_one({"id": user_id}, {"name": 1})
    return user.get("name", "Unknown") if user else "Unknown"


async def _get_conversation_or_404(conversation_id: str, user_id: str, require_admin: bool = False) -> dict:
    conversation = await db.conversations.find_one({"id": conversation_id})
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if require_admin:
        return conversation
    if user_id not in conversation.get("participants", []):
        raise HTTPException(status_code=403, detail="Not a participant of this conversation")
    return conversation


async def _notify_participants(conversation: dict, exclude_user_id: str, preview: str, sender_name: str):
    for pid in conversation.get("participants", []):
        if pid == exclude_user_id:
            continue
        try:
            await db.notifications.insert_one({
                "id": uuid.uuid4().hex,
                "user_id": pid,
                "type": "new_message",
                "title": f"New message from {sender_name}",
                "message": preview[:200],
                "icon": "message-circle",
                "read": False,
                "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "data": {"conversation_id": conversation["id"]},
            })
        except Exception as e:
            logger.warning(f"Failed to notify user {pid}: {e}")


@router.get("/messaging/conversations")
async def list_conversations(
    status: Optional[str] = None,
    user: dict = Depends(get_current_user),
):
    query: dict = {"participants": user["id"]}
    if status:
        query["status"] = status
    cursor = db.conversations.find(query).sort("last_message_at", -1).limit(100)
    conversations = await cursor.to_list(length=100)
    return ConversationListResponse(
        conversations=[
            ConversationResponse(
                id=c["id"],
                participants=c.get("participants", []),
                subject=c.get("subject"),
                last_message_at=c.get("last_message_at"),
                last_message_preview=c.get("last_message_preview"),
                last_message_sender_id=c.get("last_message_sender_id"),
                unread_count=c.get("unread_count", {}).get(user["id"], 0),
                status=c.get("status", "active"),
                escalation_level=c.get("escalation_level", 0),
                tags=c.get("tags", []),
                created_at=c.get("created_at", ""),
                updated_at=c.get("updated_at", ""),
            )
            for c in conversations
        ],
        total=len(conversations),
    )


@router.get("/messaging/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    user: dict = Depends(get_current_user),
):
    conversation = await _get_conversation_or_404(conversation_id, user["id"])
    messages = await db.messages.find(
        {"conversation_id": conversation_id}
    ).sort("created_at", 1).to_list(length=500)

    return {
        "conversation": ConversationResponse(
            id=conversation["id"],
            participants=conversation.get("participants", []),
            subject=conversation.get("subject"),
            last_message_at=conversation.get("last_message_at"),
            last_message_preview=conversation.get("last_message_preview"),
            last_message_sender_id=conversation.get("last_message_sender_id"),
            unread_count=conversation.get("unread_count", {}).get(user["id"], 0),
            status=conversation.get("status", "active"),
            escalation_level=conversation.get("escalation_level", 0),
            tags=conversation.get("tags", []),
            created_at=conversation.get("created_at", ""),
            updated_at=conversation.get("updated_at", ""),
        ),
        "messages": messages,
    }


@router.post("/messaging/send")
async def send_message(body: MessageSend, user: dict = Depends(get_current_user)):
    # Validate content
    content_err = validate_message_content(body.content)
    if content_err:
        raise HTTPException(status_code=400, detail=content_err)

    # Rate limit
    rate_err = check_rate_limit(user["id"])
    if rate_err:
        raise HTTPException(status_code=429, detail=rate_err)

    spam_err = check_spam_rate(user["id"])
    if spam_err:
        raise HTTPException(status_code=429, detail=spam_err)

    dup_err = check_duplicate_content(user["id"], body.content)
    if dup_err:
        raise HTTPException(status_code=429, detail=dup_err)

    # Validate attachments
    att_dicts = [a.model_dump() for a in body.attachments]
    att_errs = validate_attachments(att_dicts)
    if att_errs:
        raise HTTPException(status_code=400, detail="; ".join(att_errs))

    sanitized = sanitize_message_content(body.content)
    sender_name = await _get_user_name(user["id"])
    now = datetime.now(timezone.utc).isoformat()
    now_ts = datetime.now(timezone.utc).timestamp()

    # Resolve recipient
    recipient = await db.users.find_one({"id": body.recipient_id})
    if not recipient:
        raise HTTPException(status_code=404, detail="Recipient not found")

    # Find or create conversation
    conv_id = body.conversation_id
    if conv_id:
        conversation = await _get_conversation_or_404(conv_id, user["id"])
    else:
        participants = sorted([user["id"], body.recipient_id])
        existing = await db.conversations.find_one({
            "participants": participants,
            "status": {"$ne": "closed"},
        })
        if existing:
            conv_id = existing["id"]
            conversation = existing
        else:
            conv_id = uuid.uuid4().hex
            conversation = {
                "id": conv_id,
                "participants": participants,
                "subject": body.subject,
                "last_message_at": now,
                "last_message_preview": sanitized[:100],
                "last_message_sender_id": user["id"],
                "unread_count": {user["id"]: 0, body.recipient_id: 1},
                "status": "active",
                "escalation_level": 0,
                "tags": [],
                "created_at": now,
                "updated_at": now,
            }
            await db.conversations.insert_one(conversation)

    # Determine sender role
    sender_role = "admin" if user.get("is_admin") else "user"

    # Create message
    message = {
        "id": uuid.uuid4().hex,
        "conversation_id": conv_id,
        "sender_id": user["id"],
        "sender_role": sender_role,
        "content": sanitized,
        "attachments": att_dicts,
        "read_by": [user["id"]],
        "is_system_message": False,
        "created_at": now,
    }
    await db.messages.insert_one(message)

    # Update conversation
    unread = conversation.get("unread_count", {})
    for pid in conversation.get("participants", []):
        if pid != user["id"]:
            unread[pid] = unread.get(pid, 0) + 1
    await db.conversations.update_one(
        {"id": conv_id},
        {"$set": {
            "last_message_at": now,
            "last_message_preview": sanitized[:100],
            "last_message_sender_id": user["id"],
            "unread_count": unread,
            "updated_at": now,
        }}
    )

    # Audit log
    try:
        await db.audit_logs.insert_one({
            "id": uuid.uuid4().hex,
            "action": "message_sent",
            "actor_id": user["id"],
            "actor_role": sender_role,
            "target_type": "conversation",
            "target_id": conv_id,
            "details": {"message_id": message["id"], "has_attachments": len(att_dicts) > 0},
            "created_at": now,
        })
    except Exception as e:
        logger.warning(f"Audit log failed: {e}")

    # Notify recipient asynchronously
    import asyncio
    asyncio.create_task(_notify_participants(
        conversation, user["id"], sanitized[:200], sender_name
    ))

    return {
        "message_id": message["id"],
        "conversation_id": conv_id,
        "created_at": now,
    }


@router.post("/messaging/conversations/{conversation_id}/read")
async def mark_conversation_read(
    conversation_id: str,
    user: dict = Depends(get_current_user),
):
    conversation = await _get_conversation_or_404(conversation_id, user["id"])

    # Mark all unread messages as read by this user
    await db.messages.update_many(
        {"conversation_id": conversation_id, "read_by": {"$ne": user["id"]}},
        {"$push": {"read_by": user["id"]}},
    )

    # Reset unread count
    unread = conversation.get("unread_count", {})
    unread[user["id"]] = 0
    await db.conversations.update_one(
        {"id": conversation_id},
        {"$set": {"unread_count": unread, "updated_at": datetime.now(timezone.utc).isoformat()}},
    )

    return {"status": "ok"}


@router.get("/messaging/unread-count")
async def get_unread_count(user: dict = Depends(get_current_user)):
    pipeline = [
        {"$match": {"participants": user["id"], "status": "active"}},
        {"$project": {
            "unread": {"$ifNull": [{"$getField": {"field": user["id"], "input": "$unread_count"}}, 0]}
        }},
        {"$group": {"_id": None, "total": {"$sum": "$unread"}}},
    ]
    cursor = db.conversations.aggregate(pipeline)
    result = await cursor.to_list(length=1)
    total = result[0]["total"] if result else 0
    return {"total_unread": total}


# ── Admin-only endpoints ──


@router.put("/messaging/conversations/{conversation_id}/escalation")
async def update_escalation(
    conversation_id: str,
    body: EscalationUpdate,
    admin: dict = Depends(get_admin_user),
):
    conversation = await _get_conversation_or_404(conversation_id, admin["id"])
    err = validate_escalation_level(body.escalation_level)
    if err:
        raise HTTPException(status_code=400, detail=err)

    old_level = conversation.get("escalation_level", 0)
    now = datetime.now(timezone.utc).isoformat()

    await db.conversations.update_one(
        {"id": conversation_id},
        {"$set": {"escalation_level": body.escalation_level, "updated_at": now}},
    )

    # System message on escalation change
    if body.escalation_level != old_level and body.reason:
        levels = ["none", "attention", "urgent", "critical"]
        await db.messages.insert_one({
            "id": uuid.uuid4().hex,
            "conversation_id": conversation_id,
            "sender_id": admin["id"],
            "sender_role": "admin",
            "content": f"Escalation changed: {levels[old_level]} → {levels[body.escalation_level]}. Reason: {body.reason}",
            "attachments": [],
            "read_by": [admin["id"]],
            "is_system_message": True,
            "created_at": now,
        })

    # Audit
    try:
        await db.audit_logs.insert_one({
            "id": uuid.uuid4().hex,
            "action": "escalation_changed",
            "actor_id": admin["id"],
            "actor_role": "admin",
            "target_type": "conversation",
            "target_id": conversation_id,
            "details": {"from": old_level, "to": body.escalation_level, "reason": body.reason},
            "created_at": now,
        })
    except Exception as e:
        logger.warning(f"Audit log failed: {e}")

    return {"status": "ok", "escalation_level": body.escalation_level}


@router.put("/messaging/conversations/{conversation_id}/tags")
async def update_conversation_tags(
    conversation_id: str,
    body: ConversationTagsUpdate,
    admin: dict = Depends(get_admin_user),
):
    conversation = await _get_conversation_or_404(conversation_id, admin["id"])
    now = datetime.now(timezone.utc).isoformat()

    old_tags = conversation.get("tags", [])
    await db.conversations.update_one(
        {"id": conversation_id},
        {"$set": {"tags": body.tags, "updated_at": now}},
    )

    # Audit
    try:
        await db.audit_logs.insert_one({
            "id": uuid.uuid4().hex,
            "action": "tags_updated",
            "actor_id": admin["id"],
            "actor_role": "admin",
            "target_type": "conversation",
            "target_id": conversation_id,
            "details": {"from": old_tags, "to": body.tags},
            "created_at": now,
        })
    except Exception as e:
        logger.warning(f"Audit log failed: {e}")

    return {"status": "ok", "tags": body.tags}


@router.post("/messaging/conversations/{conversation_id}/close")
async def close_conversation(
    conversation_id: str,
    admin: dict = Depends(get_admin_user),
):
    await _get_conversation_or_404(conversation_id, admin["id"])
    now = datetime.now(timezone.utc).isoformat()

    await db.conversations.update_one(
        {"id": conversation_id},
        {"$set": {"status": "closed", "updated_at": now}},
    )

    # Audit
    try:
        await db.audit_logs.insert_one({
            "id": uuid.uuid4().hex,
            "action": "conversation_closed",
            "actor_id": admin["id"],
            "actor_role": "admin",
            "target_type": "conversation",
            "target_id": conversation_id,
            "details": {},
            "created_at": now,
        })
    except Exception as e:
        logger.warning(f"Audit log failed: {e}")

    return {"status": "ok"}


@router.get("/messaging/admin/inbox")
async def admin_inbox(
    status: Optional[str] = None,
    escalation_min: Optional[int] = None,
    tag: Optional[str] = None,
    admin: dict = Depends(get_admin_user),
):
    query: dict = {}
    if status:
        query["status"] = status
    if escalation_min is not None:
        query["escalation_level"] = {"$gte": escalation_min}
    if tag:
        query["tags"] = tag

    cursor = db.conversations.find(query).sort("last_message_at", -1).limit(100)
    conversations = await cursor.to_list(length=100)

    results = []
    for c in conversations:
        messages_count = await db.messages.count_documents({"conversation_id": c["id"]})
        results.append({
            "id": c["id"],
            "participants": c.get("participants", []),
            "subject": c.get("subject"),
            "last_message_at": c.get("last_message_at"),
            "last_message_preview": c.get("last_message_preview"),
            "status": c.get("status", "active"),
            "escalation_level": c.get("escalation_level", 0),
            "tags": c.get("tags", []),
            "message_count": messages_count,
            "created_at": c.get("created_at", ""),
            "updated_at": c.get("updated_at", ""),
        })

    return {"conversations": results, "total": len(results)}


@router.get("/messaging/admin/audit-log")
async def get_audit_log(
    limit: int = 50,
    admin: dict = Depends(get_admin_user),
):
    cursor = db.audit_logs.find().sort("created_at", -1).limit(min(limit, 200))
    logs = await cursor.to_list(length=min(limit, 200))
    return {"logs": logs, "total": len(logs)}
