"""Migration: set status=published for all questions missing it + ensure fachsprache specialty."""
import asyncio
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import db


async def main():
    # 1. Fix all questions without status field
    total = await db.questions.count_documents({})
    missing = await db.questions.count_documents({"status": {"$exists": False}})
    if missing:
        result = await db.questions.update_many(
            {"status": {"$exists": False}},
            {"$set": {"status": "published"}},
        )
        print(f"[OK] {result.modified_count} / {total} questions set to status=published (all were missing status)")
    else:
        print(f"[OK] All {total} questions already have status")

    # 2. Ensure no question has a non-published status accidentally
    non_published = await db.questions.count_documents({"status": {"$ne": "published"}})
    if non_published:
        print(f"[WARN]  {non_published} questions have status != published (draft/hidden)")

    # 3. Create/update fachsprache specialty
    existing = await db.specialties.find_one({"id": "fachsprache"})
    if not existing:
        await db.specialties.insert_one({
            "id": "fachsprache",
            "name": "Fachsprache",
            "name_de": "Medizinische Fachsprache",
            "country": "DE",
            "icon": "📖",
            "question_count": await db.questions.count_documents({"specialty_id": "fachsprache"}),
        })
        print("[OK] Specialty 'fachsprache' created")
    else:
        await db.specialties.update_one(
            {"id": "fachsprache"},
            {"$set": {"question_count": await db.questions.count_documents({"specialty_id": "fachsprache"})}},
        )
        print("[OK] Specialty 'fachsprache' question_count updated")


if __name__ == "__main__":
    asyncio.run(main())
