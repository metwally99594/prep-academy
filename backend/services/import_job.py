"""ImportJob CRUD operations for the Question Import & Option Completion Tool."""
from database import db
from models import ImportJob, ImportFileInfo, ParsedQuestion, ValidationResult, ValidationSummary
from datetime import datetime, timezone
from typing import Optional


async def create_import_job() -> ImportJob:
    job = ImportJob()
    await db.import_jobs.insert_one(job.model_dump())
    return job


async def get_import_job(job_id: str) -> Optional[ImportJob]:
    doc = await db.import_jobs.find_one({"id": job_id}, {"_id": 0})
    if doc:
        return ImportJob(**doc)
    return None


async def update_import_job(job: ImportJob) -> bool:
    job.updated_at = datetime.now(timezone.utc).isoformat()
    result = await db.import_jobs.update_one(
        {"id": job.id},
        {"$set": job.model_dump()}
    )
    return result.modified_count > 0


async def add_file_to_job(job_id: str, file_info: ImportFileInfo) -> bool:
    result = await db.import_jobs.update_one(
        {"id": job_id},
        {"$push": {"files": file_info.model_dump()}}
    )
    return result.modified_count > 0


async def update_file_status(job_id: str, filename: str, status: str, error: Optional[str] = None, questions_count: Optional[int] = None) -> bool:
    set_fields = {f"files.$.status": status}
    if error is not None:
        set_fields["files.$.error"] = error
    if questions_count is not None:
        set_fields["files.$.questions_count"] = questions_count
    result = await db.import_jobs.update_one(
        {"id": job_id, "files.filename": filename},
        {"$set": set_fields}
    )
    return result.modified_count > 0


async def add_questions_to_job(job_id: str, questions: list[ParsedQuestion]) -> bool:
    result = await db.import_jobs.update_one(
        {"id": job_id},
        {"$push": {"questions": {"$each": [q.model_dump() for q in questions]}}}
    )
    return result.modified_count > 0


async def set_job_status(job_id: str, status: str) -> bool:
    result = await db.import_jobs.update_one(
        {"id": job_id},
        {"$set": {"status": status, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    return result.modified_count > 0


async def delete_import_job(job_id: str) -> bool:
    result = await db.import_jobs.delete_one({"id": job_id})
    return result.deleted_count > 0


def validate_parsed_question(q: ParsedQuestion, index: int) -> ValidationResult:
    """Validate a single parsed question. Returns ValidationResult."""
    errors = []

    if not q.question or not q.question.strip():
        errors.append("Question text is empty")

    if len(q.options) < len(q.correct_answers):
        errors.append(f"Option count ({len(q.options)}) is less than correct answer count ({len(q.correct_answers)})")

    for ca in q.correct_answers:
        if ca not in q.options:
            errors.append(f"Correct answer '{ca}' not found in options list")

    if len(q.options) != len(set(q.options)):
        errors.append("Duplicate options detected")

    if not q.correct_answers:
        errors.append("No correct answer specified")

    return ValidationResult(
        question_index=index,
        valid=len(errors) == 0,
        errors=errors
    )


def validate_import_job(job: ImportJob) -> ValidationSummary:
    """Validate all questions in an import job. Returns summary."""
    errors_list = []
    valid_count = 0
    invalid_count = 0

    for i, q in enumerate(job.questions):
        result = validate_parsed_question(q, i)
        if result.valid:
            valid_count += 1
        else:
            invalid_count += 1
            errors_list.append({
                "index": i,
                "question": q.question[:80] + "..." if len(q.question) > 80 else q.question,
                "errors": result.errors
            })

    return ValidationSummary(
        total_questions=len(job.questions),
        valid=valid_count,
        invalid=invalid_count,
        errors=errors_list
    )
