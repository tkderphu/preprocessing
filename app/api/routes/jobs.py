"""
jobs.py
-------
GET /jobs/{job_id} — Poll Celery result backend for job status.
"""

import logging

from celery.result import AsyncResult
from fastapi import APIRouter, HTTPException, status

from app.models.schemas import JobResult, JobStatus
from app.worker.celery_app import celery_app

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "/jobs/{job_id}",
    response_model=JobResult,
    summary="Get processing job status",
)
async def get_job_status(job_id: str) -> JobResult:
    """
    Poll the status of a processing job by its job_id.

    Returns status: queued | processing | done | failed
    When done, the `markdown` field contains the formatted output.
    """
    result: AsyncResult = celery_app.AsyncResult(job_id)

    if result.state == "PENDING":
        return JobResult(job_id=job_id, status=JobStatus.QUEUED)

    if result.state == "STARTED" or result.state == "PROGRESS":
        return JobResult(job_id=job_id, status=JobStatus.PROCESSING)

    if result.state == "SUCCESS":
        data = result.result or {}
        return JobResult(
            job_id=job_id,
            status=JobStatus.DONE,
            file_name=data.get("file_name", ""),
            markdown=data.get("markdown", ""),
            completed_at=data.get("completed_at", ""),
        )

    if result.state == "FAILURE":
        return JobResult(
            job_id=job_id,
            status=JobStatus.FAILED,
            error=str(result.result),
        )

    return JobResult(job_id=job_id, status=JobStatus.PROCESSING)


@router.delete(
    "/jobs/{job_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke / cancel a queued job",
)
async def cancel_job(job_id: str) -> None:
    """Revoke a pending or running Celery task."""
    celery_app.control.revoke(job_id, terminate=True)
    logger.info("Revoked job %s", job_id)
