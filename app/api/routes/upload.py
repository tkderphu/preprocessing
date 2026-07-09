"""
upload.py
---------
POST /upload — Accept a file, save it, publish a job to RabbitMQ.
"""

import logging
import shutil
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from app.config import get_settings
from app.models.schemas import FileType, JobMessage, UploadResponse
from app.worker.celery_app import celery_app

logger    = logging.getLogger(__name__)
settings  = get_settings()
router    = APIRouter()

# ── Allowed extensions ────────────────────────────────────────────────────────
AUDIO_EXTS = {".mp3", ".wav", ".ogg", ".m4a", ".flac", ".webm", ".mp4"}
DOC_EXTS   = {".pdf", ".docx", ".doc"}

MAX_FILE_SIZE_MB = 500


def _detect_file_type(filename: str) -> FileType:
    suffix = Path(filename).suffix.lower()
    if suffix in AUDIO_EXTS:
        return FileType.AUDIO
    if suffix == ".pdf":
        return FileType.PDF
    if suffix in {".docx", ".doc"}:
        return FileType.DOCX
    raise HTTPException(
        status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        detail=f"Unsupported file type '{suffix}'. Allowed: {AUDIO_EXTS | DOC_EXTS}",
    )


@router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload a file for processing",
)
async def upload_file(
    file:            UploadFile = File(..., description="Audio / PDF / DOCX file"),
    recipient_email: str        = Form(default="", description="Override recipient email"),
    github_branch:   str        = Form(default="", description="Override GitHub branch"),
):
    """
    Upload a file. The server will:
    1. Validate and save the file
    2. Detect type (audio / pdf / docx)
    3. Publish a processing job to RabbitMQ
    4. Return a job_id to poll for status
    """
    file_type = _detect_file_type(file.filename)

    # Build job and create directory
    job = JobMessage(
        file_name=file.filename,
        file_type=file_type,
        recipient_email=recipient_email or settings.mail_to,
        github_branch=github_branch or settings.github_branch,
        file_path="",   # will be set after save
    )

    job_dir = settings.upload_dir / job.job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    dest = job_dir / file.filename
    job.file_path = str(dest)

    # Save the file
    try:
        with dest.open("wb") as f:
            shutil.copyfileobj(file.file, f)
    except Exception as exc:
        logger.error("Failed to save file: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save uploaded file.",
        ) from exc

    file_size_mb = dest.stat().st_size / (1024 * 1024)
    if file_size_mb > MAX_FILE_SIZE_MB:
        dest.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds {MAX_FILE_SIZE_MB} MB limit.",
        )

    logger.info(
        "Saved file '%s' (%.1f MB) → job_id=%s",
        file.filename, file_size_mb, job.job_id,
    )

    # Dispatch to Celery worker via RabbitMQ (proper Celery message format)
    try:
        celery_app.send_task(
            "app.worker.tasks.process_document_job",
            args=[job.model_dump_json()],
            task_id=job.job_id,
            queue=settings.celery_queue_name,
        )
    except Exception as exc:
        logger.error("Failed to dispatch Celery task: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to enqueue job. Please try again later.",
        ) from exc

    return UploadResponse(job_id=job.job_id)
