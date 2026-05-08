"""Analytics & Access Requests routes"""
from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone, timedelta
from typing import Optional
import uuid
import asyncio

FEATURE_FIELD_MAP = {
    "notebook": "notebook_enabled",
    "analyzer": "analyzer_enabled",
    "podcast":  "podcast_enabled",
}
FEATURE_LABELS = {
    "notebook": "PDF Notebook",
    "analyzer": "Medical Analyzer",
    "podcast":  "Daily Podcast",
}


def _calc_score(stats, streak_data, active_days_30: int = 0) -> tuple:
    """Return (score 0-100, tier str) from existing collections."""
    if not stats:
        return 0.0, "new"
    total_q  = stats.get("total_questions", 0)
    correct  = stats.get("correct_answers",  0)
    accuracy = (correct / total_q * 100) if total_q > 0 else 0
    streak   = streak_data.get("current_streak", 0) if streak_data else 0
    xp       = stats.get("xp", 0)

    pts  = min(30, total_q  * 0.05)         # questions answered  → up to 30
    pts += min(30, accuracy * 0.30)         # accuracy            → up to 30
    pts += min(15, streak   * 3)            # streak days         → up to 15
    pts += min(20, active_days_30 * 0.70)  # consistency (30 d)  → up to 20
    pts += min(5,  xp / 400)               # XP bonus            → up to 5

    score = min(100.0, round(pts, 1))
    tier  = ("power"  if score >= 80
        else "active" if score >= 50
        else "casual" if score >= 20
        else "new")
    return score, tier


