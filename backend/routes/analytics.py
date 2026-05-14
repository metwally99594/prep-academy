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
    # (POST /access-requests is handled by the primary route in server.py)

    @router.get("/access-requests/my")
    async def my_requests(user: dict = Depends(get_current_user)):
        return await db.access_requests.find(
            {"user_id": user["id"]}, {"_id": 0}
        ).sort("requested_at", -1).to_list(20)

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
