import uuid
from datetime import datetime, timezone
from typing import Optional
import asyncio


FEATURE_PACKS = {"advanced_features"}
"""Known feature pack identifiers."""

FEATURE_PACK_LABELS = {
    "advanced_features": "Erweiterte Funktionen (Analyzer, Notebook, Podcast)",
}
"""Display labels for feature packs."""


async def create_access_request(user_id: str, feature_pack: str) -> dict:
    from database import db, logger

    # Resolve requesting user info
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "name": 1, "email": 1})
    user = user or {}

    existing = await db.access_requests.find_one(
        {"user_id": user_id, "feature_pack": feature_pack, "status": "pending"}
    )
    if existing:
        logger.info("access_request=duplicate_blocked user_id=%s feature_pack=%s", user_id[:8], feature_pack)
        raise _dup_error()

    label = FEATURE_PACK_LABELS.get(feature_pack, feature_pack)
    doc = {
        "id": uuid.uuid4().hex,
        "user_id": user_id,
        "user_name": user.get("name", ""),
        "user_email": user.get("email", ""),
        "feature_pack": feature_pack,
        "feature_label": label,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "reviewed_at": None,
        "reviewed_by": None,
    }
    await db.access_requests.insert_one(doc)
    logger.info("access_request=created user_id=%s feature_pack=%s request_id=%s", user_id[:8], feature_pack, doc["id"])

    # Notify all admins
    try:
        admins = await db.users.find({"is_admin": True}, {"_id": 0, "id": 1, "email": 1, "name": 1}).to_list(20)
        now_iso = datetime.now(timezone.utc).isoformat()
        for admin in admins:
            await db.notifications.insert_one({
                "id": uuid.uuid4().hex,
                "user_id": admin["id"],
                "type": "access_request",
                "title": "Neue Zugriffsanfrage",
                "message": f"{user.get('name', 'Ein Benutzer')} bittet um Zugang zu {label}",
                "icon": "lock",
                "read": False,
                "request_id": doc["id"],
                "created_at": now_iso,
            })
            if admin.get("email"):
                try:
                    from services.email_service import send_admin_new_request_email
                    asyncio.ensure_future(send_admin_new_request_email(admin["email"], user, label))
                except Exception:
                    pass
    except Exception:
        logger.exception("access_request=notification_failed")

    return doc


async def list_access_requests(status: Optional[str] = None) -> list[dict]:
    from database import db
    query = {}
    if status:
        query["status"] = status
    cursor = db.access_requests.find(query, {"_id": 0}).sort("created_at", -1)
    return await cursor.to_list(length=500)


async def resolve_access_request(
    request_id: str, status: str, admin_id: str
) -> Optional[dict]:
    from database import db, logger
    if status not in ("approved", "rejected"):
        raise ValueError(f"Invalid status '{status}' — must be approved or rejected")

    doc = await db.access_requests.find_one({"id": request_id})
    if not doc:
        return None

    now = datetime.now(timezone.utc).isoformat()
    await db.access_requests.update_one(
        {"id": request_id},
        {"$set": {"status": status, "reviewed_at": now, "reviewed_by": admin_id}},
    )

    user_id = doc["user_id"]
    label = FEATURE_PACK_LABELS.get(doc.get("feature_pack", ""), doc.get("feature_pack", "Unbekanntes Feature"))
    now_iso = datetime.now(timezone.utc).isoformat()

    if status == "approved":
        await db.users.update_one(
            {"id": user_id},
            {"$set": {
                "notebook_enabled": True,
                "analyzer_enabled": True,
                "podcast_enabled": True,
            }},
        )
        logger.info(
            "access_request=approved request_id=%s user_id=%s admin_id=%s feature_pack=%s",
            request_id, user_id[:8], admin_id[:8], doc.get("feature_pack"),
        )
        # Notify user
        try:
            await db.notifications.insert_one({
                "id": uuid.uuid4().hex,
                "user_id": user_id,
                "type": "access_granted",
                "title": "Zugang freigeschaltet!",
                "message": f"Ihr Zugang zu {label} wurde genehmigt. Sie können alle Funktionen jetzt nutzen.",
                "icon": "unlock",
                "read": False,
                "created_at": now_iso,
            })
            req_user = await db.users.find_one({"id": user_id}, {"_id": 0, "email": 1, "name": 1})
            if req_user and req_user.get("email"):
                try:
                    from services.email_service import send_access_granted_email
                    asyncio.ensure_future(send_access_granted_email(req_user, label))
                except Exception:
                    pass
        except Exception:
            logger.exception("access_request=approve_notification_failed")
    else:
        logger.info(
            "access_request=rejected request_id=%s user_id=%s admin_id=%s feature_pack=%s",
            request_id, user_id[:8], admin_id[:8], doc.get("feature_pack"),
        )
        # Notify user
        try:
            await db.notifications.insert_one({
                "id": uuid.uuid4().hex,
                "user_id": user_id,
                "type": "access_rejected",
                "title": "Zugriffsanfrage abgelehnt",
                "message": f"Ihr Antrag für {label} wurde abgelehnt.",
                "icon": "x-circle",
                "read": False,
                "created_at": now_iso,
            })
            req_user = await db.users.find_one({"id": user_id}, {"_id": 0, "email": 1, "name": 1})
            if req_user and req_user.get("email"):
                try:
                    from services.email_service import send_access_rejected_email
                    asyncio.ensure_future(send_access_rejected_email(req_user, label))
                except Exception:
                    pass
        except Exception:
            logger.exception("access_request=reject_notification_failed")

    doc["status"] = status
    doc["reviewed_at"] = now
    doc["reviewed_by"] = admin_id
    return doc


def _dup_error():
    from fastapi import HTTPException
    return HTTPException(status_code=409, detail="Es besteht bereits eine ausstehende Anfrage für dieses Feature-Pack.")
