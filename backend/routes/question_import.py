"""Question Import & Option Completion Tool — Routes."""
import os as _os
import json as _json
import uuid as _uuid
import re as _re
import io as _io
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Request
from typing import List, Optional
from database import db, logger
from models import (
    ImportJob, ImportFileInfo, ParsedQuestion, ImportResponse,
    ValidationSummary, ValidationResult
)
from auth import get_current_user, get_admin_user
from services.import_job import (
    create_import_job, get_import_job, update_import_job,
    add_file_to_job, update_file_status, add_questions_to_job,
    set_job_status, validate_import_job
)

router = APIRouter(prefix="/api", tags=["question-import"])

ALLOWED_EXTENSIONS = {".pdf", ".md", ".markdown", ".txt"}


@router.post("/admin/question-import", response_model=ImportResponse)
async def upload_import_files(
    files: List[UploadFile] = File(...),
    user: dict = Depends(get_current_user)
):
    """Upload PDF and/or Markdown files for question import. Creates an ImportJob and returns its ID."""
    if not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin only")
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    # Validate file types
    for f in files:
        ext = _os.path.splitext(f.filename or "")[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type '{ext}' for '{f.filename}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
            )

    # Create import job
    job = await create_import_job()

    # Register each file in the job
    for f in files:
        file_type = "pdf" if f.filename and f.filename.lower().endswith(".pdf") else "markdown"
        file_info = ImportFileInfo(
            filename=f.filename or "unnamed",
            file_type=file_type,
            status="uploaded"
        )
        await add_file_to_job(job.id, file_info)

    return ImportResponse(import_id=job.id, status="uploaded")


@router.get("/admin/question-import/{import_id}")
async def get_import_job_details(
    import_id: str,
    user: dict = Depends(get_current_user)
):
    """Get details of an import job including parsed questions."""
    if not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin only")
    job = await get_import_job(import_id)
    if not job:
        raise HTTPException(status_code=404, detail="Import job not found")
    return job


@router.post("/admin/question-import/{import_id}/validate")
async def validate_import_job_endpoint(
    import_id: str,
    user: dict = Depends(get_current_user)
):
    """Validate all questions in an import job. Returns summary of valid/invalid questions."""
    if not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin only")
    job = await get_import_job(import_id)
    if not job:
        raise HTTPException(status_code=404, detail="Import job not found")

    summary = validate_import_job(job)
    return summary
