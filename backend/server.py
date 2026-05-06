from fastapi import FastAPI, APIRouter, HTTPException, Depends, UploadFile, File, Form, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import StreamingResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import os
import json
from typing import List, Optional
import uuid
from datetime import datetime, timezone
import asyncio


# Import shared modules
from database import (
    db, client, logger, JWT_SECRET, JWT_ALGORITHM,
    LEVELS, SPECIALTIES, EXAM_LOCATIONS,
    get_level_info, compute_badges
)
from models import (
    UserCreate, UserLogin, UserResponse, GoogleAuthCallback,
    QuestionChoice, QuestionCreate, QuestionUpdate, QuestionResponse,
    AnswerSubmit, AnswerResult, FavoriteCreate, StatsResponse,
    AIExplainRequest, AIChatRequest, CustomQuizRequest, SpecialtyResponse,
    NotebookChatRequest, AnalyzeRequest, BulkCityUpdate, BulkDeleteRequest
)
from auth import (
    hash_password, verify_password, create_token,
    get_current_user, get_admin_user, security
)

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

# Disable Swagger/OpenAPI in production for security
_IS_PRODUCTION = os.environ.get("ENVIRONMENT", "production").lower() == "production"
app = FastAPI(
    docs_url=None if _IS_PRODUCTION else "/docs",
    redoc_url=None if _IS_PRODUCTION else "/redoc",
    openapi_url=None if _IS_PRODUCTION else "/openapi.json",
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
api_router = APIRouter(prefix="/api")

# ============ GAMIFICATION CONFIG (imported from database.py) ============

# ============ STARTUP ============

async def _background_db_sync():
    """ALL DB operations run in background after server starts and health check passes."""
    try:
        # Create indexes
        await db.users.create_index("email", unique=True)
        await db.users.create_index("id", unique=True)
        await db.questions.create_index("id", unique=True)
        await db.questions.create_index("specialty_id")
        await db.questions.create_index("year")
        await db.questions.create_index([("specialty_id", 1), ("year", 1)])
        await db.questions.create_index([("specialty_id", 1), ("exam_location", 1)])
        await db.favorites.create_index([("user_id", 1), ("question_id", 1)], unique=True)
        await db.user_stats.create_index("user_id", unique=True)
        await db.daily_activity.create_index([("user_id", 1), ("date", 1)])
        await db.user_streaks.create_index("user_id", unique=True)
        await db.wrong_answers.create_index([("user_id", 1), ("question_id", 1)])
        logger.info("Background: Indexes created")
    except Exception as e:
        logger.error(f"Background index error: {e}")

    try:
        if await db.specialties.count_documents({}) == 0:
            await db.specialties.insert_many(SPECIALTIES)
            logger.info("Background: Seeded specialties")
        else:
            # Ensure pharma specialty exists
            pharma = await db.specialties.find_one({"id": "pharma"})
            if not pharma:
                await db.specialties.insert_one({"id": "pharma", "name": "Pharma", "name_de": "Pharmakologie & Rezeptierkunde", "icon": "Pill"})
                logger.info("Background: Added Pharma specialty")
    except Exception as e:
        logger.error(f"Background specialties error: {e}")

    try:
        admin_email = os.environ.get("ADMIN_EMAIL", "admin@medical.com")
        admin_password = os.environ.get("ADMIN_PASSWORD", "admin123")
        admin = await db.users.find_one({"email": admin_email})
        if not admin:
            admin_user = {
                "id": str(uuid.uuid4()),
                "email": admin_email,
                "password": hash_password(admin_password),
                "name": "المدير",
                "is_admin": True,
                "auth_provider": "email",
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            await db.users.insert_one(admin_user)
            logger.info("Background: Created admin user")
        if admin_password == "admin123":
            logger.warning("SECURITY: ADMIN_PASSWORD is using the default value. Change it via environment variable!")
    except Exception as e:
        logger.error(f"Background admin error: {e}")

    # Migration: Clean bad questions (no correct answer or not 5 choices)
    try:
        cleanup_done = await db.migrations.find_one({"id": "cleanup_bad_questions_v2"})
        if not cleanup_done:
            to_delete_ids = []
            async for q in db.questions.find({}, {"_id": 0, "id": 1, "choices": 1, "choices_de": 1, "correct_answers": 1}):
                choices = q.get("choices") or q.get("choices_de") or []
                has_correct = any(c.get("is_correct") for c in choices if isinstance(c, dict))
                has_correct_answers = q.get("correct_answers") and len(q.get("correct_answers", [])) > 0
                if not (has_correct or has_correct_answers) or len(choices) != 5:
                    to_delete_ids.append(q["id"])
            if to_delete_ids:
                result = await db.questions.delete_many({"id": {"$in": to_delete_ids}})
                logger.info(f"Background cleanup: Deleted {result.deleted_count} bad questions")
            await db.migrations.insert_one({"id": "cleanup_bad_questions_v2", "date": datetime.now(timezone.utc).isoformat()})
    except Exception as e:
        logger.error(f"Background cleanup error: {e}")

    try:
        # Migration: Replace old internal medicine questions with correct ones
        migration_done = await db.migrations.find_one({"id": "replace_internal_v1"})
        if not migration_done:
            import json as json_lib
            seed_file = os.path.join(os.path.dirname(__file__), "seed_questions.json")
            if os.path.exists(seed_file):
                with open(seed_file, 'r', encoding='utf-8') as f:
                    seed_questions = json_lib.load(f)
                seed_internal = [q for q in seed_questions if q.get("specialty_id") == "internal"]
                seed_internal_ids = {q["id"] for q in seed_internal}
                
                deleted = await db.questions.delete_many({
                    "specialty_id": "internal",
                    "id": {"$nin": list(seed_internal_ids)}
                })
                
                existing_ids = set()
                async for q in db.questions.find({"specialty_id": "internal"}, {"id": 1, "_id": 0}):
                    existing_ids.add(q.get("id"))
                new_to_add = [q for q in seed_internal if q["id"] not in existing_ids]
                if new_to_add:
                    await db.questions.insert_many(new_to_add)
                
                await db.migrations.insert_one({"id": "replace_internal_v1", "date": datetime.now(timezone.utc).isoformat()})
                logger.info(f"Background migration: Deleted {deleted.deleted_count} old internal, added {len(new_to_add)} new.")
                del seed_questions
    except Exception as e:
        logger.error(f"Background migration error: {e}")
    
    # Auto-seed questions from JSON file
    try:
        seed_file = os.path.join(os.path.dirname(__file__), "seed_questions.json")
        if os.path.exists(seed_file):
            current_count = await db.questions.count_documents({})
            SEED_TOTAL = 2345
            if current_count < SEED_TOTAL:
                import json as json_lib
                with open(seed_file, 'r', encoding='utf-8') as f:
                    seed_questions = json_lib.load(f)
                if seed_questions:
                    existing_ids = set()
                    async for q in db.questions.find({}, {"id": 1, "_id": 0}):
                        existing_ids.add(q.get("id"))
                    new_questions = [q for q in seed_questions if q.get("id") not in existing_ids]
                    
                    if new_questions:
                        images_file = os.path.join(os.path.dirname(__file__), "seed_images.json")
                        images = {}
                        if os.path.exists(images_file):
                            with open(images_file, 'r') as f:
                                images = json_lib.load(f)
                        for q in new_questions:
                            if q["id"] in images:
                                q["image_base64"] = images[q["id"]]
                        
                        for bi in range(0, len(new_questions), 500):
                            await db.questions.insert_many(new_questions[bi:bi+500])
                        logger.info(f"Background seed: Added {len(new_questions)} questions (DB had {current_count})")
                    else:
                        logger.info("All seed questions already exist")
                    del seed_questions
            else:
                logger.info(f"DB has {current_count} questions, seed not needed")
    except Exception as e:
        logger.error(f"Background seed error: {e}")
    
    logger.info("Background DB sync completed successfully.")

@app.on_event("startup")
async def startup_event():
    # ZERO database operations here - server must start instantly for health check
    asyncio.create_task(_background_db_sync())
    logger.info("Server started. Background DB sync launched.")
    # Start Telegram bot if token is configured
    # Only start in the worker process (not the reloader parent)
    try:
        import sys
        is_reloader = any('--reload' in arg for arg in sys.argv) and os.environ.get('WATCHFILES_FORCE_POLLING') is None
        from telegram_bot import start_bot, get_token
        if get_token():
            asyncio.create_task(start_bot())
            logger.info("Telegram bot task launched.")
    except Exception as e:
        logger.warning(f"Telegram bot not started: {e}")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()

# ============ AUTH ROUTES ============

@api_router.post("/auth/register", response_model=dict)
@limiter.limit("5/minute")
async def register(request: Request, user: UserCreate):
    existing = await db.users.find_one({"email": user.email})
    if existing:
        # Generic message to prevent email enumeration
        raise HTTPException(status_code=400, detail="Registration failed. Please try again.")

    user_doc = {
        "id": str(uuid.uuid4()),
        "email": user.email,
        "password": hash_password(user.password),
        "name": user.name,
        "is_admin": False,
        "auth_provider": "email",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.users.insert_one(user_doc)

    # Initialize user stats
    await db.user_stats.insert_one({
        "user_id": user_doc["id"],
        "total_questions": 0,
        "correct_answers": 0,
        "wrong_answers": 0,
        "by_specialty": {},
        "by_year": {}
    })
    
    token = create_token(user_doc["id"], False)
    return {"token": token, "user": {k: v for k, v in user_doc.items() if k not in ["password", "_id"]}}

@api_router.post("/auth/login", response_model=dict)
@limiter.limit("10/minute")
async def login(request: Request, credentials: UserLogin):
    from auth import _DUMMY_HASH
    user = await db.users.find_one({"email": credentials.email}, {"_id": 0})

    # Always run bcrypt to prevent timing-based user enumeration
    stored_hash = user["password"] if user and user.get("password") else _DUMMY_HASH
    password_ok = verify_password(credentials.password, stored_hash)

    if not user or not password_ok:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_token(user["id"], user.get("is_admin", False))
    return {"token": token, "user": {k: v for k, v in user.items() if k != "password"}}

@api_router.post("/auth/google/callback", response_model=dict)
async def google_callback(data: GoogleAuthCallback):
    """Google Auth is disabled"""
    raise HTTPException(status_code=410, detail="Google Auth is disabled. Please use email/password.")

@api_router.get("/auth/me", response_model=dict)
async def get_me(user: dict = Depends(get_current_user)):
    return {k: v for k, v in user.items() if k != "password"}

# ============ SPECIALTY ROUTES ============

@api_router.get("/specialties")
async def get_specialties():
    # Count questions per specialty + city
    count_pipeline = [
        {"$group": {"_id": {"spec": "$specialty_id", "city": "$exam_location"}, "count": {"$sum": 1}}}
    ]
    raw_counts = await db.questions.aggregate(count_pipeline).to_list(200)
    
    # Build nested counts
    counts = {}
    city_counts = {}
    for doc in raw_counts:
        spec = doc["_id"]["spec"]
        city = doc["_id"]["city"] or "andere"
        count = doc["count"]
        counts[spec] = counts.get(spec, 0) + count
        if spec not in city_counts:
            city_counts[spec] = {}
        city_counts[spec][city] = count
    
    specialties = await db.specialties.find({}, {"_id": 0}).to_list(100)
    for s in specialties:
        s["question_count"] = counts.get(s["id"], 0)
        s["city_counts"] = city_counts.get(s["id"], {})
    return specialties

@api_router.get("/specialties/{specialty_id}")
async def get_specialty(specialty_id: str):
    specialty = await db.specialties.find_one({"id": specialty_id}, {"_id": 0})
    if not specialty:
        raise HTTPException(status_code=404, detail="Specialty not found")
    count = await db.questions.count_documents({"specialty_id": specialty_id})
    return {**specialty, "question_count": count}

@api_router.get("/exam-types")
async def get_exam_types():
    """Return exam type selector options with live question counts"""
    from database import EXAM_TYPES
    result = []
    for et in EXAM_TYPES:
        query = {}
        if et.get("location"):
            query["exam_location"] = et["location"]
        if et.get("specialty"):
            query["specialty_id"] = et["specialty"]
        count = await db.questions.count_documents(query)
        result.append({**et, "question_count": count})
    return result


# ============ GUEST MODE ============

@api_router.get("/guest/questions")
async def get_guest_questions(specialty_id: Optional[str] = None, count: int = 5):
    """Get random questions for guests (no auth required) - limited to 5"""
    count = min(count, 5)
    query = {}
    if specialty_id:
        query["specialty_id"] = specialty_id
    pipeline = [
        {"$match": query},
        {"$sample": {"size": count}},
        {"$project": {"_id": 0, "id": 1, "specialty_id": 1, "question_text": 1,
                      "question_text_de": 1, "choices": 1, "choices_de": 1, "explanation_de": 1, "year": 1}}
    ]
    questions = await db.questions.aggregate(pipeline).to_list(count)
    for q in questions:
        if not q.get("choices") and q.get("choices_de"):
            q["choices"] = q["choices_de"]
    return questions


@api_router.get("/guest/specialties")
async def get_guest_specialties():
    """Get specialties with counts for guest view"""
    specs = []
    async for s in db.specialties.find({}, {"_id": 0, "id": 1, "name": 1, "name_de": 1, "icon": 1, "color": 1}):
        count = await db.questions.count_documents({"specialty_id": s["id"]})
        if count > 0:
            specs.append({**s, "question_count": count})
    return specs


@api_router.get("/seo/specialty/{specialty_id}")
async def get_seo_specialty_page(specialty_id: str):
    """Public SEO page data for a specialty - no auth required"""
    spec = await db.specialties.find_one({"id": specialty_id}, {"_id": 0})
    if not spec:
        raise HTTPException(status_code=404, detail="Fachgebiet nicht gefunden")

    total = await db.questions.count_documents({"specialty_id": specialty_id})

    # Get 3 sample questions (public preview)
    pipeline = [
        {"$match": {"specialty_id": specialty_id}},
        {"$sample": {"size": 3}},
        {"$project": {"_id": 0, "id": 1, "question_text_de": 1, "question_text": 1,
                      "choices": 1, "explanation_de": 1, "year": 1}}
    ]
    samples = await db.questions.aggregate(pipeline).to_list(3)

    # Get year distribution
    year_pipeline = [
        {"$match": {"specialty_id": specialty_id, "year": {"$exists": True}}},
        {"$group": {"_id": "$year", "count": {"$sum": 1}}},
        {"$sort": {"_id": -1}}
    ]
    years = await db.questions.aggregate(year_pipeline).to_list(20)

    # Total users who answered this specialty
    user_pipeline = [
        {"$match": {f"by_specialty.{specialty_id}.total": {"$gt": 0}}},
        {"$count": "users"}
    ]
    user_result = await db.user_stats.aggregate(user_pipeline).to_list(1)
    active_users = user_result[0]["users"] if user_result else 0

    return {
        "id": spec["id"],
        "name_de": spec.get("name_de", ""),
        "icon": spec.get("icon", ""),
        "color": spec.get("color", ""),
        "total_questions": total,
        "sample_questions": samples,
        "years": [{"year": y["_id"], "count": y["count"]} for y in years],
        "active_users": active_users,
    }


@api_router.get("/seo/stats")
async def get_seo_stats():
    """Public stats for landing page - no auth required"""
    total_q = await db.questions.count_documents({})
    total_users = await db.users.count_documents({})
    total_specs = await db.specialties.count_documents({})
    return {"total_questions": total_q, "total_users": total_users, "total_specialties": total_specs}


# ============ WEAKNESS MAP & PERCENTILE ============

@api_router.get("/dashboard/weakness-map")
async def get_weakness_map(user: dict = Depends(get_current_user)):
    """Get user's weakness map - accuracy per specialty with recommendations"""
    stats = await db.user_stats.find_one({"user_id": user["id"]}, {"_id": 0})
    if not stats:
        return {"specialties": [], "weakest": None, "strongest": None}

    by_spec = stats.get("by_specialty", {})
    specialties = await db.specialties.find({}, {"_id": 0, "id": 1, "name_de": 1, "icon": 1, "color": 1}).to_list(100)
    spec_map = {s["id"]: s for s in specialties}

    results = []
    for spec_id, data in by_spec.items():
        total = data.get("total", 0)
        correct = data.get("correct", 0)
        if total < 1:
            continue
        accuracy = round(correct / total * 100, 1)
        spec_info = spec_map.get(spec_id, {})
        results.append({
            "id": spec_id,
            "name_de": spec_info.get("name_de", spec_id),
            "icon": spec_info.get("icon", ""),
            "color": spec_info.get("color", "#666"),
            "total": total,
            "correct": correct,
            "accuracy": accuracy,
            "level": "strong" if accuracy >= 80 else "medium" if accuracy >= 60 else "weak",
        })

    results.sort(key=lambda x: x["accuracy"])
    weakest = results[0] if results else None
    strongest = results[-1] if results else None

    return {"specialties": results, "weakest": weakest, "strongest": strongest}


@api_router.get("/dashboard/percentile")
async def get_percentile(user: dict = Depends(get_current_user)):
    """Get user's percentile rank compared to all users"""
    my_stats = await db.user_stats.find_one({"user_id": user["id"]}, {"_id": 0})
    if not my_stats:
        return {"percentile": 0, "rank": 0, "total_users": 0, "pass_probability": 0}

    my_total = my_stats.get("total_questions", 0)
    my_correct = my_stats.get("correct_answers", 0)
    my_accuracy = (my_correct / my_total * 100) if my_total > 0 else 0
    my_xp = my_stats.get("xp", 0)

    # Count how many users have lower XP
    all_stats = await db.user_stats.find({}, {"_id": 0, "xp": 1, "total_questions": 1, "correct_answers": 1}).to_list(10000)
    total_users = len(all_stats)
    if total_users <= 1:
        return {"percentile": 100, "rank": 1, "total_users": total_users, "accuracy": round(my_accuracy, 1), "pass_probability": min(round(my_accuracy * 1.1, 1), 99)}

    lower_count = sum(1 for s in all_stats if s.get("xp", 0) < my_xp)
    percentile = round(lower_count / total_users * 100, 1)

    # Calculate pass probability based on accuracy and coverage
    total_q = await db.questions.count_documents({})
    coverage = (my_total / total_q * 100) if total_q > 0 else 0
    pass_prob = min(round(my_accuracy * 0.7 + coverage * 0.3, 1), 99) if my_total > 20 else min(round(my_accuracy * 0.5, 1), 50)

    return {
        "percentile": percentile,
        "rank": total_users - lower_count,
        "total_users": total_users,
        "accuracy": round(my_accuracy, 1),
        "pass_probability": pass_prob,
    }


# ============ CHALLENGE MODE ============

@api_router.post("/challenge/create")
async def create_challenge(
    specialty_id: str = "",
    count: int = 10,
    year: Optional[int] = None,
    exam_location: Optional[str] = None,
    all_questions: bool = False,
    user: dict = Depends(get_current_user)
):
    """Create a challenge with full filtering: specialty, year, city, count, or ALL"""
    query = {}
    if specialty_id:
        query["specialty_id"] = specialty_id
    if year:
        query["year"] = year
    if exam_location:
        query["exam_location"] = exam_location

    if all_questions:
        # Get ALL matching questions
        question_ids = [q["id"] async for q in db.questions.find(query, {"_id": 0, "id": 1})]
    else:
        count = min(max(count, 5), 50)
        pipeline = [
            {"$match": query},
            {"$sample": {"size": count}},
            {"$project": {"_id": 0, "id": 1}}
        ]
        question_ids = [q["id"] for q in await db.questions.aggregate(pipeline).to_list(count)]

    if not question_ids:
        raise HTTPException(status_code=404, detail="Keine Fragen gefunden")

    challenge_id = str(uuid.uuid4())[:8]

    # Build description
    desc_parts = []
    if specialty_id:
        spec = await db.specialties.find_one({"id": specialty_id}, {"_id": 0, "name_de": 1})
        desc_parts.append(spec.get("name_de", specialty_id) if spec else specialty_id)
    else:
        desc_parts.append("Alle Fächer")
    if year:
        desc_parts.append(str(year))
    if exam_location:
        city_names = {"vienna": "Wien", "innsbruck": "Innsbruck", "andere": "Andere Stadt"}
        desc_parts.append(city_names.get(exam_location, exam_location))
    spec_name = " | ".join(desc_parts)

    await db.challenges.insert_one({
        "id": challenge_id,
        "creator_id": user["id"],
        "creator_name": user.get("name", "Anonym"),
        "specialty_id": specialty_id,
        "specialty_name": spec_name,
        "year": year,
        "exam_location": exam_location,
        "question_ids": question_ids,
        "count": len(question_ids),
        "results": [],
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    return {"challenge_id": challenge_id, "count": len(question_ids), "specialty": spec_name}


@api_router.get("/challenge/{challenge_id}")
async def get_challenge(challenge_id: str, user: dict = Depends(get_current_user)):
    """Get challenge details and questions"""
    ch = await db.challenges.find_one({"id": challenge_id}, {"_id": 0})
    if not ch:
        raise HTTPException(status_code=404, detail="Challenge nicht gefunden")

    def strip_correct_from_choices(choices):
        """Remove is_correct flag from choices before sending to client."""
        if not choices:
            return choices
        return [{k: v for k, v in c.items() if k != "is_correct"} for c in choices]

    # Get questions (correct answers and is_correct flags are never sent to client)
    questions = []
    for qid in ch.get("question_ids", []):
        q = await db.questions.find_one({"id": qid}, {"_id": 0, "id": 1, "specialty_id": 1,
            "question_text": 1, "question_text_de": 1, "choices": 1, "choices_de": 1,
            "explanation_de": 1, "question_type": 1, "drag_drop_items": 1,
            "drag_drop_categories": 1, "blank_text": 1, "blank_answers": 1})
        if q:
            # Strip correct answer indicators before sending to client
            q["choices"] = strip_correct_from_choices(q.get("choices") or q.get("choices_de") or [])
            q.pop("choices_de", None)
            q.pop("blank_answers", None)  # also hide fill-in-blank answers
            questions.append(q)

    already_played = any(r["user_id"] == user["id"] for r in ch.get("results", []))

    return {
        "id": ch["id"],
        "creator_name": ch.get("creator_name", "Anonym"),
        "specialty_name": ch.get("specialty_name", ""),
        "count": ch.get("count", 0),
        "questions": questions,
        "results": ch.get("results", []),
        "already_played": already_played,
    }


@api_router.post("/challenge/{challenge_id}/submit")
async def submit_challenge_result(challenge_id: str, score: int = 0, total: int = 0, user: dict = Depends(get_current_user)):
    """Submit challenge result"""
    ch = await db.challenges.find_one({"id": challenge_id}, {"_id": 0})
    if not ch:
        raise HTTPException(status_code=404, detail="Challenge nicht gefunden")

    # Server-side validation: score must be non-negative and ≤ actual question count
    actual_count = ch.get("count", len(ch.get("question_ids", [])))
    if score < 0 or total < 0:
        raise HTTPException(status_code=400, detail="Ungültige Punktzahl")
    if score > actual_count or total > actual_count:
        raise HTTPException(status_code=400, detail="Ungültige Punktzahl")
    # Use server-authoritative total (question count) instead of client-supplied total
    validated_total = actual_count

    result_entry = {
        "user_id": user["id"],
        "user_name": user.get("name", "Anonym"),
        "score": score,
        "total": validated_total,
        "accuracy": round(score / validated_total * 100, 1) if validated_total > 0 else 0,
        "submitted_at": datetime.now(timezone.utc).isoformat(),
    }

    # Remove old result for same user, add new
    await db.challenges.update_one(
        {"id": challenge_id},
        {"$pull": {"results": {"user_id": user["id"]}}}
    )
    await db.challenges.update_one(
        {"id": challenge_id},
        {"$push": {"results": result_entry}}
    )

    # Get updated results
    ch = await db.challenges.find_one({"id": challenge_id}, {"_id": 0, "results": 1})
    return {"results": ch.get("results", [])}

# ============ QUESTION ROUTES ============

@api_router.get("/questions", response_model=List[QuestionResponse])
async def get_questions(
    specialty_id: Optional[str] = None,
    year: Optional[int] = None,
    exam_location: Optional[str] = None,
    limit: int = 30,
    skip: int = 0,
    user: dict = Depends(get_current_user),
):
    limit = min(limit, 100)  # hard cap to prevent mass extraction
    query = {}
    if specialty_id:
        query["specialty_id"] = specialty_id
    if year:
        query["year"] = year
    if exam_location:
        query["exam_location"] = exam_location

    questions = await db.questions.find(query, {"_id": 0}).skip(skip).limit(limit).to_list(limit)
    return questions

@api_router.get("/questions/search/text")
async def search_questions(
    q: str,
    limit: int = 50,
    user: dict = Depends(get_current_user),
):
    """Smart search: works with punctuation, numbering, partial text, full questions"""
    if not q or len(q) < 2:
        return []
    
    import re as _re
    
    # Check if query is a year
    if q.strip().isdigit() and len(q.strip()) == 4:
        questions = await db.questions.find({"year": int(q.strip())}, {"_id": 0}).limit(limit).to_list(limit)
        return questions
    
    # City aliases
    city_map = {
        "wien": "vienna", "vienna": "vienna", "فيينا": "vienna",
        "innsbruck": "innsbruck", "إنسبروك": "innsbruck",
        "andere": "andere",
    }
    if q.strip().lower() in city_map:
        questions = await db.questions.find({"exam_location": city_map[q.strip().lower()]}, {"_id": 0}).limit(limit).to_list(limit)
        return questions
    
    # Strip numbering patterns: "1.", "1)", "a)", "A.", "Frage 5:" etc.
    cleaned = _re.sub(r'^[\s]*(?:\d+[\.\)\:]|[a-zA-Z][\.\)]|Frage\s*\d+[\.\:\)]?)\s*', '', q.strip())
    if not cleaned:
        cleaned = q.strip()
    
    # Remove all punctuation except German umlauts and ß, keep spaces
    cleaned = _re.sub(r'[^\w\sÄäÖöÜüß]', ' ', cleaned)
    # Collapse whitespace
    cleaned = _re.sub(r'\s+', ' ', cleaned).strip()
    
    if len(cleaned) < 2:
        return []
    
    # Extract meaningful tokens (3+ chars to skip noise like "ist", "der")
    tokens = [t for t in cleaned.split() if len(t) >= 3]
    
    if not tokens:
        # Fallback: use the cleaned string as-is
        tokens = [cleaned]
    
    # Build regex: all tokens must appear (AND), in any order
    # Each token is escaped and wrapped in a lookahead
    token_pattern = "".join(f"(?=.*{_re.escape(t)})" for t in tokens[:8])
    fuzzy_regex = f"^{token_pattern}" if token_pattern else _re.escape(cleaned)
    
    text_fields = ["question_text_de", "question_text", "explanation_de"]
    search_conditions = []
    for field in text_fields:
        search_conditions.append({field: {"$regex": fuzzy_regex, "$options": "is"}})
    
    # Also search choices
    search_conditions.append({"choices.text_de": {"$regex": fuzzy_regex, "$options": "is"}})
    search_conditions.append({"choices.text": {"$regex": fuzzy_regex, "$options": "is"}})
    
    # Also try exact escaped match on specialty_id
    escaped_q = _re.escape(q.strip())
    search_conditions.append({"specialty_id": {"$regex": escaped_q, "$options": "i"}})
    
    query = {"$or": search_conditions}
    questions = await db.questions.find(query, {"_id": 0}).limit(limit).to_list(limit)
    
    # Fallback: if AND search returns too few results, try OR search (any token matches)
    if len(questions) < 3 and len(tokens) > 1:
        or_conditions = []
        for t in tokens[:6]:
            t_escaped = _re.escape(t)
            or_conditions.append({"question_text_de": {"$regex": t_escaped, "$options": "i"}})
            or_conditions.append({"question_text": {"$regex": t_escaped, "$options": "i"}})
            or_conditions.append({"choices.text_de": {"$regex": t_escaped, "$options": "i"}})
        
        existing_ids = {q["id"] for q in questions}
        fallback = await db.questions.find(
            {"$or": or_conditions, "id": {"$nin": list(existing_ids)}},
            {"_id": 0}
        ).limit(limit - len(questions)).to_list(limit - len(questions))
        questions.extend(fallback)
    
    return questions

@api_router.get("/questions/years/list")
async def get_available_years(specialty_id: Optional[str] = None):
    match_stage = {}
    if specialty_id:
        match_stage["specialty_id"] = specialty_id
    pipeline = [
        {"$match": match_stage} if match_stage else {"$match": {}},
        {"$group": {"_id": "$year"}},
        {"$sort": {"_id": -1}}
    ]
    years = await db.questions.aggregate(pipeline).to_list(100)
    return [y["_id"] for y in years]

@api_router.get("/simulation/questions")
async def get_simulation_questions(city: str = "vienna", user: dict = Depends(get_current_user)):
    """Get 250 questions for exam simulation - redistributes from empty specialties."""
    exam_structure = [
        ("internal", 30), ("surgery", 30), ("pediatrics", 30),
        ("neurology", 25), ("dermatology", 25), ("obgyn", 25),
        ("emergency", 25), ("ent", 20), ("psychiatry", 20),
        ("ophthalmology", 20),
    ]
    
    TARGET = 250
    all_questions = []
    remaining = 0
    specs_with_questions = []
    
    for spec_id, target in exam_structure:
        pipeline = [
            {"$match": {"specialty_id": spec_id}},
            {"$sample": {"size": target}},
            {"$project": {"_id": 0, "id": 1, "specialty_id": 1, "year": 1,
                         "question_text": 1, "question_text_de": 1, "choices": 1,
                         "choices_de": 1, "correct_answers": 1,
                         "explanation_de": 1, "exam_location": 1, "image_base64": 1,
                         "question_type": 1, "drag_drop_items": 1, "drag_drop_categories": 1,
                         "blank_text": 1, "blank_answers": 1, "tags": 1}}
        ]
        questions = await db.questions.aggregate(pipeline).to_list(target)
        all_questions.extend(questions)
        if len(questions) < target:
            remaining += target - len(questions)
        if len(questions) > 0:
            specs_with_questions.append(spec_id)
    
    # Fill remaining slots from specialties that have extra questions
    if remaining > 0 and specs_with_questions:
        existing_ids = {q["id"] for q in all_questions}
        per_spec = max(1, remaining // len(specs_with_questions)) + 2
        
        for spec_id in specs_with_questions:
            if remaining <= 0:
                break
            pipeline = [
                {"$match": {"specialty_id": spec_id, "id": {"$nin": list(existing_ids)}}},
                {"$sample": {"size": per_spec}},
                {"$project": {"_id": 0, "id": 1, "specialty_id": 1, "year": 1,
                             "question_text": 1, "question_text_de": 1, "choices": 1,
                             "choices_de": 1, "correct_answers": 1,
                             "explanation_de": 1, "exam_location": 1, "image_base64": 1}}
            ]
            extra = await db.questions.aggregate(pipeline).to_list(per_spec)
            for q in extra:
                if remaining <= 0:
                    break
                if q["id"] not in existing_ids:
                    all_questions.append(q)
                    existing_ids.add(q["id"])
                    remaining -= 1
    
    import random
    random.shuffle(all_questions)
    return all_questions[:TARGET]

@api_router.get("/questions/quiz")
async def get_quiz_questions(
    specialty_id: Optional[str] = None,
    year: Optional[int] = None,
    exam_location: Optional[str] = None,
    limit: int = 50,
    mode: str = "exam",
    user: dict = Depends(get_current_user),
):
    """Get questions for quiz. mode=study returns ALL questions, mode=exam uses random sampling"""
    query = {}
    if specialty_id:
        query["specialty_id"] = specialty_id
    if year:
        query["year"] = year
    if exam_location:
        query["exam_location"] = exam_location
    
    project = {
        "_id": 0, "id": 1, "specialty_id": 1, "year": 1,
        "question_text": 1, "question_text_de": 1,
        "choices": 1, "choices_de": 1, "correct_answers": 1,
        "explanation_de": 1, "exam_location": 1, "image_base64": 1,
        "question_type": 1, "drag_drop_items": 1, "drag_drop_categories": 1,
        "blank_text": 1, "blank_answers": 1, "tags": 1,
    }

    if mode == "study":
        # Study mode: return ALL questions for the specialty
        questions = await db.questions.find(query, project).to_list(5000)
    else:
        # Exam mode: random sample
        pipeline = []
        if query:
            pipeline.append({"$match": query})
        pipeline.append({"$sample": {"size": min(limit, 200)}})
        pipeline.append({"$project": project})
        questions = await db.questions.aggregate(pipeline).to_list(min(limit, 200))
    
    return questions

@api_router.get("/questions/count")
async def get_questions_count(
    specialty_id: Optional[str] = None,
    year: Optional[int] = None,
    exam_location: Optional[str] = None,
):
    """Fast count endpoint - no data transfer"""
    query = {}
    if specialty_id:
        query["specialty_id"] = specialty_id
    if year:
        query["year"] = year
    if exam_location:
        query["exam_location"] = exam_location
    return {"count": await db.questions.count_documents(query)}

@api_router.post("/questions/custom-quiz")
async def custom_quiz(request: CustomQuizRequest, user: dict = Depends(get_current_user)):
    """Advanced custom quiz with multiple filters"""
    query = {}

    # Multiple specialties
    if request.specialties:
        query["specialty_id"] = {"$in": request.specialties}

    # Exam location (city)
    if request.exam_location:
        query["exam_location"] = request.exam_location

    # Year range
    if request.year_from and request.year_to:
        query["year"] = {"$gte": request.year_from, "$lte": request.year_to}
    elif request.year_from:
        query["year"] = {"$gte": request.year_from}
    elif request.year_to:
        query["year"] = {"$lte": request.year_to}

    # Text search
    if request.text_search and len(request.text_search) >= 2:
        query["$or"] = [
            {"question_text_de": {"$regex": request.text_search, "$options": "i"}},
            {"question_text": {"$regex": request.text_search, "$options": "i"}},
        ]

    # Favorites only
    if request.favorites_only:
        favs = await db.favorites.find({"user_id": user["id"]}, {"_id": 0, "question_id": 1}).to_list(5000)
        fav_ids = [f["question_id"] for f in favs]
        if not fav_ids:
            return []
        query["id"] = {"$in": fav_ids}

    # Tags filter
    if request.tags:
        query["tags"] = {"$in": request.tags}

    project = {
        "_id": 0, "id": 1, "specialty_id": 1, "year": 1,
        "question_text": 1, "question_text_de": 1,
        "choices": 1, "choices_de": 1, "correct_answers": 1,
        "explanation_de": 1, "exam_location": 1, "image_base64": 1, "tags": 1,
        "question_type": 1, "drag_drop_items": 1, "drag_drop_categories": 1,
        "blank_text": 1, "blank_answers": 1,
    }

    limit = min(request.limit, 500)

    if request.mode == "study":
        questions = await db.questions.find(query, project).to_list(limit)
    else:
        pipeline = []
        if query:
            pipeline.append({"$match": query})
        pipeline.append({"$sample": {"size": limit}})
        pipeline.append({"$project": project})
        questions = await db.questions.aggregate(pipeline).to_list(limit)

    return questions

@api_router.post("/questions/custom-quiz/count")
async def custom_quiz_count(request: CustomQuizRequest, user: dict = Depends(get_current_user)):
    """Count matching questions for custom quiz filters"""
    query = {}

    if request.specialties:
        query["specialty_id"] = {"$in": request.specialties}

    if request.exam_location:
        query["exam_location"] = request.exam_location

    if request.year_from and request.year_to:
        query["year"] = {"$gte": request.year_from, "$lte": request.year_to}
    elif request.year_from:
        query["year"] = {"$gte": request.year_from}
    elif request.year_to:
        query["year"] = {"$lte": request.year_to}

    if request.text_search and len(request.text_search) >= 2:
        query["$or"] = [
            {"question_text_de": {"$regex": request.text_search, "$options": "i"}},
            {"question_text": {"$regex": request.text_search, "$options": "i"}},
        ]

    if request.favorites_only:
        favs = await db.favorites.find({"user_id": user["id"]}, {"_id": 0, "question_id": 1}).to_list(5000)
        fav_ids = [f["question_id"] for f in favs]
        if not fav_ids:
            return {"count": 0}
        query["id"] = {"$in": fav_ids}

    if request.tags:
        query["tags"] = {"$in": request.tags}

    count = await db.questions.count_documents(query)
    return {"count": count}

@api_router.get("/questions/{question_id}", response_model=QuestionResponse)
async def get_question(question_id: str, user: dict = Depends(get_current_user)):
    question = await db.questions.find_one({"id": question_id}, {"_id": 0})
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    return question

@api_router.get("/admin/questions/duplicates")
async def find_duplicate_questions(specialty_id: Optional[str] = None, admin: dict = Depends(get_admin_user)):
    """Find duplicate questions grouped by normalized text + choices fingerprint"""
    import re as _re
    
    match_stage = {}
    if specialty_id:
        match_stage["specialty_id"] = specialty_id

    projection = {
        "_id": 0, "id": 1, "specialty_id": 1, "year": 1, "exam_location": 1,
        "question_text_de": 1, "question_text": 1,
        "choices": 1, "choices_de": 1, "correct_answers": 1,
    }
    cursor = db.questions.find(match_stage, projection)
    all_questions = await cursor.to_list(10000)

    def normalize(text):
        if not text:
            return ""
        t = text.strip().lower()
        t = _re.sub(r'\s+', ' ', t)
        return t

    def get_choices_fingerprint(q):
        texts = []
        for c in (q.get("choices") or []):
            t = c.get("text_de") or c.get("text") or ""
            if t.strip():
                texts.append(normalize(t))
        for c in (q.get("choices_de") or []):
            t = c.get("text") or ""
            if t.strip():
                texts.append(normalize(t))
        texts.sort()
        return "|".join(texts)

    groups = {}
    for q in all_questions:
        text = q.get("question_text_de") or q.get("question_text") or ""
        norm_text = normalize(text)
        if not norm_text or len(norm_text) < 10:
            continue
        choices_fp = get_choices_fingerprint(q)
        key = f"{norm_text}||{choices_fp}"
        if key not in groups:
            groups[key] = []
        groups[key].append(q)

    duplicate_groups = []
    for key, questions in groups.items():
        if len(questions) >= 2:
            duplicate_groups.append({
                "_id": questions[0].get("question_text_de") or questions[0].get("question_text", ""),
                "count": len(questions),
                "questions": questions
            })

    duplicate_groups.sort(key=lambda g: g["count"], reverse=True)
    duplicate_groups = duplicate_groups[:200]

    total_dupes = sum(g["count"] - 1 for g in duplicate_groups)
    return {"groups": duplicate_groups, "total_duplicate_groups": len(duplicate_groups), "total_extra_copies": total_dupes}


@api_router.get("/admin/questions/{question_id}")
async def admin_get_question(question_id: str, admin: dict = Depends(get_admin_user)):
    """Admin: get a single question by ID for editing"""
    question = await db.questions.find_one({"id": question_id}, {"_id": 0})
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    return question


@api_router.post("/questions", response_model=QuestionResponse)
async def create_question(question: QuestionCreate, admin: dict = Depends(get_admin_user)):
    _dump = question.dict() if hasattr(question, 'dict') else question.model_dump()
    _choices_dump = [c.dict() if hasattr(c, 'dict') else c.model_dump() for c in question.choices]
    question_doc = {
        "id": str(uuid.uuid4()),
        **_dump,
        "choices": _choices_dump,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.questions.insert_one(question_doc)
    question_doc.pop("_id", None)
    return question_doc

@api_router.put("/questions/{question_id}", response_model=QuestionResponse)
async def update_question(question_id: str, question: QuestionUpdate, admin: dict = Depends(get_admin_user)):
    existing = await db.questions.find_one({"id": question_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Question not found")
    
    _q_dump = question.dict() if hasattr(question, 'dict') else question.model_dump()
    update_data = {k: v for k, v in _q_dump.items() if v is not None}
    if "choices" in update_data and isinstance(update_data["choices"], list):
        update_data["choices"] = [c.dict() if hasattr(c, 'dict') else (c.model_dump() if hasattr(c, 'model_dump') else c) for c in update_data["choices"]]
    
    if update_data:
        await db.questions.update_one({"id": question_id}, {"$set": update_data})
    
    updated = await db.questions.find_one({"id": question_id}, {"_id": 0})
    return updated

@api_router.delete("/questions/{question_id}")
async def delete_question(question_id: str, admin: dict = Depends(get_admin_user)):
    result = await db.questions.delete_one({"id": question_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Question not found")
    # Remove from favorites
    await db.favorites.delete_many({"question_id": question_id})
    return {"message": "Question deleted"}

# ============ ANSWER ROUTES ============

@api_router.post("/questions/{question_id}/answer", response_model=AnswerResult)
async def submit_answer(question_id: str, answer: AnswerSubmit, user: dict = Depends(get_current_user)):
    question = await db.questions.find_one({"id": question_id}, {"_id": 0})
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    
    # Support both data formats: choices with is_correct flag, or choices_de with correct_answers list
    choices = question.get("choices") or question.get("choices_de", [])
    correct_ids = [c["id"] for c in choices if c.get("is_correct")]
    if not correct_ids:
        # Fall back to correct_answers list (used by imported questions)
        correct_ids = question.get("correct_answers", [])
    question_type = question.get("question_type", "single_choice")
    if question_type == "drag_drop" or question_type == "kategorisierung":
        if answer.drag_drop_answer:
            items = question.get("drag_drop_items", [])
            is_correct = all(answer.drag_drop_answer.get(item["id"]) == item["correct_category"] for item in items)
        else:
            is_correct = False
    elif question_type == "luckentext":
        if answer.blank_answer:
            correct_blanks = question.get("blank_answers", [])
            is_correct = any(answer.blank_answer.strip().lower() == b.strip().lower() for b in correct_blanks)
        else:
            is_correct = False
    else:
        is_correct = set(answer.selected_choice_ids) == set(correct_ids) if correct_ids else False
    
    # Update user stats
    stats = await db.user_stats.find_one({"user_id": user["id"]})
    
    # Calculate XP: correct=10, wrong=2, streak bonus
    streak_data = await db.user_streaks.find_one({"user_id": user["id"]})
    streak_bonus = min(streak_data.get("current_streak", 0), 10) if streak_data else 0
    xp_earned = (10 + streak_bonus) if is_correct else 2
    
    old_xp = stats.get("xp", 0) if stats else 0
    old_level_info = get_level_info(old_xp)
    new_xp = old_xp + xp_earned
    new_level_info = get_level_info(new_xp)
    leveled_up = new_level_info["level"] > old_level_info["level"]
    
    if stats:
        update = {
            "$inc": {
                "total_questions": 1,
                "correct_answers": 1 if is_correct else 0,
                "wrong_answers": 0 if is_correct else 1,
                "xp": xp_earned,
                f"by_specialty.{question['specialty_id']}.total": 1,
                f"by_specialty.{question['specialty_id']}.correct": 1 if is_correct else 0,
                f"by_year.{question['year']}.total": 1,
                f"by_year.{question['year']}.correct": 1 if is_correct else 0,
            }
        }
        await db.user_stats.update_one({"user_id": user["id"]}, update)
    else:
        await db.user_stats.insert_one({
            "user_id": user["id"],
            "total_questions": 1,
            "correct_answers": 1 if is_correct else 0,
            "wrong_answers": 0 if is_correct else 1,
            "xp": xp_earned,
            "by_specialty": {question['specialty_id']: {"total": 1, "correct": 1 if is_correct else 0}},
            "by_year": {str(question['year']): {"total": 1, "correct": 1 if is_correct else 0}},
        })
    
    # Track daily activity and streak
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    await db.daily_activity.update_one(
        {"user_id": user["id"], "date": today},
        {"$inc": {"questions": 1, "correct": 1 if is_correct else 0}},
        upsert=True
    )
    
    # Update streak
    streak_data = await db.user_streaks.find_one({"user_id": user["id"]})
    import datetime as dt
    yesterday = (datetime.now(timezone.utc) - dt.timedelta(days=1)).strftime("%Y-%m-%d")
    
    if not streak_data:
        await db.user_streaks.insert_one({
            "user_id": user["id"],
            "current_streak": 1,
            "longest_streak": 1,
            "last_activity_date": today
        })
    else:
        last_date = streak_data.get("last_activity_date")
        if last_date != today:
            current_streak = streak_data.get("current_streak", 0)
            longest_streak = streak_data.get("longest_streak", 0)
            
            if last_date == yesterday:
                current_streak += 1
                longest_streak = max(longest_streak, current_streak)
            else:
                current_streak = 1
            
            await db.user_streaks.update_one(
                {"user_id": user["id"]},
                {"$set": {"current_streak": current_streak, "longest_streak": longest_streak, "last_activity_date": today}}
            )
    
    # Track wrong answers for review mode
    if not is_correct:
        existing = await db.wrong_answers.find_one({"user_id": user["id"], "question_id": question_id})
        if not existing:
            await db.wrong_answers.insert_one({
                "id": str(uuid.uuid4()),
                "user_id": user["id"],
                "question_id": question_id,
                "specialty_id": question["specialty_id"],
                "wrong_count": 1,
                "reviewed": False,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "last_wrong_at": datetime.now(timezone.utc).isoformat()
            })
        else:
            await db.wrong_answers.update_one(
                {"user_id": user["id"], "question_id": question_id},
                {"$inc": {"wrong_count": 1}, "$set": {"reviewed": False, "last_wrong_at": datetime.now(timezone.utc).isoformat()}}
            )
        # SM-2: Add to spaced repetition with quality=1 (wrong)
        import datetime as dt
        await db.spaced_repetition.update_one(
            {"user_id": user["id"], "question_id": question_id},
            {"$set": {
                "user_id": user["id"], "question_id": question_id,
                "easiness": 1.3, "interval": 1, "repetitions": 0,
                "next_review": (datetime.now(timezone.utc) + dt.timedelta(days=1)).strftime("%Y-%m-%d"),
                "last_reviewed": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "quality": 1,
            }},
            upsert=True
        )
    else:
        # If answered correctly, mark as reviewed
        await db.wrong_answers.update_one(
            {"user_id": user["id"], "question_id": question_id},
            {"$set": {"reviewed": True}}
        )
        # SM-2: Update with quality=4 (correct)
        import datetime as dt
        sr = await db.spaced_repetition.find_one({"user_id": user["id"], "question_id": question_id}, {"_id": 0})
        if sr:
            e = sr.get("easiness", 2.5)
            interval = sr.get("interval", 1)
            reps = sr.get("repetitions", 0) + 1
            if reps == 1: interval = 1
            elif reps == 2: interval = 6
            else: interval = round(interval * e)
            e = max(1.3, e + 0.1)
            await db.spaced_repetition.update_one(
                {"user_id": user["id"], "question_id": question_id},
                {"$set": {"easiness": round(e, 2), "interval": interval, "repetitions": reps,
                          "next_review": (datetime.now(timezone.utc) + dt.timedelta(days=interval)).strftime("%Y-%m-%d"),
                          "last_reviewed": datetime.now(timezone.utc).strftime("%Y-%m-%d"), "quality": 4}}
            )
    
    # Generate level-up notification
    if leveled_up:
        await db.notifications.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": user["id"],
            "type": "level_up",
            "title": "Level Up!",
            "message": f"Glückwunsch! Du bist jetzt {new_level_info['name_de']} (Level {new_level_info['level']})!",
            "icon": "trophy",
            "read": False,
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
    
    return {
        "is_correct": is_correct,
        "correct_choice_ids": correct_ids,
        "explanation": question.get("explanation") or question.get("explanation_de"),
        "xp_earned": xp_earned,
        "total_xp": new_xp,
        "level": new_level_info,
        "leveled_up": leveled_up,
    }

# ============ FAVORITES ROUTES ============

# ============ SPACED REPETITION (SM-2) ============

@api_router.get("/review/due")
async def get_due_reviews(user: dict = Depends(get_current_user), limit: int = 20):
    """Get questions due for review based on SM-2 algorithm"""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    limit = min(limit, 50)

    due_items = await db.spaced_repetition.find(
        {"user_id": user["id"], "next_review": {"$lte": today}},
        {"_id": 0}
    ).sort("next_review", 1).limit(limit).to_list(limit)

    if not due_items:
        return {"questions": [], "due_count": 0}

    q_ids = [item["question_id"] for item in due_items]
    questions = await db.questions.find(
        {"id": {"$in": q_ids}},
        {"_id": 0, "id": 1, "specialty_id": 1, "question_text": 1, "question_text_de": 1,
         "choices": 1, "choices_de": 1, "explanation_de": 1, "year": 1}
    ).to_list(limit)

    # Attach SR metadata
    sr_map = {item["question_id"]: item for item in due_items}
    for q in questions:
        sr = sr_map.get(q["id"], {})
        q["sr_interval"] = sr.get("interval", 1)
        q["sr_repetitions"] = sr.get("repetitions", 0)
        if not q.get("choices") and q.get("choices_de"):
            q["choices"] = q["choices_de"]

    total_due = await db.spaced_repetition.count_documents(
        {"user_id": user["id"], "next_review": {"$lte": today}}
    )

    return {"questions": questions, "due_count": total_due}


@api_router.post("/review/submit")
async def submit_review(question_id: str, quality: int = 3, user: dict = Depends(get_current_user)):
    """Submit review result using SM-2 algorithm. Quality: 0-5 (0=blackout, 5=perfect)"""
    import datetime as dt
    quality = max(0, min(5, quality))
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    sr = await db.spaced_repetition.find_one(
        {"user_id": user["id"], "question_id": question_id}, {"_id": 0}
    )

    if not sr:
        sr = {"user_id": user["id"], "question_id": question_id,
              "easiness": 2.5, "interval": 1, "repetitions": 0}

    e = sr.get("easiness", 2.5)
    interval = sr.get("interval", 1)
    reps = sr.get("repetitions", 0)

    # SM-2 algorithm
    if quality >= 3:
        if reps == 0:
            interval = 1
        elif reps == 1:
            interval = 6
        else:
            interval = round(interval * e)
        reps += 1
    else:
        reps = 0
        interval = 1

    e = e + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    e = max(1.3, e)

    next_date = (datetime.now(timezone.utc) + dt.timedelta(days=interval)).strftime("%Y-%m-%d")

    await db.spaced_repetition.update_one(
        {"user_id": user["id"], "question_id": question_id},
        {"$set": {
            "user_id": user["id"], "question_id": question_id,
            "easiness": round(e, 2), "interval": interval,
            "repetitions": reps, "next_review": next_date,
            "last_reviewed": today, "quality": quality,
        }},
        upsert=True
    )

    return {"interval": interval, "next_review": next_date, "easiness": round(e, 2)}


@api_router.get("/review/stats")
async def get_review_stats(user: dict = Depends(get_current_user)):
    """Get spaced repetition stats"""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    total = await db.spaced_repetition.count_documents({"user_id": user["id"]})
    due = await db.spaced_repetition.count_documents({"user_id": user["id"], "next_review": {"$lte": today}})
    mastered = await db.spaced_repetition.count_documents({"user_id": user["id"], "interval": {"$gte": 21}})
    return {"total_cards": total, "due_today": due, "mastered": mastered}


# ============ FAVORITES ROUTES ============

@api_router.get("/favorites", response_model=List[QuestionResponse])
async def get_favorites(user: dict = Depends(get_current_user)):
    favorites = await db.favorites.find({"user_id": user["id"]}, {"_id": 0}).to_list(1000)
    question_ids = [f["question_id"] for f in favorites]
    questions = await db.questions.find({"id": {"$in": question_ids}}, {"_id": 0}).to_list(1000)
    return questions

@api_router.post("/favorites", response_model=dict)
async def add_favorite(fav: FavoriteCreate, user: dict = Depends(get_current_user)):
    existing = await db.favorites.find_one({"user_id": user["id"], "question_id": fav.question_id})
    if existing:
        return {"message": "Already in favorites"}
    
    await db.favorites.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        "question_id": fav.question_id,
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    return {"message": "Added to favorites"}

@api_router.delete("/favorites/{question_id}")
async def remove_favorite(question_id: str, user: dict = Depends(get_current_user)):
    result = await db.favorites.delete_one({"user_id": user["id"], "question_id": question_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Favorite not found")
    return {"message": "Removed from favorites"}

@api_router.get("/favorites/check/{question_id}")
async def check_favorite(question_id: str, user: dict = Depends(get_current_user)):
    exists = await db.favorites.find_one({"user_id": user["id"], "question_id": question_id})
    return {"is_favorite": exists is not None}

# ============ REVIEW (WRONG ANSWERS) ROUTES ============

@api_router.get("/review", response_model=List[QuestionResponse])
async def get_wrong_answers(user: dict = Depends(get_current_user), include_reviewed: bool = False):
    """Get questions the user answered incorrectly for review"""
    query = {"user_id": user["id"]}
    if not include_reviewed:
        query["reviewed"] = False
    
    wrong_answers = await db.wrong_answers.find(query, {"_id": 0}).sort("last_wrong_at", -1).to_list(1000)
    question_ids = [w["question_id"] for w in wrong_answers]
    questions = await db.questions.find({"id": {"$in": question_ids}}, {"_id": 0}).to_list(1000)
    return questions

@api_router.get("/review/count")
async def get_wrong_answers_count(user: dict = Depends(get_current_user)):
    """Get count of unreviewed wrong answers"""
    count = await db.wrong_answers.count_documents({"user_id": user["id"], "reviewed": False})
    total = await db.wrong_answers.count_documents({"user_id": user["id"]})
    return {"unreviewed": count, "total": total}

@api_router.delete("/review/{question_id}")
async def remove_from_review(question_id: str, user: dict = Depends(get_current_user)):
    """Remove a question from review list"""
    result = await db.wrong_answers.delete_one({"user_id": user["id"], "question_id": question_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Question not found in review list")
    return {"message": "Removed from review"}

@api_router.post("/review/{question_id}/mark-reviewed")
async def mark_as_reviewed(question_id: str, user: dict = Depends(get_current_user)):
    """Mark a question as reviewed"""
    result = await db.wrong_answers.update_one(
        {"user_id": user["id"], "question_id": question_id},
        {"$set": {"reviewed": True}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Question not found in review list")
    return {"message": "Marked as reviewed"}

# ============ STATS ROUTES ============

@api_router.get("/stats", response_model=StatsResponse)
async def get_stats(user: dict = Depends(get_current_user)):
    stats = await db.user_stats.find_one({"user_id": user["id"]}, {"_id": 0})
    if not stats:
        return StatsResponse(
            total_questions=0,
            correct_answers=0,
            wrong_answers=0,
            accuracy_percentage=0,
            by_specialty={},
            by_year={}
        )
    
    total = stats.get("total_questions", 0)
    correct = stats.get("correct_answers", 0)
    accuracy = (correct / total * 100) if total > 0 else 0
    
    return StatsResponse(
        total_questions=total,
        correct_answers=correct,
        wrong_answers=stats.get("wrong_answers", 0),
        accuracy_percentage=round(accuracy, 1),
        by_specialty=stats.get("by_specialty", {}),
        by_year=stats.get("by_year", {})
    )

# ============ AI ROUTES ============

MODEL_MAP = {
    "gpt-4o": ("openai", "gpt-4o"),
    "claude-sonnet": ("anthropic", "claude-sonnet-4-5-20250929"),
    "gemini-flash": ("gemini", "gemini-3-flash-preview"),
}

LANG_PROMPTS = {
    "de": "Antworte auf Deutsch. Verwende medizinische Fachbegriffe auf Deutsch.",
    "en": "Answer in English. Use medical terminology in English.",
    "ar": "أجب باللغة العربية. استخدم المصطلحات الطبية باللغة العربية مع ذكر المصطلح الألماني بين قوسين عند الحاجة.",
    "ru": "Отвечайте на русском языке. Используйте медицинскую терминологию на русском языке.",
    "uk": "Відповідайте українською мовою. Використовуйте медичну термінологію українською з німецьким терміном у дужках.",
}

def get_model_config(model_key: str):
    return MODEL_MAP.get(model_key, MODEL_MAP["gpt-4o"])

async def _or_text(system_msg: str, user_msg: str, max_tokens: int = 1000) -> str:
    """OpenRouter DeepSeek text call — free tier, strips <think> blocks."""
    import re as _re, httpx
    or_key = os.environ.get("OPENROUTER_API_KEY")
    if not or_key:
        raise HTTPException(status_code=503, detail="AI nicht verfügbar — OPENROUTER_API_KEY fehlt")
    async with httpx.AsyncClient(timeout=55.0) as client:
        r = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {or_key}", "Content-Type": "application/json",
                     "HTTP-Referer": "https://mcq-medical-prep.academy", "X-Title": "PrepAcademy"},
            json={"model": "openai/gpt-oss-120b:free",
                  "messages": [{"role": "system", "content": system_msg},
                                {"role": "user", "content": user_msg}],
                  "max_tokens": max_tokens, "temperature": 0.4},
        )
        d = r.json()
        if "choices" in d and d["choices"]:
            content = d["choices"][0]["message"]["content"] or ""
            return _re.sub(r"<think>.*?</think>", "", content, flags=_re.DOTALL).strip()
        raise HTTPException(status_code=503, detail=f"AI-Antwort fehlgeschlagen: {str(d)[:200]}")

@api_router.get("/ai/models")
async def get_ai_models():
    return [
        {"id": "gpt-4o", "name": "GPT-4o", "provider": "OpenAI", "icon": "openai", "color": "#10a37f"},
        {"id": "claude-sonnet", "name": "Claude Sonnet", "provider": "Anthropic", "icon": "anthropic", "color": "#cc785c"},
        {"id": "gemini-flash", "name": "Gemini Flash", "provider": "Google", "icon": "gemini", "color": "#4285f4"},
    ]

@api_router.get("/ai/languages")
async def get_ai_languages():
    return [
        {"id": "de", "name": "Deutsch", "flag": "DE"},
        {"id": "en", "name": "English", "flag": "GB"},
        {"id": "ar", "name": "العربية", "flag": "SA"},
        {"id": "ru", "name": "Русский", "flag": "RU"},
    ]

@api_router.post("/ai/explain")
async def ai_explain(request: AIExplainRequest, user: dict = Depends(get_current_user)):
    question = await db.questions.find_one({"id": request.question_id}, {"_id": 0})
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    
    try:
        lang_instruction = LANG_PROMPTS.get(request.language, LANG_PROMPTS["de"])
        choices = question.get("choices") or question.get("choices_de") or []
        correct_choices = [c.get("text_de") or c.get("text", "") for c in choices if c.get("is_correct")]
        q_text = question.get("question_text_de") or question.get("question_text", "")
        system_msg = f"Du bist ein medizinischer Lernassistent für österreichische Prüfungsvorbereitung.\n{lang_instruction}\nErkläre klar und präzise."
        prompt = f"""Frage: {q_text}

Richtige Antworten: {', '.join(correct_choices)}

{f"Studentenfrage: {request.user_question}" if request.user_question else ""}

Erkläre warum diese Antworten richtig sind und welche medizinischen Konzepte wichtig sind."""
        response = await _or_text(system_msg, prompt, max_tokens=800)
        return {"explanation": response, "model": request.model, "language": request.language}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"AI explain error: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate AI explanation")

@api_router.post("/ai/chat")
async def ai_chat(request: AIChatRequest, user: dict = Depends(get_current_user)):
    """Interactive AI chat for medical questions - multi-model, multi-language"""
    question = await db.questions.find_one({"id": request.question_id}, {"_id": 0})
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    
    try:
        lang_instruction = LANG_PROMPTS.get(request.language, LANG_PROMPTS["de"])
        choices = question.get("choices") or question.get("choices_de") or []
        correct_choices = [c.get("text_de") or c.get("text", "") for c in choices if c.get("is_correct")]
        all_choices = "\n".join([f"- {c.get('text_de') or c.get('text', '')} {'✓' if c.get('is_correct') else ''}" for c in choices])
        q_text = question.get("question_text_de") or question.get("question_text", "")
        expl = question.get("explanation_de") or question.get("explanation", "")
        system_message = f"""Du bist ein medizinischer KI-Assistent für die österreichische Prüfungsvorbereitung.
{lang_instruction}
Aktuelle Frage: {q_text}
Antwortmöglichkeiten:\n{all_choices}
Richtige Antworten: {', '.join(correct_choices)}
{f"Offizielle Erklärung: {expl}" if expl else ""}
Regeln: Erkläre medizinische Konzepte klar. Verwende klinische Beispiele. Sei freundlich und ermutigend."""
        response = await _or_text(system_message, request.user_message, max_tokens=800)
        return {"response": response, "model": request.model, "language": request.language}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"AI chat error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get AI response")


# ============ PDF NOTEBOOK (NotebookLM-like) - PREMIUM ============

async def check_notebook_access(user: dict):
    """Check if user has notebook access (admin always has access)"""
    if user.get("is_admin"):
        return True
    u = await db.users.find_one({"id": user["id"]}, {"_id": 0, "notebook_enabled": 1})
    if not u or not u.get("notebook_enabled"):
        raise HTTPException(status_code=403, detail="Notebook-Zugang nicht freigeschaltet. Kontaktieren Sie den Administrator.")
    return True

@api_router.post("/admin/notebook/toggle/{user_id}")
async def toggle_notebook_access(user_id: str, user: dict = Depends(get_current_user)):
    """Admin: Enable/disable notebook access for a user"""
    if not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Nur für Administratoren")
    target = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not target:
        raise HTTPException(status_code=404, detail="Benutzer nicht gefunden")
    new_val = not target.get("notebook_enabled", False)
    await db.users.update_one({"id": user_id}, {"$set": {"notebook_enabled": new_val}})
    return {"user_id": user_id, "notebook_enabled": new_val}

NOTEBOOK_SYSTEM_PROMPT = """Du bist ein erstklassiger medizinischer Lernassistent — wie ein persönlicher Tutor für die österreichische Medizinprüfung (MedAT / SIP).

📄 DOKUMENT: "{filename}"
{doc_text}

═══════════════════════════════════════
DEINE KERNREGELN:
═══════════════════════════════════════

🌐 SPRACHE:
- Standardmäßig antworte in der GLEICHEN SPRACHE wie das Dokument
- Wenn der Benutzer auf Arabisch fragt oder "اشرح بالعربي" sagt → antworte im PRÜFUNGSSTIL (Arabisch + deutsche Fachbegriffe), so:
  • Erkläre auf Arabisch
  • Behalte ALLE medizinischen Fachbegriffe auf Deutsch (z.B. Herzinsuffizienz, Kontusionsherd, Hemiparese)
  • Benutze Emojis für Struktur: 🧠 🔍 ❗ ✅ ❌ 💡 👉
- Wenn auf Deutsch gefragt → antworte auf Deutsch
- Wenn auf Englisch gefragt → antworte auf Englisch

📋 STIL & STRUKTUR (wie ein Top-Tutor):
1. Benutze immer klare Überschriften und Abschnitte
2. Verwende Aufzählungszeichen und Nummerierung
3. Bei Prüfungsfragen: analysiere JEDE Antwort einzeln (✅/❌) mit Begründung
4. Erkläre die klinische Logik Schritt für Schritt
5. Am Ende: "🧠 Goldene Regel" oder "💡 Prüfungstipp" als Zusammenfassung
6. Bei Differentialdiagnosen: tabellarisch vergleichen

🎯 PRÜFUNGSMODUS:
- Wenn der User nach Erklärung einer Frage fragt → benutze das Format:
  🧾 Kurze Zusammenfassung des Falls
  🔍 Klinische Analyse (Schritt für Schritt)
  ⚖️ Analyse jeder Antwortoption (A/B/C/D/E)
  ✅ Richtige Antwort + Begründung
  🧠 Goldene Regel / Prüfungstipp

📚 INHALT:
- Basiere Antworten auf dem Dokumentinhalt
- Du darfst aber dein medizinisches Wissen ergänzen, wenn es hilft
- Sage ehrlich wenn etwas nicht im Dokument steht
- Verknüpfe Konzepte mit klinischer Relevanz
"""

@api_router.post("/notebook/upload")
async def upload_pdf(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    """Upload a PDF, extract text, and split into smart chunks"""
    await check_notebook_access(user)
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Nur PDF-Dateien sind erlaubt")
    
    content = await file.read()
    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Datei zu groß (max 20MB)")
    
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(stream=content, filetype="pdf")
        text_pages = []
        for page in doc:
            text_pages.append(page.get_text())
        full_text = "\n\n".join(text_pages)
        doc.close()
        
        if not full_text.strip():
            raise HTTPException(status_code=400, detail="PDF enthält keinen lesbaren Text")
        
        # Smart chunking: split into sections of ~3000 words each
        words = full_text.split()
        total_words = len(words)
        chunk_size = 3000  # words per chunk
        chunks = []
        
        if total_words <= chunk_size:
            chunks.append({"index": 0, "title": "Gesamtes Dokument", "text": full_text, "word_count": total_words, "page_start": 1, "page_end": len(text_pages)})
        else:
            # Build chunks by pages
            current_chunk_text = ""
            current_chunk_words = 0
            chunk_start_page = 1
            chunk_idx = 0
            
            for page_num, page_text in enumerate(text_pages):
                page_words = len(page_text.split())
                
                if current_chunk_words + page_words > chunk_size and current_chunk_text:
                    # Save current chunk
                    chunks.append({
                        "index": chunk_idx,
                        "title": f"Abschnitt {chunk_idx + 1} (S. {chunk_start_page}-{page_num})",
                        "text": current_chunk_text.strip(),
                        "word_count": current_chunk_words,
                        "page_start": chunk_start_page,
                        "page_end": page_num,
                    })
                    chunk_idx += 1
                    current_chunk_text = page_text + "\n\n"
                    current_chunk_words = page_words
                    chunk_start_page = page_num + 1
                else:
                    current_chunk_text += page_text + "\n\n"
                    current_chunk_words += page_words
            
            # Save last chunk
            if current_chunk_text.strip():
                chunks.append({
                    "index": chunk_idx,
                    "title": f"Abschnitt {chunk_idx + 1} (S. {chunk_start_page}-{len(text_pages)})",
                    "text": current_chunk_text.strip(),
                    "word_count": current_chunk_words,
                    "page_start": chunk_start_page,
                    "page_end": len(text_pages),
                })
        
        notebook_id = str(uuid.uuid4())
        await db.pdf_notebooks.insert_one({
            "id": notebook_id,
            "user_id": user["id"],
            "filename": file.filename,
            "text": full_text[:100000],
            "chunks": chunks,
            "chunk_count": len(chunks),
            "page_count": len(text_pages),
            "word_count": total_words,
            "char_count": len(full_text),
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        # Auto-generate summary + key topics (non-blocking fire-and-forget)
        async def _auto_summary():
            try:
                import json as json_lib
                resp = await _or_text(
                    "Du bist ein medizinischer Experte. Antworte NUR als valides JSON.",
                    f'Analysiere dieses Dokument und antworte NUR als JSON:\n{{"summary": "3-4 Sätze", "topics": ["Thema1"], "suggested_questions": ["Frage1?"]}}\n\nDOKUMENT:\n{full_text[:3000]}',
                    max_tokens=400,
                )
                try:
                    clean = resp.strip()
                    if clean.startswith("```"): clean = clean.split("\n", 1)[1].rsplit("```", 1)[0]
                    auto_data = json_lib.loads(clean)
                except Exception:
                    auto_data = {"summary": "", "topics": [], "suggested_questions": []}
                await db.pdf_notebooks.update_one({"id": notebook_id}, {"$set": {
                    "auto_summary": auto_data.get("summary", ""),
                    "topics": auto_data.get("topics", []),
                    "suggested_questions": auto_data.get("suggested_questions", []),
                }})
            except Exception as e:
                logger.warning(f"Auto-summary error: {e}")
        asyncio.create_task(_auto_summary())
        
        return {
            "id": notebook_id,
            "filename": file.filename,
            "page_count": len(text_pages),
            "word_count": total_words,
            "chunk_count": len(chunks),
            "chunks": [{"index": c["index"], "title": c["title"], "word_count": c["word_count"], "page_start": c["page_start"], "page_end": c["page_end"]} for c in chunks],
            "char_count": len(full_text),
            "preview": full_text[:500]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"PDF upload error: {e}")
        raise HTTPException(status_code=500, detail="Fehler beim Verarbeiten der PDF")

@api_router.get("/notebook/list")
async def list_notebooks(user: dict = Depends(get_current_user)):
    """List user's uploaded PDFs"""
    await check_notebook_access(user)
    notebooks = await db.pdf_notebooks.find(
        {"user_id": user["id"]}, {"_id": 0, "text": 0, "chunks.text": 0}
    ).sort("created_at", -1).to_list(50)
    return notebooks

@api_router.get("/notebook/{notebook_id}")
async def get_notebook(notebook_id: str, user: dict = Depends(get_current_user)):
    """Get notebook details with summary and topics"""
    await check_notebook_access(user)
    nb = await db.pdf_notebooks.find_one(
        {"id": notebook_id, "user_id": user["id"]}, {"_id": 0, "text": 0, "chunks.text": 0}
    )
    if not nb:
        raise HTTPException(status_code=404, detail="Notebook nicht gefunden")
    return nb

@api_router.delete("/notebook/{notebook_id}")
async def delete_notebook(notebook_id: str, user: dict = Depends(get_current_user)):
    """Delete a notebook"""
    await check_notebook_access(user)
    result = await db.pdf_notebooks.delete_one({"id": notebook_id, "user_id": user["id"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Notebook nicht gefunden")
    await db.notebook_chats.delete_many({"notebook_id": notebook_id})
    return {"status": "deleted"}

@api_router.post("/notebook/chat")
async def notebook_chat(request: NotebookChatRequest, user: dict = Depends(get_current_user)):
    """Chat with a PDF document - Smart bilingual medical tutor"""
    await check_notebook_access(user)
    notebook = await db.pdf_notebooks.find_one(
        {"id": request.notebook_id, "user_id": user["id"]}, {"_id": 0}
    )
    if not notebook:
        raise HTTPException(status_code=404, detail="Notebook nicht gefunden")
    
    try:
        doc_text = notebook["text"][:8000]
        # If chunk_index specified, use that chunk
        if request.chunk_index is not None and "chunks" in notebook:
            chunks = notebook.get("chunks", [])
            if 0 <= request.chunk_index < len(chunks):
                doc_text = chunks[request.chunk_index]["text"][:8000]
        system_msg = NOTEBOOK_SYSTEM_PROMPT.format(filename=notebook["filename"], doc_text=doc_text[:6000])

        # Build conversation with history
        history = await db.notebook_chats.find(
            {"notebook_id": request.notebook_id, "user_id": user["id"]}
        ).sort("created_at", -1).to_list(20)
        history.reverse()

        context_msgs = ""
        for h in history[-6:]:
            role = "User" if h["role"] == "user" else "Assistant"
            context_msgs += f"\n{role}: {h['content'][:300]}\n"

        full_message = f"[Chatverlauf:{context_msgs}]\n\nNeue Frage: {request.message}" if context_msgs else request.message
        response = await _or_text(system_msg, full_message, max_tokens=800)
        
        # Save chat
        now = datetime.now(timezone.utc).isoformat()
        await db.notebook_chats.insert_many([
            {"id": str(uuid.uuid4()), "notebook_id": request.notebook_id, "user_id": user["id"],
             "role": "user", "content": request.message, "created_at": now},
            {"id": str(uuid.uuid4()), "notebook_id": request.notebook_id, "user_id": user["id"],
             "role": "assistant", "content": response, "created_at": now}
        ])
        
        return {"response": response}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Notebook chat error: {e}")
        raise HTTPException(status_code=500, detail="AI-Fehler aufgetreten")

@api_router.get("/notebook/{notebook_id}/history")
async def get_notebook_history(notebook_id: str, user: dict = Depends(get_current_user)):
    """Get chat history for a notebook"""
    await check_notebook_access(user)
    messages = await db.notebook_chats.find(
        {"notebook_id": notebook_id, "user_id": user["id"]},
        {"_id": 0}
    ).sort("created_at", 1).to_list(100)
    return messages

@api_router.post("/notebook/{notebook_id}/summarize")
async def summarize_notebook(notebook_id: str, chunk_index: int = -1, language: str = "de", user: dict = Depends(get_current_user)):
    """Auto-summarize the PDF in exam style"""
    await check_notebook_access(user)
    notebook = await db.pdf_notebooks.find_one(
        {"id": notebook_id, "user_id": user["id"]}, {"_id": 0}
    )
    if not notebook:
        raise HTTPException(status_code=404, detail="Notebook nicht gefunden")

    doc_text = notebook["text"][:60000]
    if chunk_index >= 0 and "chunks" in notebook:
        chunks = notebook.get("chunks", [])
        if 0 <= chunk_index < len(chunks):
            doc_text = chunks[chunk_index]["text"]

    LANG_SUM = {"de": "auf Deutsch", "en": "in English", "ar": "باللغة العربية", "ru": "на русском языке", "uk": "українською мовою"}
    lang_str = LANG_SUM.get(language, "auf Deutsch")
    system_msg = f"Du bist ein Experte für medizinische Prüfungsvorbereitung. Antworte {lang_str}."
    prompt = f"""Erstelle eine prüfungsrelevante Zusammenfassung dieses medizinischen Dokuments:

1. 📋 **Zusammenfassung** (5-7 Sätze)
2. 🎯 **Hauptthemen** (als Liste)
3. ⚡ **Prüfungsrelevante Fakten** (die wahrscheinlich in MCQ-Fragen vorkommen)
4. 🧠 **Goldene Regeln** (Merkregeln für die Prüfung)
5. ❓ **Mögliche Prüfungsfragen** (3-5 Beispielfragen die aus diesem Stoff kommen könnten)

DOKUMENT:
{doc_text}"""

    try:
        response = await _or_text(system_msg, prompt, max_tokens=800)
        return {"summary": response}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Summarize error: {e}")
        raise HTTPException(status_code=503, detail="AI nicht verfügbar")

@api_router.post("/notebook/{notebook_id}/generate-mcq")
async def generate_mcq(notebook_id: str, chunk_index: int = -1, language: str = "de", user: dict = Depends(get_current_user)):
    """Generate MCQ questions from the PDF content"""
    await check_notebook_access(user)
    notebook = await db.pdf_notebooks.find_one(
        {"id": notebook_id, "user_id": user["id"]}, {"_id": 0}
    )
    if not notebook:
        raise HTTPException(status_code=404, detail="Notebook nicht gefunden")
    
    try:
        doc_text = notebook["text"][:4000]
        if chunk_index >= 0 and "chunks" in notebook:
            chunks = notebook.get("chunks", [])
            if 0 <= chunk_index < len(chunks):
                doc_text = chunks[chunk_index]["text"][:4000]

        LANG_MCQ = {"de": "auf Deutsch", "en": "in English", "ar": "باللغة العربية", "ru": "на русском языке", "uk": "українською мовою"}
        lang_str = LANG_MCQ.get(language, "auf Deutsch")
        system_msg = f"Du bist ein Experte für medizinische MCQ-Prüfungsfragen. Antworte {lang_str}."
        prompt = f"""Erstelle 5 MCQ-Prüfungsfragen basierend auf diesem Dokument. Format für JEDE Frage:
**Frage X:** [klinisches Szenario]
A) ... B) ... C) ... D) ... E) ...
✅ Richtige Antwort: [Buchstabe]
💡 Erklärung: [kurze Begründung]
---
DOKUMENT:\n{doc_text}"""
        response = await _or_text(system_msg, prompt, max_tokens=800)
        return {"mcq": response}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"MCQ generation error: {e}")
        raise HTTPException(status_code=500, detail="MCQ-Generierung fehlgeschlagen")


@api_router.post("/notebook/{notebook_id}/generate-quiz")
async def generate_quiz_from_notebook(notebook_id: str, count: int = 10, language: str = "de", chunk_index: int = -1, user: dict = Depends(get_current_user)):
    """Start quiz generation as background job to avoid proxy timeout."""
    await check_notebook_access(user)
    notebook = await db.pdf_notebooks.find_one(
        {"id": notebook_id, "user_id": user["id"]}, {"_id": 0}
    )
    if not notebook:
        raise HTTPException(status_code=404, detail="Notebook nicht gefunden")

    count = min(max(count, 3), 50)
    job_id = str(uuid.uuid4())

    # Save job as pending
    await db.quiz_jobs.insert_one({
        "id": job_id, "user_id": user["id"], "notebook_id": notebook_id,
        "status": "processing", "count": count, "language": language,
        "chunk_index": chunk_index,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    # Run in background
    import asyncio
    asyncio.create_task(_run_quiz_generation(job_id, notebook, count, language, chunk_index, user))

    return {"success": True, "job_id": job_id, "status": "processing", "message": "Quiz-Generierung gestartet..."}


@api_router.get("/quiz-job/{job_id}")
async def get_quiz_job_status(job_id: str, user: dict = Depends(get_current_user)):
    """Poll quiz generation job status."""
    job = await db.quiz_jobs.find_one({"id": job_id, "user_id": user["id"]}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Job nicht gefunden")
    return job


async def _run_quiz_generation(job_id: str, notebook: dict, count: int, language: str, chunk_index: int, user: dict):
    """Background task: generate quiz in batches and save results."""
    import json as json_lib, re as _re, httpx
    or_key = os.environ.get("OPENROUTER_API_KEY")
    if not or_key:
        await db.quiz_jobs.update_one({"id": job_id}, {"$set": {"status": "error", "message": "OPENROUTER_API_KEY fehlt"}})
        return

    try:
        doc_text = notebook["text"][:4000]
        if chunk_index >= 0 and "chunks" in notebook:
            chunks = notebook.get("chunks", [])
            if 0 <= chunk_index < len(chunks):
                doc_text = chunks[chunk_index]["text"][:4000]

        LANG_QUIZ = {
            "de": ("auf Deutsch", "Fragetext als klinisches Szenario auf Deutsch", "Kurze Erklärung auf Deutsch", "Alle Texte auf Deutsch"),
            "en": ("in English", "Question text as clinical scenario in English", "Brief explanation in English", "All texts in English"),
            "ar": ("باللغة العربية", "نص السؤال كسيناريو سريري بالعربية", "شرح مختصر بالعربية", "جميع النصوص بالعربية"),
            "ru": ("на русском языке", "Текст вопроса как клинический сценарий на русском", "Краткое объяснение на русском", "Все тексты на русском"),
            "uk": ("українською мовою", "Текст питання як клінічний сценарій українською", "Коротке пояснення українською", "Усі тексти українською"),
        }
        lang_cfg = LANG_QUIZ.get(language, LANG_QUIZ["de"])

        # Generate all questions in a single call (context is limited, keep prompt small)
        batch_size = min(count, 10)
        batches = [(i, min(i + batch_size, count)) for i in range(0, count, batch_size)]
        all_saved = []
        now = datetime.now(timezone.utc).isoformat()
        notebook_id = notebook.get("id", "")

        for batch_idx, (start, end) in enumerate(batches):
            batch_count = end - start
            await db.quiz_jobs.update_one({"id": job_id}, {"$set": {
                "message": f"Batch {batch_idx+1}/{len(batches)}: Generiere Fragen {start+1}-{end}..."
            }})

            already_generated = ""
            if all_saved:
                already_generated = "\n\nBereits generierte Fragen (NICHT wiederholen):\n" + "\n".join([f"- {q['text']}" for q in all_saved[-5:]])

            prompt = f"""Erstelle genau {batch_count} MCQ-Prüfungsfragen basierend auf dem folgenden medizinischen Dokument.

WICHTIG: Antworte NUR mit einem JSON-Array. Kein anderer Text.

Format:
[
  {{
    "question_text": "{lang_cfg[1]}",
    "choices": [
      {{"text": "Option A", "is_correct": false}},
      {{"text": "Option B", "is_correct": false}},
      {{"text": "Option C", "is_correct": true}},
      {{"text": "Option D", "is_correct": false}},
      {{"text": "Option E", "is_correct": false}}
    ],
    "explanation": "{lang_cfg[2]}"
  }}
]

Regeln:
- Genau {batch_count} Fragen
- Genau 5 Antwortoptionen pro Frage (A-E)
- Genau 1 richtige Antwort pro Frage
- Klinische Szenarien wenn möglich
- {lang_cfg[3]}
- Antworte NUR mit dem JSON-Array, KEIN anderer Text
{already_generated}

DOKUMENT:
{doc_text}"""

            async with httpx.AsyncClient(timeout=55.0) as client:
                r = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={"Authorization": f"Bearer {or_key}", "Content-Type": "application/json",
                             "HTTP-Referer": "https://mcq-medical-prep.academy", "X-Title": "PrepAcademy"},
                    json={"model": "openai/gpt-oss-120b:free",
                          "messages": [{"role": "system", "content": f"Du bist ein Experte für medizinische MCQ-Prüfungsfragen. Antworte NUR als valides JSON-Array. Erstelle Fragen {lang_cfg[0]}."},
                                        {"role": "user", "content": prompt}],
                          "max_tokens": 1200, "temperature": 0.4},
                )
                rd = r.json()
            if "choices" not in rd or not rd["choices"]:
                logger.warning(f"Quiz batch {batch_idx} no choices: {str(rd)[:200]}")
                continue
            response = rd["choices"][0]["message"]["content"] or ""
            response = _re.sub(r"<think>.*?</think>", "", response, flags=_re.DOTALL).strip()

            # Parse JSON from response
            json_str = response.strip()
            if json_str.startswith("```"):
                json_str = json_str.split("```")[1]
                if json_str.startswith("json"):
                    json_str = json_str[4:]
                json_str = json_str.strip()

            try:
                questions_data = json_lib.loads(json_str)
                if not isinstance(questions_data, list):
                    continue
            except json_lib.JSONDecodeError:
                logger.error(f"Quiz batch {batch_idx} JSON parse error")
                continue

            for q_data in questions_data:
                q_text = q_data.get("question_text", "").strip()
                if not q_text:
                    continue
                choices_raw = q_data.get("choices", [])
                if len(choices_raw) < 2:
                    continue

                choices = []
                for j, c in enumerate(choices_raw):
                    choices.append({
                        "id": str(j + 1),
                        "text": c.get("text", ""),
                        "text_de": c.get("text", ""),
                        "is_correct": bool(c.get("is_correct", False))
                    })

                has_correct = any(c["is_correct"] for c in choices)
                if not has_correct:
                    choices[0]["is_correct"] = True

                question_id = str(uuid.uuid4())
                question_doc = {
                    "id": question_id,
                    "specialty_id": "special",
                    "year": datetime.now(timezone.utc).year,
                    "question_text": q_text,
                    "question_text_de": q_text,
                    "choices": choices,
                    "explanation": q_data.get("explanation", ""),
                    "explanation_de": q_data.get("explanation", ""),
                    "exam_location": "vienna",
                    "created_at": now,
                    "source": "notebook",
                    "notebook_id": notebook_id,
                    "notebook_filename": notebook.get("filename", ""),
                    "generated_by": user["id"],
                }
                await db.questions.insert_one(question_doc)
                all_saved.append({"id": question_id, "text": q_text[:100]})

        # Update specialty question count cache
        special_count = await db.questions.count_documents({"specialty_id": "special"})
        await db.specialties.update_one({"id": "special"}, {"$set": {"question_count": special_count}})

        await db.quiz_jobs.update_one({"id": job_id}, {"$set": {
            "status": "done",
            "count": len(all_saved),
            "questions": all_saved,
            "message": f"{len(all_saved)} Fragen wurden erfolgreich generiert und gespeichert."
        }})
    except Exception as e:
        logger.error(f"Quiz generation error: {e}")
        await db.quiz_jobs.update_one({"id": job_id}, {"$set": {"status": "error", "message": f"Quiz-Generierung fehlgeschlagen: {str(e)[:200]}"}})



# ============ MEDICAL REPORT ANALYZER - PREMIUM ============

async def check_analyzer_access(user: dict):
    """Check if user has analyzer access (admin always has access)"""
    if user.get("is_admin"):
        return True
    u = await db.users.find_one({"id": user["id"]}, {"_id": 0, "analyzer_enabled": 1})
    if not u or not u.get("analyzer_enabled"):
        raise HTTPException(status_code=403, detail="Analyzer-Zugang nicht freigeschaltet. Kontaktieren Sie den Administrator.")
    return True


@api_router.get("/analyzer/access")
async def get_analyzer_access(user: dict = Depends(get_current_user)):
    """Check if current user has analyzer access"""
    try:
        await check_analyzer_access(user)
        return {"access": True}
    except HTTPException:
        raise

@api_router.post("/admin/analyzer/toggle/{user_id}")
async def toggle_analyzer_access(user_id: str, user: dict = Depends(get_current_user)):
    """Admin: Enable/disable analyzer access for a user"""
    if not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Nur für Administratoren")
    target = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not target:
        raise HTTPException(status_code=404, detail="Benutzer nicht gefunden")
    new_val = not target.get("analyzer_enabled", False)
    await db.users.update_one({"id": user_id}, {"$set": {"analyzer_enabled": new_val}})
    return {"user_id": user_id, "analyzer_enabled": new_val}

ANALYZER_SPECIALISTS = {
    "ECG": """Du bist ein erfahrener Kardiologe und EKG-Spezialist.
Analysiere das EKG systematisch:
1. RHYTHMUS: Sinusrhythmus? Vorhofflimmern? Regelmäßig/unregelmäßig?
2. FREQUENZ: Bradykardie (<60), Normal (60-100), Tachykardie (>100)?
3. ACHSE: Normal (-30° bis +90°), Linkstyp, Rechtstyp, überdrehter Typ?
4. P-WELLEN: Morphologie, Dauer, P-mitrale, P-pulmonale?
5. PQ-INTERVALL: Normal (120-200ms), AV-Block I/II/III?
6. QRS-KOMPLEX: Dauer (<120ms normal), Schenkelblock, Hypertrophie?
7. ST-STRECKE: Hebungen (STEMI!), Senkungen, Lokalisation?
8. T-WELLEN: Normal, invertiert, spitz (Hyperkaliämie)?
9. QTc-ZEIT: Verlängert (>440ms Männer, >460ms Frauen)?
10. PATHOLOGISCHE Q-ZACKEN: Alter Infarkt?
Bewerte die klinische Dringlichkeit (Notfall bei STEMI, VT, kompletter AV-Block).""",

    "CT": """Du bist ein erfahrener Radiologe für CT-Diagnostik.
Systematische CT-Analyse:
1. TECHNIK: Nativ/KM, Schichtdicke, Fensterung
2. PARENCHYM: Dichtemessungen (HU), fokale Läsionen, Verkalkungen
3. GEFÄßE: Aneurysmen, Stenosen, Thrombosen, Lungenembolie
4. LYMPHKNOTEN: Größe, Lokalisation, pathologisch >1cm
5. KNOCHEN: Frakturen, Lysen, Sklerosierung
6. WEICHTEILE: Raumforderungen, Flüssigkeit, Abszesse
7. ORGANE: Größe, Parenchymstruktur, Kontrastmittelverhalten
8. FREIE LUFT/FLÜSSIGKEIT: Pneumoperitoneum, Aszites, Pleuraerguss
Verwende Hounsfield-Einheiten (HU) für Dichtemessungen.""",

    "MRI": """Du bist ein erfahrener Neuroradiologe und MRT-Spezialist.
Systematische MRT-Analyse:
1. SEQUENZEN: T1, T2, FLAIR, DWI/ADC, T1+KM, SWI
2. SIGNALCHARAKTERISTIK: hypo/iso/hyperintens in jeder Sequenz
3. DWI: Diffusionsrestriktion? (frischer Infarkt, Abszess)
4. KONTRASTMITTEL: Anreicherungsmuster (ringförmig, homogen, inhomogen)
5. RAUMFORDERUNG: Größe, Lokalisation, Masseneffekt, Ödem
6. GEFÄSSE: MRA-Befunde, Stenosen, Aneurysmen
7. VENTRIKEL: Größe, Hydrocephalus
8. MYELON: Signalveränderungen, Kompression""",

    "BloodTest": """Du bist ein erfahrener Labormediziner und klinischer Pathologe.
Systematische Blutbildanalyse:
1. BLUTBILD: Hb, Hkt, MCV, MCH, MCHC, RDW → Anämietyp
2. LEUKOZYTEN: Differentialblutbild, Linksverschiebung, Leukozytose/Leukopenie
3. THROMBOZYTEN: Thrombozytopenie/Thrombozytose, Ursachen
4. GERINNUNG: INR, PTT, Fibrinogen, D-Dimere
5. ELEKTROLYTE: Na, K, Ca, Mg, Phosphat → Klinische Bedeutung
6. NIERENWERTE: Kreatinin, GFR, Harnstoff, Harnsäure
7. LEBERWERTE: GOT, GPT, GGT, AP, Bilirubin, Albumin → Schädigungsmuster
8. ENTZÜNDUNG: CRP, PCT, BSG, Ferritin, IL-6
9. SCHILDDRÜSE: TSH, fT3, fT4
10. LIPIDE: Cholesterin, LDL, HDL, Triglyceride
Markiere JEDEN pathologischen Wert mit ↑ oder ↓ und dem Referenzbereich.""",

    "XRay": """Du bist ein erfahrener Radiologe für konventionelle Röntgendiagnostik.
Systematische Röntgenanalyse:
1. THORAX: Herzsilhouette (CTR), Mediastinum, Lungenhili, Pleurawinkel
2. LUNGE: Infiltrate, Rundherde, Verschattungen, Überblähung
3. KNOCHEN: Frakturen (Typ, Dislokation), Osteolysen, Arthrose
4. GELENKE: Gelenkspalt, Osteophyten, Erosionen, Kalzifikationen
5. ABDOMEN: Spiegelbildung, freie Luft, Ileus-Zeichen
6. WEICHTEILE: Schwellung, Fremdkörper, Verkalkungen
Bei Thorax: Qualitätskriterien (Rotation, Inspiration, Penetration).""",

    "Ultrasound": """Du bist ein erfahrener Sonographie-Spezialist.
Systematische Ultraschallanalyse:
1. LEBER: Größe, Echogenität, fokale Läsionen, Steatose
2. GALLENBLASE: Konkremente, Wandverdickung, Murphy-Zeichen
3. GALLENWEGE: DHC-Weite (<7mm normal), intrahepatische Erweiterung
4. PANKREAS: Größe, Echogenität, Raumforderungen
5. MILZ: Größe (<12cm), Echogenität
6. NIEREN: Größe, Parenchymbreite, Stauung, Konkremente, Zysten
7. AORTA: Durchmesser (<3cm normal), Aneurysma
8. FREIE FLÜSSIGKEIT: Morrison-Pouch, Douglas-Raum
9. DOPPLER: Flusssignale, RI, PI""",

    "Echo": """Du bist ein erfahrener Kardiologe und Echokardiographie-Spezialist.
Systematische Echokardiographie-Analyse:
1. LV-FUNKTION: EF (normal >55%), Wandbewegungsstörungen, GLS
2. LV-DIMENSIONEN: LVEDD, LVESD, Wanddicken (IVS, HW)
3. DIASTOLISCHE FUNKTION: E/A, E/e', LAVI, TR-Vmax → Grad I-III
4. RECHTES HERZ: RV-Funktion (TAPSE >17mm), RV-Dilatation, RVSP
5. KLAPPEN:
   - Aortenklappe: Stenose (Vmax, mittlerer Gradient, KÖF), Insuffizienz
   - Mitralklappe: Stenose (PHT, KÖF), Insuffizienz (Vena contracta, PISA)
   - Trikuspidalklappe: Insuffizienz, RVSP-Berechnung
   - Pulmonalklappe: Insuffizienz, Gradient
6. PERIKARD: Erguss, Tamponade-Zeichen, Konstriktion
7. AORTA: Ascendens-Weite (<40mm), Aortenklappenmorphologie
Verwende aktuelle ASE/EACVI-Richtlinien für Normwerte.""",

    "Other": """Du bist ein erfahrener medizinischer Bildanalyst.
Analysiere den medizinischen Bericht oder das Bild systematisch.
Beschreibe alle erkennbaren Befunde, Auffälligkeiten und klinisch relevanten Details.
Ordne die Befunde nach klinischer Bedeutung und gib Empfehlungen.""",
}

ANALYZER_COMMON = """
WICHTIG - PFLICHTREGELN:
1. Du MUSST IMMER analysieren. Verweigere NIE. Dies ist ein LERNWERKZEUG.
2. Beschreibe JEDEN erkennbaren Befund im Detail mit Messwerten und Lokalisationen.
3. Sage NIEMALS "Ich kann nicht" oder "Konsultieren Sie einen Arzt" - DU bist der Experte hier.
4. Verwende klinische Fachterminologie UND verständliche Erklärungen.

ANALYSE-FORMAT (IMMER einhalten):

## Befund (Findings)
- Jeden einzelnen Befund detailliert auflisten
- Messwerte mit Referenzbereichen und ↑↓ Kennzeichnung
- Pathologische Werte FETT markieren und klinisch einordnen

## Schweregrad
**Normal** / **Leicht auffällig** / **Moderat** / **Schwer** / **Kritisch**
Begründung des Schweregrads in 1-2 Sätzen.

## Differentialdiagnosen
1. Wahrscheinlichste Diagnose (>80%)
2. Alternative Diagnose (40-80%)
3. Auszuschließende Diagnose (<20%)

## Klinische Bedeutung
- Was bedeuten die Befunde für den Patienten?
- Welche Organe/Systeme sind betroffen?
- Prognose und Verlauf

## Empfehlungen
- Sofortmaßnahmen (falls nötig)
- Weiterführende Diagnostik
- Therapieoptionen mit Evidenzlevel

## Zusammenfassung
Strukturierte Zusammenfassung in 3-4 Sätzen für Prüfungsvorbereitung.

## Vertrauen: [X]%

QUALITÄTSREGELN:
- IMMER auf Deutsch mit korrekter Terminologie
- "vereinbar mit..." statt definitive Diagnosen
- Bei Arabisch-Anfrage: Arabisch + deutsche Fachbegriffe in Klammern
- Mindestens 800 Wörter pro Analyse
"""

@api_router.post("/analyzer/analyze-upload")
async def analyze_medical_report_upload(
    files: list[UploadFile] = File(...),
    report_type: str = Form("Other"),
    clinical_context: str = Form(""),
    user: dict = Depends(get_current_user),
):
    """Multipart upload version — handles large medical images reliably (no JSON base64 overhead)."""
    await check_analyzer_access(user)

    if not os.environ.get("OPENROUTER_API_KEY"):
        raise HTTPException(status_code=500, detail="AI service not configured")

    if not files:
        raise HTTPException(status_code=400, detail="Kein Bild hochgeladen")

    # Read each file, convert to base64 server-side (no proxy size limits)
    all_images = []
    for f in files[:10]:
        raw = await f.read()
        if len(raw) == 0:
            continue
        import base64 as _b64
        all_images.append(_b64.b64encode(raw).decode("ascii"))

    if not all_images:
        raise HTTPException(status_code=400, detail="Kein gültiges Bild erhalten")

    job_id = str(uuid.uuid4())
    await db.analyzer_jobs.insert_one({
        "id": job_id,
        "user_id": user["id"],
        "status": "processing",
        "report_type": report_type,
        "image_count": len(all_images),
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    asyncio.create_task(_run_analyzer_job(job_id, user, all_images, report_type, clinical_context or ""))

    return {"job_id": job_id, "status": "processing"}


@api_router.post("/analyzer/analyze")
async def analyze_medical_report(request: AnalyzeRequest, user: dict = Depends(get_current_user)):
    """Start multi-AI analysis as a background job (returns job_id for polling)."""
    await check_analyzer_access(user)

    if not os.environ.get("OPENROUTER_API_KEY"):
        raise HTTPException(status_code=500, detail="AI service not configured")

    # Collect images
    all_images = []
    if request.images and len(request.images) > 0:
        for img in request.images[:10]:
            b64 = img.split(",", 1)[1] if "," in img else img
            all_images.append(b64)
    elif request.image_base64:
        b64 = request.image_base64
        if "," in b64:
            b64 = b64.split(",", 1)[1]
        all_images.append(b64)

    if not all_images:
        raise HTTPException(status_code=400, detail="Kein Bild hochgeladen")

    job_id = str(uuid.uuid4())
    await db.analyzer_jobs.insert_one({
        "id": job_id,
        "user_id": user["id"],
        "status": "processing",
        "report_type": request.report_type,
        "image_count": len(all_images),
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    asyncio.create_task(_run_analyzer_job(job_id, user, all_images, request.report_type, request.clinical_context or ""))

    return {"job_id": job_id, "status": "processing"}


@api_router.get("/analyzer/job/{job_id}")
async def get_analyzer_job(job_id: str, user: dict = Depends(get_current_user)):
    """Poll the status of a multi-AI analysis job."""
    job = await db.analyzer_jobs.find_one({"id": job_id, "user_id": user["id"]}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Job nicht gefunden")
    return job


async def _openrouter_vision_call(model: str, system_msg: str, user_text: str, images_b64: list, max_tokens: int = 2500) -> str | None:
    """Call OpenRouter chat/completions with vision content. Returns text or None on failure."""
    or_key = os.environ.get("OPENROUTER_API_KEY")
    if not or_key:
        return None
    try:
        import httpx
        content = [{"type": "text", "text": user_text}]
        for b64 in images_b64[:6]:  # cap to 6 images per call
            content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}})
        async with httpx.AsyncClient(timeout=120.0) as client:
            r = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {or_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://mcq-medical-prep.academy",
                    "X-Title": "PrepAcademy Medical Analyzer",
                },
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_msg},
                        {"role": "user", "content": content},
                    ],
                    "max_tokens": max_tokens,
                    "temperature": 0.3,
                },
            )
            data = r.json()
            if "choices" in data and data["choices"]:
                return data["choices"][0]["message"]["content"]
            logger.warning(f"OpenRouter {model} no choices: {str(data)[:300]}")
            return None
    except Exception as e:
        logger.warning(f"OpenRouter {model} failed: {e}")
        return None


_ANALYZER_MODEL_LABELS = {
    "google/gemma-4-31b-it:free":          "Gemma 4 31B (Google)",
    "nvidia/nemotron-nano-12b-v2-vl:free": "Nemotron 12B VL (NVIDIA)",
    "baidu/qianfan-ocr-fast:free":         "Qianfan OCR (Baidu)",
    "google/gemma-4-26b-a4b-it:free":      "Gemma 4 26B (Google)",
}

_SECOND_OPINION_FALLBACKS = [
    "nvidia/nemotron-nano-12b-v2-vl:free",
    "google/gemma-4-26b-a4b-it:free",
    "baidu/qianfan-ocr-fast:free",
]

_CATEGORY_KEYWORDS = {
    "ECG":       ["EKG", "QRS", "P-Welle", "Sinusrhythmus", "Vorhofflimmern", "Herzrhythmus", "RR-Intervall", "ST", "QT", "T-Welle", "Herzfrequenz"],
    "XRay":      ["Röntgen", "Thorax", "Lunge", "Pneumonie", "Atelektase", "Pleura", "Kardiomegalie", "Hilus", "Zwerchfell"],
    "CT":        ["CT", "Computertomographie", "Hounsfield", "Densität", "Schnitt", "axial", "koronal", "sagittal"],
    "MRI":       ["MRT", "Magnetresonanz", "T1", "T2", "FLAIR", "Sequenz", "Signalveränderung", "Hyperintens"],
    "Ultrasound":["Ultraschall", "Sonographie", "Echostruktur", "hyperechogen", "hypoechogen", "Schallschatten"],
    "BloodTest": ["Hämoglobin", "Leukozyten", "Thrombozyten", "CRP", "Kreatinin", "GOT", "GPT", "Elektrolyt"],
    "Echo":      ["Echokardiographie", "Ejektionsfraktion", "Wandbewegung", "Mitral", "Aorta", "Perikard", "LVEF"],
}

async def _run_analyzer_job(job_id: str, user: dict, all_images: list, report_type: str, clinical_context: str):
    """
    Multi-AI medical analysis — free vision models with fallback chain.
    Primary: google/gemma-4-31b-it:free
    Second:  nvidia/nemotron-nano-12b-v2-vl:free → gemma-4-26b → qianfan (fallback chain)
    Third:   baidu/qianfan-ocr-fast:free
    """
    try:
        specialist_prompt = ANALYZER_SPECIALISTS.get(report_type, ANALYZER_SPECIALISTS["Other"])
        system_msg = specialist_prompt + ANALYZER_COMMON

        context_text = ""
        if clinical_context.strip():
            context_text = f"\n\nKlinischer Kontext / Patientenanamnese:\n{clinical_context.strip()}\n\n"

        img_count_text = f" ({len(all_images)} Bilder)" if len(all_images) > 1 else ""
        main_prompt = f"""Analysiere {"diese" if len(all_images) > 1 else "dieses"} medizinische{"n" if len(all_images) > 1 else ""} {"Bilder/Befunde" if len(all_images) > 1 else "Bild/Befund"} ({report_type}){img_count_text} vollständig und detailliert.
{f"Es sind {len(all_images)} Bilder - analysiere ALLE zusammen und erstelle einen Gesamtbefund." if len(all_images) > 1 else ""}
{context_text}
WICHTIG: Du MUSST eine vollständige strukturierte Analyse liefern in DEUTSCHER Sprache.
Beschreibe ALLES was du in {"allen Bildern" if len(all_images) > 1 else "dem Bild"} erkennst.
Verweigere die Analyse NICHT. Dies ist ein Lernwerkzeug für Medizinstudenten.
Gib deine beste fachliche Einschätzung als erfahrener Facharzt.
Strukturiere die Antwort in: Befund, Interpretation, Differentialdiagnosen, Empfehlungen, Zusammenfassung."""

        primary_role = "Du bist ein erfahrener Facharzt (Prep Academy Medical AI) mit Spezialisierung auf Bildgebung und Befundinterpretation. Antworte IMMER auf Deutsch."
        second_role  = "Du bist ein zweiter unabhängiger Facharzt (Prep Academy Medical AI). Arbeite besonders sorgfältig bei Differentialdiagnosen. Antworte IMMER auf Deutsch."
        third_role   = "Du bist ein dritter Facharzt mit Zugang zu aktuellen Leitlinien (ESC, DGK, AWMF, WHO). Fokus auf evidenzbasierte Medizin. Antworte IMMER auf Deutsch."

        # Run primary + third in parallel; second uses fallback chain
        primary_model_id = "google/gemma-4-31b-it:free"
        third_model_id   = "baidu/qianfan-ocr-fast:free"
        results = await asyncio.gather(
            _openrouter_vision_call(primary_model_id, primary_role + "\n\n" + system_msg, main_prompt, all_images, 1500),
            _openrouter_vision_call(third_model_id,   third_role   + "\n\n" + system_msg, main_prompt, all_images, 1500),
            return_exceptions=True,
        )
        primary_analysis = results[0] if isinstance(results[0], str) and (results[0] or "").strip() else None
        third_opinion    = results[1] if isinstance(results[1], str) and (results[1] or "").strip() else None
        primary_model_used = _ANALYZER_MODEL_LABELS[primary_model_id] if primary_analysis else None
        third_model_used   = _ANALYZER_MODEL_LABELS[third_model_id]   if third_opinion   else None

        # Refusal fallback for primary
        refusal_markers = ["kann ich nicht", "kann das nicht", "Es tut mir leid", "nicht möglich", "nicht analysieren", "nicht in der Lage", "I cannot", "I can't"]
        if primary_analysis and any(m in primary_analysis[:200] for m in refusal_markers):
            fb = await _openrouter_vision_call(
                "nvidia/nemotron-nano-12b-v2-vl:free",
                "Du bist ein medizinischer Lernassistent. Beschreibe IMMER was sichtbar ist. Verweigere NIE.",
                f"Analysiere {'diese medizinischen Bilder' if len(all_images) > 1 else 'dieses medizinische Bild'} ({report_type}) auf Deutsch.\n{context_text}\nStrukturierte Analyse: Befund, Interpretation, Differentialdiagnosen, Empfehlungen.",
                all_images, 1200,
            )
            if fb and fb.strip():
                primary_analysis = fb
                primary_model_used = _ANALYZER_MODEL_LABELS["nvidia/nemotron-nano-12b-v2-vl:free"]

        # Second opinion — fallback chain: nemotron → gemma-4-26b → qianfan
        second_opinion = None
        second_model_used = None
        used_for_third = {third_model_id}  # don't reuse third model as second
        for fb_model in _SECOND_OPINION_FALLBACKS:
            if fb_model in used_for_third:
                continue
            fb_result = await _openrouter_vision_call(
                fb_model, second_role + "\n\n" + system_msg, main_prompt, all_images, 1500
            )
            if fb_result and fb_result.strip():
                second_opinion = fb_result
                second_model_used = _ANALYZER_MODEL_LABELS.get(fb_model, fb_model)
                break

        # Promote second to primary if primary failed
        if not primary_analysis:
            if second_opinion:
                primary_analysis, primary_model_used = second_opinion, second_model_used
                second_opinion, second_model_used = third_opinion, third_model_used
                third_opinion, third_model_used = None, None
            elif third_opinion:
                primary_analysis, primary_model_used = third_opinion, third_model_used
                third_opinion, third_model_used = None, None

        if not primary_analysis:
            await db.analyzer_jobs.update_one({"id": job_id}, {"$set": {
                "status": "error",
                "message": "Alle KI-Modelle konnten das Bild nicht analysieren. Bitte versuche es mit einem klareren Bild erneut."
            }})
            return

        # ── Category mismatch detection ──
        category_warning = None
        if report_type in _CATEGORY_KEYWORDS:
            keywords = _CATEGORY_KEYWORDS[report_type]
            found = sum(1 for kw in keywords if kw.lower() in primary_analysis.lower())
            if found < 2:  # fewer than 2 expected keywords → likely wrong type
                category_warning = (
                    f"⚠️ **Hinweis:** Die Analyse enthält wenige {report_type}-typische Befunde. "
                    f"Bitte überprüfe, ob der gewählte Untersuchungstyp ({report_type}) korrekt ist.\n\n"
                )

        # ── Confidence score (based on # of AI models that responded) ──
        ai_count = sum(1 for x in [primary_analysis, second_opinion, third_opinion] if x)
        confidence_score = {1: 55, 2: 72, 3: 85}.get(ai_count, 55)

        # Build models_used list for frontend display
        models_used = []
        if primary_model_used:   models_used.append({"role": "Erstanalyse",   "model": primary_model_used})
        if second_model_used:    models_used.append({"role": "Zweitmeinung",  "model": second_model_used})
        if third_model_used:     models_used.append({"role": "Drittmeinung", "model": third_model_used})

        # Build analysis text
        warning_prefix = category_warning or ""
        full_analysis = f"{warning_prefix}## Erstanalyse — {primary_model_used}\n{primary_analysis}"
        if second_opinion:
            full_analysis += f"\n\n---\n\n## Zweitmeinung — {second_model_used}\n{second_opinion}"
        if third_opinion:
            full_analysis += f"\n\n---\n\n## Drittmeinung — {third_model_used}\n{third_opinion}"

        analysis_id = str(uuid.uuid4())
        analysis_doc = {
            "id": analysis_id,
            "user_id": user["id"],
            "report_type": report_type,
            "analysis": full_analysis,
            "has_second_opinion": bool(second_opinion),
            "has_third_opinion": bool(third_opinion),
            "ai_count": ai_count,
            "confidence_score": confidence_score,
            "models_used": models_used,
            "image_count": len(all_images),
            "image_preview": all_images[0][:200] + "..." if all_images else "",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.analyses.insert_one(analysis_doc)

        await db.analyzer_jobs.update_one({"id": job_id}, {"$set": {
            "status": "done",
            "result": {
                "id": analysis_id,
                "analysis": full_analysis,
                "report_type": report_type,
                "has_second_opinion": bool(second_opinion),
                "has_third_opinion": bool(third_opinion),
                "ai_count": ai_count,
                "confidence_score": confidence_score,
                "models_used": models_used,
            }
        }})
    except Exception as e:
        logger.error(f"Analyzer job {job_id} error: {e}")
        await db.analyzer_jobs.update_one({"id": job_id}, {"$set": {
            "status": "error",
            "message": f"Analyse fehlgeschlagen: {str(e)[:200]}"
        }})

@api_router.get("/analyzer/history")
async def get_analysis_history(user: dict = Depends(get_current_user)):
    """Get user's analysis history"""
    await check_analyzer_access(user)
    analyses = await db.analyses.find(
        {"user_id": user["id"]},
        {"_id": 0, "id": 1, "report_type": 1, "analysis": 1, "created_at": 1}
    ).sort("created_at", -1).to_list(50)
    return analyses

@api_router.delete("/analyzer/{analysis_id}")
async def delete_analysis(analysis_id: str, user: dict = Depends(get_current_user)):
    """Delete an analysis"""
    result = await db.analyses.delete_one({"id": analysis_id, "user_id": user["id"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Analyse nicht gefunden")
    return {"message": "Analyse gelöscht"}

@api_router.get("/analyzer/{analysis_id}/pdf")
async def export_analysis_pdf(analysis_id: str, user: dict = Depends(get_current_user)):
    """Export an analysis as a styled PDF report"""
    try:
        from fpdf import FPDF
    except ImportError:
        raise HTTPException(status_code=500, detail="PDF-Bibliothek nicht installiert (fpdf2)")
    import io
    import re as _re

    analysis = await db.analyses.find_one(
        {"id": analysis_id, "user_id": user["id"]},
        {"_id": 0}
    )
    if not analysis:
        raise HTTPException(status_code=404, detail="Analyse nicht gefunden")

    report_type = analysis.get("report_type", "Unbekannt")
    text = analysis.get("analysis", "")
    created = analysis.get("created_at", "")
    if created:
        try:
            from datetime import datetime as _dt
            dt = _dt.fromisoformat(created.replace("Z", "+00:00"))
            date_str = dt.strftime("%d.%m.%Y %H:%M")
        except Exception:
            date_str = created[:16]
    else:
        date_str = "—"

    type_names = {
        "ECG": "EKG — Elektrokardiogramm",
        "CT": "CT — Computertomographie",
        "MRI": "MRT — Magnetresonanztomographie",
        "BloodTest": "Blutbild — Laborergebnisse",
        "XRay": "Röntgen — Röntgenaufnahme",
        "Ultrasound": "Ultraschall — Sonographie",
    }

    class MedPDF(FPDF):
        def __init__(self):
            super().__init__()
            font_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
            self._use_unicode = False
            try:
                if os.path.exists(os.path.join(font_dir, "DejaVuSans.ttf")):
                    self.add_font("DejaVu", "", os.path.join(font_dir, "DejaVuSans.ttf"), uni=True)
                    self.add_font("DejaVu", "B", os.path.join(font_dir, "DejaVuSans-Bold.ttf"), uni=True)
                    self.add_font("DejaVu", "I", os.path.join(font_dir, "DejaVuSans-Oblique.ttf"), uni=True)
                    self._use_unicode = True
            except Exception:
                self._use_unicode = False

        def _f(self, style=""):
            return "DejaVu" if self._use_unicode else "Helvetica"

        def _safe(self, text):
            if self._use_unicode:
                return text
            replacements = {
                "\u00e4": "ae", "\u00f6": "oe", "\u00fc": "ue", "\u00df": "ss",
                "\u00c4": "Ae", "\u00d6": "Oe", "\u00dc": "Ue",
                "\u2014": "-", "\u2013": "-", "\u2026": "...",
                "\u201e": '"', "\u201c": '"', "\u201d": '"',
                "\u2018": "'", "\u2019": "'",
                "\u2022": "-", "\u00b0": " Grad",
            }
            for k, v in replacements.items():
                text = text.replace(k, v)
            return text.encode("latin-1", "replace").decode("latin-1")

        def header(self):
            self.set_font(self._f(), "B", 18)
            self.set_text_color(8, 145, 178)
            self.cell(0, 10, "Prep Academy", new_x="LMARGIN", new_y="NEXT")
            self.set_font(self._f(), "", 9)
            self.set_text_color(120, 120, 120)
            self.cell(0, 5, self._safe("KI-gest\u00fctzte medizinische Befundanalyse"), new_x="LMARGIN", new_y="NEXT")
            self.line(10, self.get_y() + 3, 200, self.get_y() + 3)
            self.ln(8)

        def footer(self):
            self.set_y(-25)
            self.set_draw_color(200, 200, 200)
            self.line(10, self.get_y(), 200, self.get_y())
            self.ln(3)
            self.set_font(self._f(), "I", 7)
            self.set_text_color(140, 140, 140)
            self.multi_cell(0, 3.5, self._safe(
                "Hinweis: Diese KI-Analyse dient ausschlie\u00dflich als klinisches Entscheidungshilfemittel. "
                "Die \u00e4rztliche Beurteilung hat stets Vorrang. Keine eigenst\u00e4ndige Diagnosestellung."
            ), align="C")
            self.set_font(self._f(), "", 7)
            self.cell(0, 4, f"Seite {self.page_no()}/{{nb}}", align="C")

    pdf = MedPDF()
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=30)
    pdf.add_page()

    # Report type & date box
    pdf.set_fill_color(240, 249, 250)
    pdf.set_draw_color(8, 145, 178)
    pdf.rect(10, pdf.get_y(), 190, 18, style="DF")
    y_box = pdf.get_y()
    pdf.set_xy(15, y_box + 2)
    pdf.set_font(pdf._f(), "B", 12)
    pdf.set_text_color(8, 145, 178)
    pdf.cell(120, 7, pdf._safe(type_names.get(report_type, report_type)))
    pdf.set_font(pdf._f(), "", 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 7, date_str, align="R")
    pdf.set_xy(15, y_box + 10)
    pdf.set_font(pdf._f(), "", 8)
    pdf.set_text_color(120, 120, 120)
    pdf.cell(0, 5, f"Analyse-ID: {analysis_id[:12]}...")
    pdf.set_y(y_box + 22)

    # Parse markdown sections
    sections = _re.split(r'^## ', text, flags=_re.MULTILINE)
    for section in sections:
        if not section.strip():
            continue
        lines = section.split("\n", 1)
        title = lines[0].strip()
        body = lines[1].strip() if len(lines) > 1 else ""

        # Section heading
        pdf.set_font(pdf._f(), "B", 11)
        pdf.set_text_color(8, 145, 178)
        pdf.cell(0, 8, pdf._safe(title), new_x="LMARGIN", new_y="NEXT")
        pdf.set_draw_color(8, 145, 178)
        pdf.line(10, pdf.get_y(), 80, pdf.get_y())
        pdf.ln(2)

        # Section body
        pdf.set_font(pdf._f(), "", 9)
        pdf.set_text_color(40, 40, 40)
        for line in body.split("\n"):
            line = line.strip()
            if not line:
                pdf.ln(2)
                continue
            # Bold markers
            clean = _re.sub(r'\*\*(.*?)\*\*', r'\1', line)
            if line.startswith("- "):
                clean = clean[2:]
                pdf.cell(5, 5, pdf._safe(chr(8226)))
                pdf.multi_cell(0, 5, pdf._safe(f" {clean}"))
            elif line.startswith("Rate:") or line.startswith("**"):
                pdf.set_font(pdf._f(), "B", 9)
                pdf.multi_cell(0, 5, pdf._safe(clean))
                pdf.set_font(pdf._f(), "", 9)
            else:
                pdf.multi_cell(0, 5, pdf._safe(clean))
        pdf.ln(3)

    # Generate PDF bytes
    buf = io.BytesIO()
    pdf.output(buf)
    buf.seek(0)

    filename = f"Analyse_{report_type}_{date_str.replace('.', '-').replace(':', '-').replace(' ', '_')}.pdf"
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


# ============ DASHBOARD ROUTES ============

@api_router.get("/dashboard/stats")
async def get_dashboard_stats(user: dict = Depends(get_current_user)):
    """Get comprehensive dashboard statistics for a user"""
    user_id = user["id"]
    
    # Get user stats
    stats = await db.user_stats.find_one({"user_id": user_id}, {"_id": 0})
    if not stats:
        stats = {"total_questions": 0, "correct_answers": 0, "wrong_answers": 0, "by_specialty": {}, "by_year": {}}
    
    # Get streak data
    streak_data = await db.user_streaks.find_one({"user_id": user_id}, {"_id": 0})
    if not streak_data:
        streak_data = {"current_streak": 0, "longest_streak": 0, "last_activity_date": None}
    
    # Get exam date if set
    user_settings = await db.user_settings.find_one({"user_id": user_id}, {"_id": 0})
    exam_date = user_settings.get("exam_date") if user_settings else None
    daily_goal = user_settings.get("daily_goal", 50) if user_settings else 50
    weekly_goal = user_settings.get("weekly_goal", 250) if user_settings else 250
    
    # Get total questions per specialty - single aggregation instead of N queries
    count_pipeline = [
        {"$group": {"_id": "$specialty_id", "count": {"$sum": 1}}}
    ]
    spec_counts = {doc["_id"]: doc["count"] for doc in await db.questions.aggregate(count_pipeline).to_list(100)}
    
    specialties = await db.specialties.find({}, {"_id": 0}).to_list(100)
    specialty_progress = []
    for spec in specialties:
        total_in_spec = spec_counts.get(spec["id"], 0)
        user_answered = stats.get("by_specialty", {}).get(spec["id"], {}).get("total", 0)
        user_correct = stats.get("by_specialty", {}).get(spec["id"], {}).get("correct", 0)
        specialty_progress.append({
            "id": spec["id"],
            "name_de": spec["name_de"],
            "total_questions": total_in_spec,
            "answered": user_answered,
            "correct": user_correct,
            "progress": round((user_answered / total_in_spec * 100) if total_in_spec > 0 else 0, 1)
        })
    
    # Calculate readiness score
    total_questions = sum(spec_counts.values())
    total_answered = stats.get("total_questions", 0)
    total_correct = stats.get("correct_answers", 0)
    accuracy = (total_correct / total_answered * 100) if total_answered > 0 else 0
    coverage = (total_answered / total_questions * 100) if total_questions > 0 else 0
    readiness = round((accuracy * 0.6 + coverage * 0.4), 1)  # Weighted score
    
    return {
        "total_answered": total_answered,
        "total_correct": total_correct,
        "total_wrong": stats.get("wrong_answers", 0),
        "accuracy": round(accuracy, 1),
        "coverage": round(coverage, 1),
        "readiness": readiness,
        "current_streak": streak_data.get("current_streak", 0),
        "longest_streak": streak_data.get("longest_streak", 0),
        "exam_date": exam_date,
        "daily_goal": daily_goal,
        "weekly_goal": weekly_goal,
        "specialty_progress": specialty_progress,
        "xp": stats.get("xp", 0),
        "level": get_level_info(stats.get("xp", 0)),
    }

@api_router.get("/dashboard/weekly-activity")
async def get_weekly_activity(user: dict = Depends(get_current_user)):
    """Get daily activity for the past 7 days"""
    user_id = user["id"]
    
    # Get activity for last 7 days
    activities = await db.daily_activity.find(
        {"user_id": user_id},
        {"_id": 0}
    ).sort("date", -1).limit(7).to_list(7)
    
    # Create a map for easy lookup
    activity_map = {a["date"]: a for a in activities}
    
    # Generate last 7 days
    result = []
    for i in range(6, -1, -1):
        date = (datetime.now(timezone.utc) - __import__('datetime').timedelta(days=i)).strftime("%Y-%m-%d")
        day_name = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"][(datetime.now(timezone.utc) - __import__('datetime').timedelta(days=i)).weekday()]
        
        if date in activity_map:
            act = activity_map[date]
            result.append({
                "date": date,
                "day": day_name,
                "questions": act.get("questions", 0),
                "correct": act.get("correct", 0),
                "accuracy": round((act.get("correct", 0) / act.get("questions", 1)) * 100) if act.get("questions", 0) > 0 else 0
            })
        else:
            result.append({
                "date": date,
                "day": day_name,
                "questions": 0,
                "correct": 0,
                "accuracy": 0
            })
    
    return result

@api_router.get("/dashboard/achievements")
async def get_achievements(user: dict = Depends(get_current_user)):
    """Get user achievements/badges"""
    user_id = user["id"]
    stats = await db.user_stats.find_one({"user_id": user_id}, {"_id": 0})
    streak_data = await db.user_streaks.find_one({"user_id": user_id}, {"_id": 0})
    
    if not stats:
        stats = {"total_questions": 0, "correct_answers": 0, "xp": 0, "by_specialty": {}}
    if not streak_data:
        streak_data = {"current_streak": 0, "longest_streak": 0}
    
    return compute_badges(stats, streak_data)

@api_router.get("/dashboard/recent-activity")
async def get_recent_activity(user: dict = Depends(get_current_user), limit: int = 5):
    """Get recent quiz activities"""
    user_id = user["id"]
    
    activities = await db.quiz_sessions.find(
        {"user_id": user_id},
        {"_id": 0}
    ).sort("completed_at", -1).limit(limit).to_list(limit)
    
    return activities

@api_router.post("/dashboard/settings")
async def update_dashboard_settings(user: dict = Depends(get_current_user), exam_date: Optional[str] = None, daily_goal: Optional[int] = None, weekly_goal: Optional[int] = None):
    """Update user dashboard settings"""
    user_id = user["id"]
    
    update_data = {}
    if exam_date is not None:
        update_data["exam_date"] = exam_date
    if daily_goal is not None:
        update_data["daily_goal"] = daily_goal
    if weekly_goal is not None:
        update_data["weekly_goal"] = weekly_goal
    
    if update_data:
        await db.user_settings.update_one(
            {"user_id": user_id},
            {"$set": update_data},
            upsert=True
        )
    
    return {"message": "Settings updated"}

@api_router.post("/dashboard/track-activity")
async def track_activity(user: dict = Depends(get_current_user), questions: int = 1, correct: int = 0):
    """Track daily activity and update streak"""
    # Validate inputs to prevent stat manipulation
    questions = max(0, min(questions, 500))
    correct = max(0, min(correct, questions))  # correct can never exceed questions answered
    user_id = user["id"]
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    # Update daily activity
    await db.daily_activity.update_one(
        {"user_id": user_id, "date": today},
        {"$inc": {"questions": questions, "correct": correct}},
        upsert=True
    )
    
    # Update streak
    streak_data = await db.user_streaks.find_one({"user_id": user_id})
    yesterday = (datetime.now(timezone.utc) - __import__('datetime').timedelta(days=1)).strftime("%Y-%m-%d")
    
    if not streak_data:
        await db.user_streaks.insert_one({
            "user_id": user_id,
            "current_streak": 1,
            "longest_streak": 1,
            "last_activity_date": today
        })
    else:
        last_date = streak_data.get("last_activity_date")
        current_streak = streak_data.get("current_streak", 0)
        longest_streak = streak_data.get("longest_streak", 0)
        
        if last_date == today:
            # Already tracked today
            pass
        elif last_date == yesterday:
            # Continuing streak
            current_streak += 1
            longest_streak = max(longest_streak, current_streak)
            await db.user_streaks.update_one(
                {"user_id": user_id},
                {"$set": {"current_streak": current_streak, "longest_streak": longest_streak, "last_activity_date": today}}
            )
        else:
            # Streak broken, start new
            await db.user_streaks.update_one(
                {"user_id": user_id},
                {"$set": {"current_streak": 1, "last_activity_date": today}}
            )
    
    return {"message": "Activity tracked"}

# ============ GAMIFICATION ROUTES ============

@api_router.get("/gamification/profile")
async def get_gamification_profile(user: dict = Depends(get_current_user)):
    """Get user's XP, level, badges, and rank"""
    user_id = user["id"]
    stats = await db.user_stats.find_one({"user_id": user_id}, {"_id": 0})
    streak_data = await db.user_streaks.find_one({"user_id": user_id}, {"_id": 0})
    
    if not stats:
        stats = {"total_questions": 0, "correct_answers": 0, "wrong_answers": 0, "xp": 0, "by_specialty": {}}
    if not streak_data:
        streak_data = {"current_streak": 0, "longest_streak": 0}
    
    xp = stats.get("xp", 0)
    level_info = get_level_info(xp)
    badges = compute_badges(stats, streak_data)
    
    # Calculate rank (position among all users by XP)
    higher_count = await db.user_stats.count_documents({"xp": {"$gt": xp}})
    rank = higher_count + 1
    
    return {
        "xp": xp,
        "level": level_info,
        "badges": badges,
        "rank": rank,
        "all_levels": LEVELS,
        "streak": streak_data.get("current_streak", 0),
        "longest_streak": streak_data.get("longest_streak", 0),
    }

@api_router.get("/gamification/leaderboard")
async def get_public_leaderboard(user: dict = Depends(get_current_user)):
    """Get top users by XP - public leaderboard"""
    pipeline = [
        {"$lookup": {
            "from": "user_stats",
            "localField": "id",
            "foreignField": "user_id",
            "as": "stats"
        }},
        {"$unwind": {"path": "$stats", "preserveNullAndEmptyArrays": True}},
        {"$project": {
            "_id": 0,
            "id": 1,
            "name": 1,
            "xp": {"$ifNull": ["$stats.xp", 0]},
            "total_questions": {"$ifNull": ["$stats.total_questions", 0]},
            "correct_answers": {"$ifNull": ["$stats.correct_answers", 0]},
        }},
        {"$match": {"total_questions": {"$gt": 0}}},
        {"$sort": {"xp": -1}},
        {"$limit": 50}
    ]
    
    users = await db.users.aggregate(pipeline).to_list(50)
    
    # Add level info and rank
    for i, u in enumerate(users):
        u["rank"] = i + 1
        u["level"] = get_level_info(u.get("xp", 0))
        u["accuracy"] = round((u["correct_answers"] / u["total_questions"] * 100), 1) if u.get("total_questions", 0) > 0 else 0
    
    return users

# ============ NOTIFICATION ROUTES ============

MOTIVATIONAL_MESSAGES = [
    "Bleib dran! Jede Frage bringt dich näher zum Ziel.",
    "Dein Wissen wächst jeden Tag. Weiter so!",
    "Kleine Schritte führen zum großen Erfolg.",
    "Die Prüfung wartet – zeig, was du kannst!",
    "Heute schon gelernt? Dein Streak wartet auf dich!",
    "Übung macht den Meister – starte jetzt!",
    "Du bist auf dem richtigen Weg. Mach weiter!",
]

STREAK_MESSAGES = {
    0: "Du hast gestern nicht gelernt. Starte heute neu!",
    1: "Tag 1 geschafft! Mach weiter, um deinen Streak aufzubauen.",
    3: "3 Tage in Folge! Du baust eine starke Gewohnheit auf.",
    5: "5-Tage-Streak! Du bist auf Kurs.",
    7: "Eine ganze Woche! Deine Disziplin zahlt sich aus.",
    14: "2 Wochen am Stück! Du bist nicht aufzuhalten.",
    30: "30-Tage-Streak! Ein wahrer Champion.",
}

REVIEW_MESSAGES = [
    "{count} Fragen warten auf Wiederholung. SM-2 sagt: Heute ist der beste Tag!",
    "Dein Gehirn vergisst – {count} Fragen brauchen eine Auffrischung.",
    "{count} Karteikarten sind fällig. 10 Minuten reichen!",
]

@api_router.get("/notifications")
async def get_notifications(user: dict = Depends(get_current_user)):
    """Get user notifications (latest 20)"""
    notifications = await db.notifications.find(
        {"user_id": user["id"]},
        {"_id": 0}
    ).sort("created_at", -1).limit(20).to_list(20)
    
    unread = await db.notifications.count_documents({"user_id": user["id"], "read": False})
    return {"notifications": notifications, "unread_count": unread}

@api_router.post("/notifications/read")
async def mark_notifications_read(user: dict = Depends(get_current_user)):
    """Mark all notifications as read"""
    await db.notifications.update_many(
        {"user_id": user["id"], "read": False},
        {"$set": {"read": True}}
    )
    return {"status": "ok"}

@api_router.post("/notifications/generate-daily")
async def generate_daily_notifications(user: dict = Depends(get_current_user)):
    """Generate smart daily notifications based on streak, reviews, and progress"""
    import random
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    existing = await db.notifications.find_one({
        "user_id": user["id"], "type": "daily_reminder", "date": today
    })
    if existing:
        return {"status": "already_generated"}
    
    # Check streak status
    streak_data = await db.user_streaks.find_one({"user_id": user["id"]})
    streak = streak_data.get("current_streak", 0) if streak_data else 0
    
    # Check due reviews
    due_count = await db.spaced_repetition.count_documents(
        {"user_id": user["id"], "next_review": {"$lte": today}}
    )
    
    notifications_to_create = []
    
    # 1. Streak notification
    streak_msg = None
    for threshold in sorted(STREAK_MESSAGES.keys(), reverse=True):
        if streak >= threshold:
            streak_msg = STREAK_MESSAGES[threshold]
            break
    if not streak_msg:
        streak_msg = random.choice(MOTIVATIONAL_MESSAGES)
    
    if streak >= 3:
        streak_msg = f"🔥 {streak}-Tage-Streak! {streak_msg}"
    
    notifications_to_create.append({
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        "type": "daily_reminder",
        "title": "Tägliche Erinnerung",
        "message": streak_msg,
        "icon": "flame",
        "read": False,
        "date": today,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    
    # 2. Review reminder (if due cards exist)
    if due_count > 0:
        review_msg = random.choice(REVIEW_MESSAGES).format(count=due_count)
        notifications_to_create.append({
            "id": str(uuid.uuid4()),
            "user_id": user["id"],
            "type": "review_reminder",
            "title": "Wiederholung fällig",
            "message": review_msg,
            "icon": "rotate-ccw",
            "read": False,
            "date": today,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
    
    # 3. Weakness alert (weekly)
    import datetime as dt
    if datetime.now(timezone.utc).weekday() == 0:  # Monday
        stats = await db.user_stats.find_one({"user_id": user["id"]}, {"_id": 0, "by_specialty": 1})
        if stats:
            by_spec = stats.get("by_specialty", {})
            weakest = None
            for sid, data in by_spec.items():
                if data.get("total", 0) >= 5:
                    acc = data.get("correct", 0) / data.get("total", 1) * 100
                    if weakest is None or acc < weakest[1]:
                        weakest = (sid, acc)
            if weakest and weakest[1] < 60:
                spec = await db.specialties.find_one({"id": weakest[0]}, {"_id": 0, "name_de": 1})
                name = spec.get("name_de", weakest[0]) if spec else weakest[0]
                notifications_to_create.append({
                    "id": str(uuid.uuid4()),
                    "user_id": user["id"],
                    "type": "weakness_alert",
                    "title": "Schwäche erkannt",
                    "message": f"{name}: nur {round(weakest[1])}% richtig. Übe gezielt, um dich zu verbessern!",
                    "icon": "alert-triangle",
                    "read": False,
                    "date": today,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                })
    
    for n in notifications_to_create:
        await db.notifications.insert_one(n)
    
    return {"status": "created", "count": len(notifications_to_create)}

# ============ NOTES & REPORTS ROUTES ============

@api_router.post("/notes")
async def save_note(data: dict, user: dict = Depends(get_current_user)):
    """Save or update a personal note for a question"""
    question_id = data.get("question_id")
    text = data.get("text", "").strip()
    if not question_id:
        raise HTTPException(status_code=400, detail="question_id required")
    existing = await db.notes.find_one({"user_id": user["id"], "question_id": question_id})
    if existing:
        await db.notes.update_one(
            {"user_id": user["id"], "question_id": question_id},
            {"$set": {"text": text, "updated_at": datetime.now(timezone.utc).isoformat()}}
        )
    else:
        await db.notes.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": user["id"],
            "question_id": question_id,
            "text": text,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
    return {"status": "saved"}

@api_router.get("/notes/all")
async def get_all_notes(user: dict = Depends(get_current_user)):
    """Get all notes for a user with question text"""
    notes = await db.notes.find(
        {"user_id": user["id"], "text": {"$ne": ""}},
        {"_id": 0}
    ).sort("updated_at", -1).to_list(500)

    if not notes:
        return []

    question_ids = [n["question_id"] for n in notes]
    questions = await db.questions.find(
        {"id": {"$in": question_ids}},
        {"_id": 0, "id": 1, "question_text_de": 1, "question_text": 1, "specialty_id": 1}
    ).to_list(500)
    q_map = {q["id"]: q for q in questions}

    result = []
    for n in notes:
        q = q_map.get(n["question_id"], {})
        result.append({
            "id": n.get("id", ""),
            "question_id": n["question_id"],
            "text": n["text"],
            "question_text": q.get("question_text_de", q.get("question_text", "Frage nicht gefunden")),
            "specialty_id": q.get("specialty_id", ""),
            "created_at": n.get("created_at", ""),
            "updated_at": n.get("updated_at", ""),
        })
    return result

@api_router.get("/notes/{question_id}")
async def get_note(question_id: str, user: dict = Depends(get_current_user)):
    """Get user's note for a question"""
    note = await db.notes.find_one(
        {"user_id": user["id"], "question_id": question_id},
        {"_id": 0}
    )
    return note or {"text": ""}

@api_router.delete("/notes/{question_id}")
async def delete_note(question_id: str, user: dict = Depends(get_current_user)):
    """Delete a user's note for a question"""
    await db.notes.delete_one({"user_id": user["id"], "question_id": question_id})
    return {"status": "deleted"}

@api_router.post("/reports")
async def submit_report(data: dict, user: dict = Depends(get_current_user)):
    """Submit a problem report for a question"""
    question_id = data.get("question_id")
    category = data.get("category", "")
    details = data.get("details", "").strip()
    question_text = data.get("question_text", "")
    if not question_id or not category:
        raise HTTPException(status_code=400, detail="question_id and category required")
    report = {
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        "question_id": question_id,
        "category": category,
        "details": details,
        "question_text": question_text,
        "status": "open",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.reports.insert_one(report)

    # Notify all admins about the new report
    admins = await db.users.find({"is_admin": True}, {"_id": 0, "id": 1}).to_list(50)
    reporter = user.get("email", "Unbekannt")
    now = datetime.now(timezone.utc).isoformat()
    for admin in admins:
        await db.notifications.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": admin["id"],
            "type": "report",
            "icon": "bell",
            "title": f"Neue Meldung: {category}",
            "message": f"{reporter} hat eine Frage gemeldet ({category}). Details: {details[:80] if details else 'Keine'}",
            "report_id": report["id"],
            "read": False,
            "created_at": now,
        })

    return {"status": "submitted"}

@api_router.get("/admin/reports")
async def get_reports(status: str = "open", admin: dict = Depends(get_admin_user)):
    """Admin: get all reports"""
    query = {}
    if status != "all":
        query["status"] = status
    reports = await db.reports.find(query, {"_id": 0}).sort("created_at", -1).to_list(200)
    return reports

@api_router.post("/admin/reports/{report_id}/resolve")
async def resolve_report(report_id: str, admin: dict = Depends(get_admin_user)):
    """Admin: resolve a report"""
    await db.reports.update_one({"id": report_id}, {"$set": {"status": "resolved"}})
    return {"status": "resolved"}

@api_router.delete("/admin/reports/{report_id}")
async def delete_report(report_id: str, admin: dict = Depends(get_admin_user)):
    """Admin: delete a report"""
    await db.reports.delete_one({"id": report_id})
    return {"status": "deleted"}

@api_router.post("/admin/reports/{report_id}/reply")
async def reply_to_report(report_id: str, data: dict, admin: dict = Depends(get_admin_user)):
    """Admin: reply to a report — sends notification to the reporting user"""
    message = data.get("message", "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="Nachricht erforderlich")

    report = await db.reports.find_one({"id": report_id}, {"_id": 0})
    if not report:
        raise HTTPException(status_code=404, detail="Bericht nicht gefunden")

    now = datetime.now(timezone.utc).isoformat()
    await db.reports.update_one(
        {"id": report_id},
        {"$set": {"status": "replied", "admin_reply": message, "replied_at": now, "replied_by": admin["id"]}}
    )

    await db.notifications.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": report["user_id"],
        "type": "report_reply",
        "icon": "bell",
        "title": "Antwort auf Ihre Meldung",
        "message": f"Admin hat auf Ihre Meldung ({report.get('category', '')}) geantwortet: {message}",
        "read": False,
        "created_at": now,
    })

    return {"status": "replied"}


# ============ TAGS SYSTEM ============

@api_router.get("/tags")
async def get_tags():
    """Get all question tags"""
    tags = await db.tags.find({}, {"_id": 0}).sort("name", 1).to_list(200)
    return tags

@api_router.post("/admin/tags")
async def create_tag(data: dict, admin: dict = Depends(get_admin_user)):
    """Admin: create a tag"""
    name = data.get("name", "").strip()
    color = data.get("color", "#6366f1")
    if not name:
        raise HTTPException(status_code=400, detail="Name erforderlich")
    existing = await db.tags.find_one({"name": {"$regex": f"^{name}$", "$options": "i"}})
    if existing:
        raise HTTPException(status_code=400, detail="Tag existiert bereits")
    tag = {"id": str(uuid.uuid4()), "name": name, "color": color, "created_at": datetime.now(timezone.utc).isoformat()}
    await db.tags.insert_one(tag)
    return {"id": tag["id"], "name": name, "color": color}

@api_router.delete("/admin/tags/{tag_id}")
async def delete_tag(tag_id: str, admin: dict = Depends(get_admin_user)):
    """Admin: delete a tag and remove from all questions"""
    await db.tags.delete_one({"id": tag_id})
    await db.questions.update_many({"tags": tag_id}, {"$pull": {"tags": tag_id}})
    return {"status": "deleted"}

@api_router.post("/admin/questions/{question_id}/tags")
async def update_question_tags(question_id: str, data: dict, admin: dict = Depends(get_admin_user)):
    """Admin: set tags on a question"""
    tags = data.get("tags", [])
    await db.questions.update_one({"id": question_id}, {"$set": {"tags": tags}})
    return {"status": "updated"}

@api_router.get("/admin/reports/all")
async def get_all_reports(admin: dict = Depends(get_admin_user)):
    """Admin: get all reports with user info"""
    reports = await db.reports.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)
    user_ids = list(set(r.get("user_id", "") for r in reports))
    users = await db.users.find({"id": {"$in": user_ids}}, {"_id": 0, "id": 1, "email": 1}).to_list(500)
    u_map = {u["id"]: u.get("email", "Unbekannt") for u in users}
    for r in reports:
        r["user_email"] = u_map.get(r.get("user_id", ""), "Unbekannt")
    return reports


# ============ ADMIN ROUTES (extracted to routes/admin.py) ============

# ============ TELEGRAM BOT STATUS ============

@api_router.get("/admin/telegram/status")
async def get_telegram_status(admin: dict = Depends(get_admin_user)):
    """Get Telegram bot status and user count"""
    from telegram_bot import get_token
    user_count = await db.telegram_users.count_documents({})
    total_answers = 0
    async for s in db.telegram_stats.find({}, {"_id": 0, "total": 1}):
        total_answers += s.get("total", 0)
    return {
        "enabled": bool(get_token()),
        "users": user_count,
        "total_answers": total_answers,
    }

# ============ AI MEDICAL BLOG ============

@api_router.get("/blog/posts")
async def get_blog_posts(limit: int = 20, skip: int = 0):
    """Get published blog posts (public, no auth)"""
    posts = await db.blog_posts.find(
        {"published": True},
        {"_id": 0, "content": 0}
    ).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    total = await db.blog_posts.count_documents({"published": True})
    return {"posts": posts, "total": total}


@api_router.get("/blog/posts/{slug}")
async def get_blog_post(slug: str):
    """Get a single blog post by slug (public)"""
    post = await db.blog_posts.find_one({"slug": slug, "published": True}, {"_id": 0})
    if not post:
        raise HTTPException(status_code=404, detail="Artikel nicht gefunden")
    # Increment views
    await db.blog_posts.update_one({"slug": slug}, {"$inc": {"views": 1}})
    return post


@api_router.post("/blog/generate")
async def generate_blog_post(topic: str = "", specialty_id: str = "", admin: dict = Depends(get_admin_user)):
    """Start blog post generation as background job (admin only)"""
    job_id = str(uuid.uuid4())
    await db.blog_jobs.insert_one({
        "id": job_id, "status": "processing", "topic": topic, "specialty_id": specialty_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    asyncio.create_task(_run_blog_generation(job_id, topic, specialty_id))
    return {"job_id": job_id, "status": "processing"}


@api_router.get("/blog/job/{job_id}")
async def get_blog_job(job_id: str, admin: dict = Depends(get_admin_user)):
    """Poll blog generation job"""
    job = await db.blog_jobs.find_one({"id": job_id}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Job nicht gefunden")
    return job


async def _run_blog_generation(job_id: str, topic: str, specialty_id: str):
    """Background: generate blog post"""
    import re
    try:
        if not topic:
            specs_with_q = []
            async for s in db.specialties.find({}, {"_id": 0, "id": 1, "name_de": 1}):
                cnt = await db.questions.count_documents({"specialty_id": s["id"]})
                if cnt > 10:
                    specs_with_q.append(s["name_de"])
            import random
            topic = f"Top Prüfungsfragen: {random.choice(specs_with_q)}" if specs_with_q else "Medizinische Prüfungsvorbereitung"

        query = {"specialty_id": specialty_id} if specialty_id else {}
        pipeline = [{"$match": query}, {"$sample": {"size": 10}},
                    {"$project": {"_id": 0, "question_text_de": 1, "explanation_de": 1}}]
        sample_qs = await db.questions.aggregate(pipeline).to_list(10)
        q_context = "\n".join([f"- {q.get('question_text_de','')[:100]}: {q.get('explanation_de','')[:150]}" for q in sample_qs if q.get("question_text_de")])

        system_msg = "Du bist ein medizinischer Fachjournalist für Prep Academy. Schreibe informative, SEO-optimierte Blog-Artikel auf Deutsch. Verwende Markdown (## ###). Max 1000 Wörter."
        prompt = f"""Schreibe einen Blog-Artikel über: "{topic}"
Zielgruppe: Medizinstudenten für die österreichische Ärzte-Prüfung.
Kontext:\n{q_context}
Format:
TITLE: [Titel]
EXCERPT: [2 Sätze]
TAGS: [tag1, tag2, tag3]
---
[Artikel in Markdown]"""
        response = await _or_text(system_msg, prompt, max_tokens=800)
        
        parts = response.split("---", 1)
        meta = parts[0] if parts else ""
        content = parts[1].strip() if len(parts) > 1 else response
        
        title = topic
        excerpt = ""
        tags = []
        for line in meta.strip().split("\n"):
            if line.startswith("TITLE:"): title = line.replace("TITLE:", "").strip().strip("*").strip()
            elif line.startswith("EXCERPT:"): excerpt = line.replace("EXCERPT:", "").strip().strip("*").strip()
            elif line.startswith("TAGS:"): tags = [t.strip().strip("*") for t in line.replace("TAGS:", "").strip().strip("[]").split(",")]
        
        slug = re.sub(r'[^a-z0-9]+', '-', title.lower().replace("ä","ae").replace("ö","oe").replace("ü","ue").replace("ß","ss")).strip("-")[:80]
        existing = await db.blog_posts.find_one({"slug": slug})
        if existing:
            slug = f"{slug}-{uuid.uuid4().hex[:4]}"
        
        post = {
            "id": str(uuid.uuid4()), "slug": slug, "title": title, "excerpt": excerpt,
            "content": content, "tags": tags, "specialty_id": specialty_id,
            "author": "Prep Academy AI", "published": True, "views": 0,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await db.blog_posts.insert_one(post)
        await db.blog_jobs.update_one({"id": job_id}, {"$set": {"status": "done", "post": {k: v for k, v in post.items() if k != "_id"}}})
    except Exception as e:
        logger.error(f"Blog generation error: {e}")
        await db.blog_jobs.update_one({"id": job_id}, {"$set": {"status": "error", "message": str(e)[:200]}})


# ============ ROOT ============

# Health check at root level (NOT under /api) - required for deployment
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/")
async def app_root():
    return {"status": "healthy", "app": "Medical MCQ API"}

@api_router.get("/")
async def root():
    return {"message": "Medical MCQ API", "version": "1.0.0"}

# Include routers
app.include_router(api_router)

# Include learning tools router
from routes.learn import router as learn_router
app.include_router(learn_router)

# Include admin router
from routes.admin import router as admin_router
app.include_router(admin_router)

# Include billing/Stripe router
from routes.billing import make_router as make_billing_router
billing_router = make_billing_router(db, get_current_user)
app.include_router(billing_router, prefix="/api")

# Include daily podcast router + start background generator
from routes.daily_podcast import make_router as make_podcast_router, daily_podcast_loop
podcast_router = make_podcast_router(db, get_current_user)
app.include_router(podcast_router)

# Include Medical RAG + DICOM routers (only if heavy ML packages are installed)
# These are disabled in Emergent free deployment (which has 250m CPU + 1Gi memory limit)
# To re-enable: install chromadb + sentence-transformers + pydicom + opencv-python-headless
# and set ENABLE_ADVANCED_FEATURES=true in .env
_ADVANCED = os.environ.get("ENABLE_ADVANCED_FEATURES", "false").lower() == "true"
if _ADVANCED:
    try:
        from routes.rag import router as rag_router
        app.include_router(rag_router)
        logger.info("[Server] RAG router enabled")
    except Exception as e:
        logger.warning(f"[Server] RAG router skipped: {e}")

    try:
        from routes.dicom import router as dicom_router
        app.include_router(dicom_router)
        logger.info("[Server] DICOM router enabled")
    except Exception as e:
        logger.warning(f"[Server] DICOM router skipped: {e}")
else:
    logger.info("[Server] Advanced features (RAG + DICOM) disabled via ENABLE_ADVANCED_FEATURES")


@app.on_event("startup")
async def _start_daily_podcast():
    asyncio.create_task(daily_podcast_loop(db))
    logger.info("Daily podcast background loop scheduled")

# CORS Configuration
# IMPORTANT: allow_credentials=True is incompatible with allow_origins=["*"].
# Always use an explicit list of trusted origins.
cors_origins_env = os.environ.get('CORS_ORIGINS', '')
if cors_origins_env and cors_origins_env != '*':
    cors_origins = [o.strip() for o in cors_origins_env.split(',') if o.strip()]
else:
    # Safe defaults for known deployment domains
    cors_origins = [
        "https://prep-academy-rho.vercel.app",
        "https://prep-academy.vercel.app",
        "http://localhost:3000",
        "http://localhost:5173",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)
