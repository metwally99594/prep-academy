from fastapi import APIRouter, HTTPException, Depends
import math, logging
from datetime import datetime, timezone
from auth import get_current_user

logger = logging.getLogger("masterclass")

router = APIRouter(prefix="/api", tags=["masterclass"])


@router.get("/masterclass/levels")
async def get_masterclass_levels(user: dict = Depends(get_current_user)):
    from database import db
    levels = await db.masterclass_levels.find(
        {}, {"_id": 0}
    ).sort("level_number", 1).to_list(200)

    progress = await db.masterclass_progress.find_one(
        {"user_id": user["id"]},
        {"_id": 0},
    )
    completed = set(progress.get("completed_levels", [])) if progress else set()
    current = progress.get("current_level", 1) if progress else 1

    result = []
    for lv in levels:
        n = lv["level_number"]
        is_completed = n in completed
        is_current = n == current
        is_locked = n > current and not is_completed
        result.append({
            "level_number": n,
            "title": lv["title"],
            "description": lv.get("description", ""),
            "chapter": lv.get("chapter", math.ceil(n / 10)),
            "is_completed": is_completed,
            "is_current": is_current,
            "is_locked": is_locked,
        })
    return {"levels": result, "current_level": current, "completed_count": len(completed)}


@router.get("/masterclass/levels/{level_number}")
async def get_masterclass_level(level_number: int, user: dict = Depends(get_current_user)):
    from database import db
    lv = await db.masterclass_levels.find_one(
        {"level_number": level_number},
        {"_id": 0},
    )
    if not lv:
        raise HTTPException(404, "Level nicht gefunden")
    return lv


@router.post("/masterclass/levels/{level_number}/complete")
async def complete_masterclass_level(level_number: int, user: dict = Depends(get_current_user)):
    from database import db
    try:
        lv = await db.masterclass_levels.find_one({"level_number": level_number})
        if not lv:
            raise HTTPException(404, "Level nicht gefunden")

        now = datetime.now(timezone.utc).isoformat()
        await db.masterclass_progress.update_one(
            {"user_id": user["id"]},
            {
                "$addToSet": {"completed_levels": level_number},
                "$set": {"current_level": level_number + 1, "last_activity": now},
                "$setOnInsert": {"user_id": user["id"], "completed_levels": []},
            },
            upsert=True,
        )
        return {"next_level": level_number + 1}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("complete_level(%d) failed: %s", level_number, str(e))
        raise HTTPException(status_code=500, detail=f"Fehler beim Abschließen: {str(e)}")


@router.get("/masterclass/progress")
async def get_masterclass_progress(user: dict = Depends(get_current_user)):
    from database import db
    total = await db.masterclass_levels.count_documents({})
    progress = await db.masterclass_progress.find_one(
        {"user_id": user["id"]},
        {"_id": 0},
    )
    completed_count = len(progress.get("completed_levels", [])) if progress else 0
    current = progress.get("current_level", 1) if progress else 1
    percent = round((completed_count / total) * 100) if total > 0 else 0
    return {
        "current_level": current,
        "completed_count": completed_count,
        "total_levels": total,
        "progress_percent": percent,
    }
