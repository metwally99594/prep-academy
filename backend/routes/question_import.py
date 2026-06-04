"""Question Import & Option Completion Tool — Routes."""
import os as _os
import json as _json
import uuid as _uuid
import re as _re
import tempfile as _tempfile
import aiofiles as _aiofiles
from pathlib import Path as _Path
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
from services.ocr_service import extract_text_from_pdf, extract_text_from_markdown

router = APIRouter(prefix="/api", tags=["question-import"])

ALLOWED_EXTENSIONS = {".pdf", ".md", ".markdown", ".txt"}
UPLOAD_DIR = _Path(_os.environ.get("IMPORT_UPLOAD_DIR", _tempfile.gettempdir())) / "question_import"


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

    # Save files to disk and register in job
    job_dir = UPLOAD_DIR / job.id
    job_dir.mkdir(parents=True, exist_ok=True)

    for f in files:
        file_type = "pdf" if f.filename and f.filename.lower().endswith(".pdf") else "markdown"
        save_path = job_dir / (f.filename or "unnamed")
        content = await f.read()
        _aiofiles;  # ensure imported
        async with _aiofiles.open(str(save_path), "wb") as out:
            await out.write(content)

        file_info = ImportFileInfo(
            filename=f.filename or "unnamed",
            file_type=file_type,
            status="uploaded"
        )
        await add_file_to_job(job.id, file_info)

    return ImportResponse(import_id=job.id, status="uploaded")


@router.post("/admin/question-import/{import_id}/process")
async def process_import_job(
    import_id: str,
    user: dict = Depends(get_current_user)
):
    """Process uploaded files: OCR for PDFs, text extraction for Markdown. Updates job status."""
    if not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin only")
    job = await get_import_job(import_id)
    if not job:
        raise HTTPException(status_code=404, detail="Import job not found")
    if job.status != "uploaded":
        raise HTTPException(status_code=400, detail=f"Job already processed (status: {job.status})")

    await set_job_status(import_id, "processing")
    job_dir = UPLOAD_DIR / job.id
    all_questions = []
    errors = []

    for file_info in job.files:
        file_path = job_dir / file_info.filename
        if not file_path.exists():
            await update_file_status(import_id, file_info.filename, "failed", error="File not found on disk")
            errors.append({"filename": file_info.filename, "error": "File not found"})
            continue

        try:
            await update_file_status(import_id, file_info.filename, "processing")

            if file_info.file_type == "pdf":
                text = extract_text_from_pdf(str(file_path))
            else:
                text = extract_text_from_markdown(str(file_path))

            if not text or not text.strip():
                raise ValueError("Extracted text is empty")

            # Store raw text as a placeholder question for now
            # Full question parsing will be implemented in Action #4
            placeholder = ParsedQuestion(
                question=f"[RAW TEXT from {file_info.filename}]",
                options=[],
                correct_answers=[],
                source_file=file_info.filename,
                status="parsed"
            )
            all_questions.append(placeholder)
            await update_file_status(import_id, file_info.filename, "parsed", questions_count=1)

        except Exception as e:
            logger.error(f"Failed to process {file_info.filename}: {e}")
            await update_file_status(import_id, file_info.filename, "failed", error=str(e))
            errors.append({"filename": file_info.filename, "error": str(e)})

    if all_questions:
        await add_questions_to_job(import_id, all_questions)

    new_status = "parsed" if not errors else ("failed" if not all_questions else "parsed")
    await set_job_status(import_id, new_status)

    return {
        "import_id": import_id,
        "status": new_status,
        "files_processed": len(job.files),
        "questions_extracted": len(all_questions),
        "errors": errors
    }


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