def make_analytics_router(db, get_current_user, get_admin_user):
    router = APIRouter(prefix="/api", tags=["analytics"])

    # ── Access Requests ───────────────────────────────────────────────

    @router.post("/access-requests")
    async def submit_request(body: dict, user: dict = Depends(get_current_user)):
        feature = (body.get("feature") or "").strip().lower()
        if feature not in FEATURE_FIELD_MAP:
            raise HTTPException(400, f"Ungültige Funktion. Erlaubt: {', '.join(FEATURE_FIELD_MAP)}")

        fresh = await db.users.find_one({"id": user["id"]}, {"_id": 0, FEATURE_FIELD_MAP[feature]: 1})
        if fresh and fresh.get(FEATURE_FIELD_MAP[feature]):
            raise HTTPException(400, "Zugang bereits freigeschaltet")

        existing = await db.access_requests.find_one(
            {"user_id": user["id"], "feature": feature, "status": "pending"}
        )
        if existing:
            raise HTTPException(409, "Du hast bereits eine ausstehende Anfrage für diese Funktion")

        now_iso = datetime.now(timezone.utc).isoformat()
        req = {
            "id":            str(uuid.uuid4()),
            "user_id":       user["id"],
            "user_name":     user.get("name", ""),
            "user_email":    user.get("email", ""),
            "feature":       feature,
            "feature_label": FEATURE_LABELS.get(feature, feature),
            "status":        "pending",
            "user_message":  (body.get("user_message") or "")[:500],
            "admin_note":    "",
            "requested_at":  now_iso,
            "responded_at":  None,
        }
        await db.access_requests.insert_one(req)

        admins = await db.users.find({"is_admin": True}, {"_id": 0, "id": 1, "email": 1, "name": 1}).to_list(20)
        for admin in admins:
            await db.notifications.insert_one({
                "id":         str(uuid.uuid4()),
                "user_id":    admin["id"],
                "type":       "access_request",
                "title":      "Neue Zugriffsanfrage",
                "message":    f"{user.get('name')} bittet um Zugang zu {FEATURE_LABELS.get(feature, feature)}",
                "icon":       "lock",
                "read":       False,
                "request_id": req["id"],
                "created_at": now_iso,
            })
            if admin.get("email"):
                try:
                    from services.email_service import send_admin_new_request_email
                    asyncio.ensure_future(send_admin_new_request_email(
                        admin["email"], user, FEATURE_LABELS.get(feature, feature)
                    ))
                except Exception:
                    pass

        return {"status": "pending", "request_id": req["id"]}

    @router.get("/access-requests/my")
    async def my_requests(user: dict = Depends(get_current_user)):
        return await db.access_requests.find(
            {"user_id": user["id"]}, {"_id": 0}
        ).sort("requested_at", -1).to_list(20)

    @router.get("/admin/access-requests")
    async def list_requests(status: Optional[str] = None, admin: dict = Depends(get_admin_user)):
        query = {} if not status else {"status": status}
        return await db.access_requests.find(query, {"_id": 0}).sort("requested_at", -1).to_list(500)

    @router.patch("/admin/access-requests/{req_id}")
    async def respond_request(req_id: str, body: dict, admin: dict = Depends(get_admin_user)):
        new_status = body.get("status")
        if new_status not in ("approved", "rejected"):
            raise HTTPException(400, "status muss 'approved' oder 'rejected' sein")

        req = await db.access_requests.find_one({"id": req_id}, {"_id": 0})
        if not req:
            raise HTTPException(404, "Anfrage nicht gefunden")
        if req["status"] != "pending":
            raise HTTPException(400, "Anfrage wurde bereits bearbeitet")

        admin_note = (body.get("admin_note") or "")[:500]
        now_iso    = datetime.now(timezone.utc).isoformat()

        await db.access_requests.update_one(
            {"id": req_id},
            {"$set": {"status": new_status, "admin_note": admin_note, "responded_at": now_iso}}
        )

        if new_status == "approved":
            field = FEATURE_FIELD_MAP.get(req["feature"])
            if field:
                await db.users.update_one({"id": req["user_id"]}, {"$set": {field: True}})

        feature_label = req.get("feature_label") or FEATURE_LABELS.get(req["feature"], req["feature"])
        if new_status == "approved":
            notif_extra = {
                "type":    "access_granted",
                "title":   f"{feature_label} freigeschaltet!",
                "message": f"Ihr Zugang zu {feature_label} wurde genehmigt. Sie können die Funktion jetzt nutzen.",
                "icon":    "unlock",
            }
        else:
            reason = f" Grund: {admin_note}" if admin_note else ""
            notif_extra = {
                "type":    "access_rejected",
                "title":   "Zugriffsanfrage abgelehnt",
                "message": f"Ihr Antrag für {feature_label} wurde abgelehnt.{reason}",
                "icon":    "x-circle",
            }

        await db.notifications.insert_one({
            "id":       str(uuid.uuid4()),
            "user_id":  req["user_id"],
            **notif_extra,
            "read":     False,
            "feature":  req["feature"],
            "created_at": now_iso,
        })

        # Send email to user
        try:
            req_user = await db.users.find_one({"id": req["user_id"]}, {"_id": 0, "email": 1, "name": 1})
            if req_user and req_user.get("email"):
                if new_status == "approved":
                    from services.email_service import send_access_granted_email
                    asyncio.ensure_future(send_access_granted_email(req_user, feature_label))
                else:
                    from services.email_service import send_access_rejected_email
                    asyncio.ensure_future(send_access_rejected_email(req_user, feature_label, admin_note))
        except Exception:
            pass

        return {"status": new_status, "request_id": req_id}

    # ── Analytics ─────────────────────────────────────────────────────

    @router.get("/admin/analytics/overview")
    async def overview(admin: dict = Depends(get_admin_user)):
        total       = await db.users.count_documents({"is_admin": False})
        seven_ago   = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        active_ids: set = set()
        async for a in db.user_activity.find(
            {"last_active": {"$gte": seven_ago}}, {"_id": 0, "user_id": 1}
        ):
            active_ids.add(a["user_id"])
        today_str  = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        new_today  = await db.users.count_documents({"created_at": {"$gte": today_str}, "is_admin": False})
        pending    = await db.access_requests.count_documents({"status": "pending"})
        total_q_db = await db.questions.count_documents({})
        return {
            "total_users":       total,
            "active_7d":         len(active_ids),
            "new_today":         new_today,
            "pending_requests":  pending,
            "total_questions_db": total_q_db,
        }

    @router.get("/admin/analytics/users")
    async def all_users_stats(admin: dict = Depends(get_admin_user)):
        users = await db.users.find(
            {"is_admin": False}, {"_id": 0, "password": 0}
        ).to_list(1000)
        thirty_ago = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")

        result = []
        for u in users:
            uid    = u["id"]
            stats  = await db.user_stats.find_one({"user_id": uid}, {"_id": 0})
            streak = await db.user_streaks.find_one({"user_id": uid}, {"_id": 0})
            active_days = await db.daily_activity.count_documents({
                "user_id": uid, "date": {"$gte": thirty_ago}, "questions": {"$gt": 0}
            })
            score, tier = _calc_score(stats, streak, active_days)
            act         = await db.user_activity.find_one({"user_id": uid}, {"_id": 0})
            last_active = (act or {}).get("last_active") or u.get("created_at", "")

            total_q = (stats or {}).get("total_questions", 0)
            correct = (stats or {}).get("correct_answers",  0)
            result.append({
                "id":               uid,
                "name":             u.get("name", ""),
                "email":            u.get("email", ""),
                "created_at":       u.get("created_at", ""),
                "notebook_enabled": u.get("notebook_enabled", False),
                "analyzer_enabled": u.get("analyzer_enabled", False),
                "podcast_enabled":  u.get("podcast_enabled",  False),
                "score":            score,
                "tier":             tier,
                "total_questions":  total_q,
                "correct_answers":  correct,
                "accuracy":         round(correct / total_q * 100, 1) if total_q > 0 else 0,
                "current_streak":   (streak or {}).get("current_streak", 0),
                "last_active":      last_active,
                "active_days_30":   active_days,
                "xp":               (stats or {}).get("xp", 0),
            })

        result.sort(key=lambda x: x["score"], reverse=True)
        return result

    @router.get("/admin/analytics/users/{user_id}/detail")
    async def user_detail(user_id: str, admin: dict = Depends(get_admin_user)):
        u = await db.users.find_one({"id": user_id}, {"_id": 0, "password": 0})
        if not u:
            raise HTTPException(404, "Benutzer nicht gefunden")

        stats  = await db.user_stats.find_one({"user_id": user_id}, {"_id": 0}) or {}
        streak = await db.user_streaks.find_one({"user_id": user_id}, {"_id": 0}) or {}

        ninety_ago = (datetime.now(timezone.utc) - timedelta(days=90)).strftime("%Y-%m-%d")
        daily = await db.daily_activity.find(
            {"user_id": user_id, "date": {"$gte": ninety_ago}},
            {"_id": 0}
        ).sort("date", 1).to_list(90)

        subjects = sorted(
            [
                {
                    "id":       sid,
                    "total":    d.get("total", 0),
                    "correct":  d.get("correct", 0),
                    "accuracy": round(d.get("correct", 0) / max(d.get("total", 1), 1) * 100, 1),
                }
                for sid, d in stats.get("by_specialty", {}).items()
                if d.get("total", 0) > 0
            ],
            key=lambda x: x["accuracy"]
        )

        thirty_ago  = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")
        active_days = await db.daily_activity.count_documents({
            "user_id": user_id, "date": {"$gte": thirty_ago}, "questions": {"$gt": 0}
        })
        score, tier = _calc_score(stats, streak, active_days)

        reqs = await db.access_requests.find(
            {"user_id": user_id}, {"_id": 0}
        ).sort("requested_at", -1).to_list(20)

        act_doc     = await db.user_activity.find_one({"user_id": user_id}, {"_id": 0})
        last_active = (act_doc or {}).get("last_active") or u.get("created_at", "")

        total_q      = stats.get("total_questions", 0)
        acc          = round(stats.get("correct_answers", 0) / max(total_q, 1) * 100, 1) if total_q > 0 else 0
        cur_streak   = streak.get("current_streak", 0)
        days_inactive = 999
        if last_active:
            try:
                ldt = datetime.fromisoformat(last_active.replace("Z", "+00:00"))
                days_inactive = (datetime.now(timezone.utc) - ldt).days
            except Exception:
                pass

        if days_inactive > 14:
            rec = f"Inaktiv seit {days_inactive} Tagen. Erinnerung oder Re-Engagement empfohlen."
        elif total_q > 200 and acc > 75 and not all([u.get("notebook_enabled"), u.get("analyzer_enabled"), u.get("podcast_enabled")]):
            rec = f"Engagierter Benutzer ({total_q} Fragen, {acc}% Genauigkeit). Empfehle: Alle Funktionen freischalten."
        elif total_q > 50 and cur_streak >= 5:
            rec = f"Aktiver Lernender ({cur_streak}-Tage-Streak). Guter Kandidat für Premium-Funktionen."
        elif total_q < 10:
            rec = "Neuer Benutzer in der Orientierungsphase — kein Handlungsbedarf."
        else:
            rec = f"Regelmäßiger Benutzer. Gesamtscore: {score}/100. Weiter beobachten."

        return {
            "user":               u,
            "score":              score,
            "tier":               tier,
            "stats":              stats,
            "streak":             streak,
            "daily_activity":     daily,
            "subject_performance": subjects,
            "access_requests":    reqs,
            "recommendation":     rec,
            "last_active":        last_active,
            "active_days_30":     active_days,
        }

    return router
