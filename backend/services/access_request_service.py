import uuid
from datetime import datetime, timezone
from typing import Optional


FEATURE_PACKS = {"advanced_features"}
"""Known feature pack identifiers."""


async def create_access_request(user_id: str, feature_pack: str) -> dict:
    from database import db, logger
    existing = await db.access_requests.find_one(
        {"user_id": user_id, "feature_pack": feature_pack, "status": "pending"}
    )
    if existing:
        logger.info("access_request=duplicate_blocked user_id=%s feature_pack=%s", user_id[:8], feature_pack)
        raise _dup_error()

    doc = {
        "id": uuid.uuid4().hex,
        "user_id": user_id,
        "feature_pack": feature_pack,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "reviewed_at": None,
        "reviewed_by": None,
    }
    await db.access_requests.insert_one(doc)
    logger.info("access_request=created user_id=%s feature_pack=%s request_id=%s", user_id[:8], feature_pack, doc["id"])
    return doc


async def list_access_requests() -> list[dict]:
    from database import db
    cursor = db.access_requests.find({}, {"_id": 0}).sort("created_at", -1)
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

    if status == "approved":
        user_id = doc["user_id"]
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
    else:
        logger.info(
            "access_request=rejected request_id=%s user_id=%s admin_id=%s feature_pack=%s",
            request_id, doc["user_id"][:8], admin_id[:8], doc.get("feature_pack"),
        )

    doc["status"] = status
    doc["reviewed_at"] = now
    doc["reviewed_by"] = admin_id
    return doc


def _dup_error():
    from fastapi import HTTPException
    return HTTPException(status_code=409, detail="Es besteht bereits eine ausstehende Anfrage für dieses Feature-Pack.")
