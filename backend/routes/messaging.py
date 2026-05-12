"""Messaging Routes: User ↔ Admin conversation system."""
from fastapi import APIRouter, HTTPException, Depends, Body
import uuid
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field

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


class ContactAdminRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)
    subject: Optional[str] = None


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


async def _enrich_conversation(conv: dict, my_id: str) -> dict:
    """Return conversation dict with participants_info and resolved unread_count for the caller."""
    d = {k: v for k, v in conv.items() if k != "_id"}
    participants_info: dict = {}
    for pid in d.get("participants", []):
        u = await db.users.find_one(
            {"id": pid},
            {"_id": 0, "id": 1, "name": 1, "email": 1, "is_admin": 1},
        )
        if u:
            participants_info[pid] = u
    d["participants_info"] = participants_info
    raw_unread = d.get("unread_count", {})
    if isinstance(raw_unread, dict):
        d["unread_count"] = raw_unread.get(my_id, 0)
    return d


async def _notify_participants(conversation: dict, exclude_user_id: str, preview: str, sender_name: str):
    for pid in conversation.get("participants", []):
        if pid == exclude_user_id:
            continue
        try:
            await db.notifications.insert_one({
                "id": uuid.uuid4().hex,
                "user_id": pid,
                "type": "new_message",
                "title": f"Neue Nachricht von {sender_name}",
                "message": preview[:200],
                "icon": "message-square",
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
    convs = await db.conversations.find(query).sort("last_message_at", -1).limit(100).to_list(100)
    enriched = [await _enrich_conversation(c, user["id"]) for c in convs]
    return {"conversations": enriched, "total": len(enriched)}


@router.get("/messaging/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    user: dict = Depends(get_current_user),
):
    conversation = await _get_conversation_or_404(conversation_id, user["id"])
    messages = await db.messages.find(
        {"conversation_id": conversation_id}
    ).sort("created_at", 1).to_list(length=500)
    for m in messages:
        m.pop("_id", None)
    enriched = await _enrich_conversation(conversation, user["id"])
    return {"conversation": enriched, "messages": messages}


@router.post("/messaging/contact-admin")
async def contact_admin(body: ContactAdminRequest, user: dict = Depends(get_current_user)):
    """Start or continue a conversation with the default admin."""
    admin = await db.users.find_one({"is_admin": True}, {"id": 1, "_id": 0})
    if not admin:
        raise HTTPException(status_code=503, detail="Kein Administrator verfügbar")

    admin_id = admin["id"]
    if admin_id == user["id"]:
        raise HTTPException(status_code=400, detail="Sie sind der Administrator")

    content_err = validate_message_content(body.content)
    if content_err:
        raise HTTPException(status_code=400, detail=content_err)
    rate_err = check_rate_limit(user["id"])
    if rate_err:
        raise HTTPException(status_code=429, detail=rate_err)
    spam_err = check_spam_rate(user["id"])
    if spam_err:
        raise HTTPException(status_code=429, detail=spam_err)
    dup_err = check_duplicate_content(user["id"], body.content)
    if dup_err:
        raise HTTPException(status_code=429, detail=dup_err)

    sanitized = sanitize_message_content(body.content)
    sender_name = await _get_user_name(user["id"])
    now = datetime.now(timezone.utc).isoformat()
    participants = sorted([user["id"], admin_id])

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
            "unread_count": {user["id"]: 0, admin_id: 1},
            "status": "active",
            "escalation_level": 0,
            "tags": [],
            "created_at": now,
            "updated_at": now,
        }
        await db.conversations.insert_one(conversation)

    message = {
        "id": uuid.uuid4().hex,
        "conversation_id": conv_id,
        "sender_id": user["id"],
        "sender_role": "user",
        "content": sanitized,
        "attachments": [],
        "read_by": [user["id"]],
        "is_system_message": False,
        "created_at": now,
    }
    await db.messages.insert_one(message)

    unread = conversation.get("unread_count", {})
    if isinstance(unread, dict):
        unread[admin_id] = unread.get(admin_id, 0) + 1
    else:
        unread = {user["id"]: 0, admin_id: 1}

    await db.conversations.update_one(
        {"id": conv_id},
        {"$set": {
            "last_message_at": now,
            "last_message_preview": sanitized[:100],
            "last_message_sender_id": user["id"],
            "unread_count": unread,
            "updated_at": now,
        }},
    )

    import asyncio
    asyncio.create_task(_notify_participants(conversation, user["id"], sanitized[:200], sender_name))
    logger.info(f"[Messaging] contact-admin from {user['id'][:8]} conv={conv_id[:8]}")
    return {"conversation_id": conv_id, "message_id": message["id"]}


@router.post("/messaging/send")
async def send_message(body: MessageSend, user: dict = Depends(get_current_user)):
    content_err = validate_message_content(body.content, has_attachments=len(body.attachments) > 0)
    if content_err:
        raise HTTPException(status_code=400, detail=content_err)
    rate_err = check_rate_limit(user["id"])
    if rate_err:
        raise HTTPException(status_code=429, detail=rate_err)
    spam_err = check_spam_rate(user["id"])
    if spam_err:
        raise HTTPException(status_code=429, detail=spam_err)
    dup_err = check_duplicate_content(user["id"], body.content)
    if dup_err:
        raise HTTPException(status_code=429, detail=dup_err)

    att_dicts = [a.model_dump() for a in body.attachments]
    att_errs = validate_attachments(att_dicts)
    if att_errs:
        raise HTTPException(status_code=400, detail="; ".join(att_errs))

    sanitized = sanitize_message_content(body.content)
    sender_name = await _get_user_name(user["id"])
    now = datetime.now(timezone.utc).isoformat()

    recipient = await db.users.find_one({"id": body.recipient_id})
    if not recipient:
        raise HTTPException(status_code=404, detail="Recipient not found")

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

    sender_role = "admin" if user.get("is_admin") else "user"
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

    unread = conversation.get("unread_count", {})
    if not isinstance(unread, dict):
        unread = {}
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
        }},
    )

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

    import asyncio
    asyncio.create_task(_notify_participants(conversation, user["id"], sanitized[:200], sender_name))
    return {"message_id": message["id"], "conversation_id": conv_id, "created_at": now}


