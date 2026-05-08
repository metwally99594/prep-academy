"""Trial system — 30-day auto-trial for new users."""
from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone, timedelta
import uuid
import asyncio
import logging

logger = logging.getLogger(__name__)

TRIAL_DAYS = 30
_FEATURES = ["notebook_enabled", "analyzer_enabled", "podcast_enabled"]


# ── Cron helpers ───────────────────────────────────────────────────

async def _check_expired_trials(db) -> None:
    from services.email_service import send_trial_expired_email
    now_iso = datetime.now(timezone.utc).isoformat()
    async for user in db.users.find({
        "trial_ends_at": {"$lte": now_iso},
        "is_permanent": {"$ne": True},
        "is_admin": {"$ne": True},
        "trial_expired_notified": {"$ne": True},
    }, {"_id": 0}):
        await db.users.update_one(
            {"id": user["id"]},
            {"$set": {**{f: False for f in _FEATURES}, "trial_expired_notified": True}},
        )
        await db.notifications.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": user["id"],
            "type": "trial_expired",
            "title": "Probezeit abgelaufen",
            "message": "Ihre 30-tägige Probezeit ist abgelaufen. Kontaktieren Sie den Administrator für eine Verlängerung.",
            "icon": "clock",
            "read": False,
            "created_at": now_iso,
        })
        asyncio.ensure_future(send_trial_expired_email(user))
        logger.info("[Trial] Expired: %s", user.get("email"))


async def _send_trial_warnings(db) -> None:
    from services.email_service import send_trial_5days_warning_email, send_trial_2days_warning_email
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    five_iso = (now + timedelta(days=5)).isoformat()
    two_iso  = (now + timedelta(days=2)).isoformat()

    # 5-day warning
    async for user in db.users.find({
        "trial_ends_at": {"$lte": five_iso, "$gt": two_iso},
        "is_permanent": {"$ne": True}, "is_admin": {"$ne": True},
        "trial_5day_warned": {"$ne": True},
    }, {"_id": 0}):
        te = user.get("trial_ends_at", "")
        days = max(0, (datetime.fromisoformat(te.replace("Z", "+00:00")) - now).days) if te else 0
        await db.users.update_one({"id": user["id"]}, {"$set": {"trial_5day_warned": True}})
        await db.notifications.insert_one({
            "id": str(uuid.uuid4()), "user_id": user["id"],
            "type": "trial_warning", "title": f"Probezeit endet in {days} Tagen",
            "message": f"Ihre Probezeit läuft in {days} Tagen ab. Jetzt Verlängerung anfragen.",
            "icon": "clock", "read": False, "created_at": now_iso,
        })
        asyncio.ensure_future(send_trial_5days_warning_email(user, days))

    # 2-day warning
    async for user in db.users.find({
        "trial_ends_at": {"$lte": two_iso, "$gt": now_iso},
        "is_permanent": {"$ne": True}, "is_admin": {"$ne": True},
        "trial_2day_warned": {"$ne": True},
    }, {"_id": 0}):
        te = user.get("trial_ends_at", "")
        days = max(0, (datetime.fromisoformat(te.replace("Z", "+00:00")) - now).days) if te else 0
        await db.users.update_one({"id": user["id"]}, {"$set": {"trial_2day_warned": True}})
        await db.notifications.insert_one({
            "id": str(uuid.uuid4()), "user_id": user["id"],
            "type": "trial_warning_urgent",
            "title": f"⚠️ Probezeit endet in {days} Tagen!",
            "message": "Letzte Chance: Kontaktieren Sie den Administrator für eine Verlängerung.",
            "icon": "clock", "read": False, "created_at": now_iso,
        })
        asyncio.ensure_future(send_trial_2days_warning_email(user, days))


async def trial_loop(db) -> None:
    """Run trial checks every hour."""
    while True:
        await asyncio.sleep(3600)
        try:
            await _check_expired_trials(db)
            await _send_trial_warnings(db)
        except Exception as exc:
            logger.error("[Trial cron] %s", exc)