@router.post("/messaging/conversations/{conversation_id}/read")
async def mark_conversation_read(
    conversation_id: str,
    user: dict = Depends(get_current_user),
):
    conversation = await _get_conversation_or_404(conversation_id, user["id"])
    await db.messages.update_many(
        {"conversation_id": conversation_id, "read_by": {"$ne": user["id"]}},
        {"$push": {"read_by": user["id"]}},
    )
    unread = conversation.get("unread_count", {})
    if isinstance(unread, dict):
        unread[user["id"]] = 0
    else:
        unread = {user["id"]: 0}
    await db.conversations.update_one(
        {"id": conversation_id},
        {"$set": {"unread_count": unread, "updated_at": datetime.now(timezone.utc).isoformat()}},
    )
    return {"status": "ok"}


@router.get("/messaging/unread-count")
async def get_unread_count(user: dict = Depends(get_current_user)):
    convs = await db.conversations.find(
        {"participants": user["id"], "status": "active"},
        {"unread_count": 1},
    ).to_list(200)
    total = 0
    for c in convs:
        uc = c.get("unread_count", {})
        if isinstance(uc, dict):
            total += uc.get(user["id"], 0)
        elif isinstance(uc, int):
            total += uc
    return {"total_unread": total}


# ── Admin-only endpoints ──


@router.get("/messaging/admin/users")
async def admin_search_users(
    q: Optional[str] = None,
    admin: dict = Depends(get_admin_user),
):
    """Search users to start a new conversation with."""
    import re as _re
    query: dict = {}
    if q and len(q) >= 1:
        pattern = _re.compile(_re.escape(q), _re.IGNORECASE)
        query = {"$or": [{"name": pattern}, {"email": pattern}]}
    users = await db.users.find(
        query, {"_id": 0, "id": 1, "name": 1, "email": 1, "is_admin": 1}
    ).sort("created_at", -1).limit(20).to_list(20)
    return {"users": users}


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

    convs = await db.conversations.find(query).sort("last_message_at", -1).limit(100).to_list(100)
    results = []
    for c in convs:
        enriched = await _enrich_conversation(c, admin["id"])
        enriched["message_count"] = await db.messages.count_documents({"conversation_id": c["id"]})
        results.append(enriched)
    return {"conversations": results, "total": len(results)}


@router.get("/messaging/admin/audit-log")
async def get_audit_log(
    limit: int = 50,
    admin: dict = Depends(get_admin_user),
):
    logs = await db.audit_logs.find().sort("created_at", -1).limit(min(limit, 200)).to_list(min(limit, 200))
    for l in logs:
        l.pop("_id", None)
    return {"logs": logs, "total": len(logs)}