async def migrate_existing_users(db) -> None:
    """One-time migration: give existing users without trial fields a trial."""
    count = 0
    now = datetime.now(timezone.utc)
    async for user in db.users.find(
        {"trial_started_at": {"$exists": False}}, {"_id": 0, "id": 1, "is_admin": 1}
    ):
        if user.get("is_admin"):
            await db.users.update_one(
                {"id": user["id"]},
                {"$set": {"is_permanent": True, "trial_extensions_count": 0}},
            )
        else:
            ends = (now + timedelta(days=TRIAL_DAYS)).isoformat()
            await db.users.update_one(
                {"id": user["id"]},
                {"$set": {
                    "trial_started_at": now.isoformat(),
                    "trial_ends_at": ends,
                    "is_permanent": False,
                    "trial_extensions_count": 0,
                    "notebook_enabled": True,
                    "analyzer_enabled": True,
                    "podcast_enabled": True,
                }},
            )
        count += 1
    if count:
        logger.info("[Trial] Migrated %d existing users", count)


# ── Router factory ─────────────────────────────────────────────────

def make_trial_router(db, get_current_user, get_admin_user):
    router = APIRouter(prefix="/api", tags=["trial"])

    @router.post("/trial/request-extension")
    async def request_extension(body: dict, user: dict = Depends(get_current_user)):
        existing = await db.access_requests.find_one({
            "user_id": user["id"], "feature": "trial_extension", "status": "pending"
        })
        if existing:
            raise HTTPException(409, "Du hast bereits eine ausstehende Verlängerungsanfrage")
        now_iso = datetime.now(timezone.utc).isoformat()
        req = {
            "id": str(uuid.uuid4()),
            "user_id": user["id"],
            "user_name": user.get("name", ""),
            "user_email": user.get("email", ""),
            "feature": "trial_extension",
            "feature_label": "Probezeit-Verlängerung",
            "status": "pending",
            "user_message": (body.get("message") or "")[:500],
            "admin_note": "",
            "requested_at": now_iso,
            "responded_at": None,
        }
        await db.access_requests.insert_one(req)
        admins = await db.users.find({"is_admin": True}, {"_id": 0, "id": 1, "email": 1}).to_list(20)
        for admin in admins:
            await db.notifications.insert_one({
                "id": str(uuid.uuid4()),
                "user_id": admin["id"],
                "type": "trial_extension_request",
                "title": "Verlängerungsanfrage",
                "message": f"{user.get('name')} bittet um Verlängerung der Probezeit",
                "icon": "clock",
                "read": False,
                "request_id": req["id"],
                "created_at": now_iso,
            })
        return {"status": "pending", "request_id": req["id"]}

    @router.get("/trial/status")
    async def trial_status(user: dict = Depends(get_current_user)):
        now = datetime.now(timezone.utc)
        te = user.get("trial_ends_at")
        days_left = 0
        if te:
            try:
                delta = datetime.fromisoformat(te.replace("Z", "+00:00")) - now
                days_left = max(0, delta.days)
            except Exception:
                pass
        return {
            "is_permanent": user.get("is_permanent", False),
            "trial_started_at": user.get("trial_started_at"),
            "trial_ends_at": te,
            "days_left": days_left if not user.get("is_permanent") else -1,
            "is_trial_active": user.get("is_permanent", False) or (te is not None and days_left > 0),
            "trial_extensions_count": user.get("trial_extensions_count", 0),
        }

    @router.get("/admin/trials/overview")
    async def trials_overview(admin: dict = Depends(get_admin_user)):
        now_iso = datetime.now(timezone.utc).isoformat()
        week_iso = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
        base_q = {"is_admin": {"$ne": True}}
        active   = await db.users.count_documents({**base_q, "trial_ends_at": {"$gt": now_iso}, "is_permanent": {"$ne": True}})
        expiring = await db.users.count_documents({**base_q, "trial_ends_at": {"$gt": now_iso, "$lte": week_iso}, "is_permanent": {"$ne": True}})
        expired  = await db.users.count_documents({**base_q, "trial_ends_at": {"$lte": now_iso}, "is_permanent": {"$ne": True}})
        permanent= await db.users.count_documents({**base_q, "is_permanent": True})
        return {"active": active, "expiring_this_week": expiring, "expired": expired, "permanent": permanent}

    @router.get("/admin/trials/expiring-soon")
    async def expiring_soon(admin: dict = Depends(get_admin_user)):
        week_iso = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
        now_iso  = datetime.now(timezone.utc).isoformat()
        users = await db.users.find(
            {"is_admin": {"$ne": True}, "trial_ends_at": {"$gt": now_iso, "$lte": week_iso}, "is_permanent": {"$ne": True}},
            {"_id": 0, "id": 1, "name": 1, "email": 1, "trial_ends_at": 1},
        ).sort("trial_ends_at", 1).to_list(100)
        return users

    @router.post("/admin/users/{user_id}/trial/start")
    async def start_trial(user_id: str, admin: dict = Depends(get_admin_user)):
        from services.email_service import send_trial_started_email
        now = datetime.now(timezone.utc)
        ends = (now + timedelta(days=TRIAL_DAYS)).isoformat()
        user = await db.users.find_one({"id": user_id}, {"_id": 0})
        if not user:
            raise HTTPException(404, "Benutzer nicht gefunden")
        await db.users.update_one({"id": user_id}, {"$set": {
            "trial_started_at": now.isoformat(),
            "trial_ends_at": ends,
            "is_permanent": False,
            "notebook_enabled": True,
            "analyzer_enabled": True,
            "podcast_enabled": True,
            "trial_expired_notified": False,
        }})
        asyncio.ensure_future(send_trial_started_email(user, TRIAL_DAYS))
        return {"trial_ends_at": ends}

    @router.post("/admin/users/{user_id}/trial/extend")
    async def extend_trial(user_id: str, body: dict, admin: dict = Depends(get_admin_user)):
        from services.email_service import send_trial_extended_email
        days = min(int(body.get("days", 30)), 365)
        user = await db.users.find_one({"id": user_id}, {"_id": 0})
        if not user:
            raise HTTPException(404, "Benutzer nicht gefunden")
        now = datetime.now(timezone.utc)
        current_end = user.get("trial_ends_at")
        base = now
        if current_end:
            try:
                parsed = datetime.fromisoformat(current_end.replace("Z", "+00:00"))
                base = max(now, parsed)
            except Exception:
                pass
        new_end = (base + timedelta(days=days)).isoformat()
        await db.users.update_one({"id": user_id}, {"$set": {
            "trial_ends_at": new_end,
            "is_permanent": False,
            "notebook_enabled": True,
            "analyzer_enabled": True,
            "podcast_enabled": True,
            "trial_expired_notified": False,
        }, "$inc": {"trial_extensions_count": 1}})
        asyncio.ensure_future(send_trial_extended_email(user, days, new_end))
        return {"trial_ends_at": new_end, "extended_by_days": days}

    @router.post("/admin/users/{user_id}/make-permanent")
    async def make_permanent(user_id: str, admin: dict = Depends(get_admin_user)):
        from services.email_service import send_trial_made_permanent_email
        user = await db.users.find_one({"id": user_id}, {"_id": 0})
        if not user:
            raise HTTPException(404, "Benutzer nicht gefunden")
        await db.users.update_one({"id": user_id}, {"$set": {
            "is_permanent": True,
            "notebook_enabled": True,
            "analyzer_enabled": True,
            "podcast_enabled": True,
        }})
        asyncio.ensure_future(send_trial_made_permanent_email(user))
        return {"is_permanent": True}

    @router.post("/admin/users/{user_id}/revoke")
    async def revoke_access(user_id: str, admin: dict = Depends(get_admin_user)):
        user = await db.users.find_one({"id": user_id}, {"_id": 0})
        if not user:
            raise HTTPException(404, "Benutzer nicht gefunden")
        await db.users.update_one({"id": user_id}, {"$set": {
            "is_permanent": False,
            "notebook_enabled": False,
            "analyzer_enabled": False,
            "podcast_enabled": False,
            "trial_expired_notified": True,
        }})
        return {"revoked": True}

    return router
