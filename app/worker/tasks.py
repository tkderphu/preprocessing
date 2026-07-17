"""
tasks.py
--------
Celery task pipeline for processing uploaded documents/audio.

Pipeline (single chained task):
  1. Extract text  (Whisper / Tika+OCR)
  2. Redact PII    (GLiNER + regex)
  3. Format to MD  (Qwen2.5)
  4. Save .md file
  5. Send email    (aiosmtplib)
  6. Push to GitLab (httpx)
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from celery import Task

from app.worker.celery_app import celery_app
from app.models.schemas import JobMessage, FileType
from app.services.extractor.factory import extract
from app.services.redaction import get_redaction_service
from app.services.formatter import MarkdownFormatter
from app.services.mailer import MailService
from app.services.gitlab_pusher import GitLabPusher
from app.config import get_settings

logger   = logging.getLogger(__name__)
settings = get_settings()

# Module-level singletons (initialized once per worker process)
_formatter: MarkdownFormatter | None = None
_mailer:    MailService       | None = None
_pusher:    GitLabPusher      | None = None


def _get_formatter() -> MarkdownFormatter:
    global _formatter
    if _formatter is None:
        _formatter = MarkdownFormatter()
    return _formatter


def _get_mailer() -> MailService:
    global _mailer
    if _mailer is None:
        _mailer = MailService()
    return _mailer


def _get_pusher() -> GitLabPusher:
    global _pusher
    if _pusher is None:
        _pusher = GitLabPusher()
    return _pusher


@celery_app.task(
    bind=True,
    name="app.worker.tasks.process_document_job",
    max_retries=2,
    default_retry_delay=30,
    acks_late=True,
)
def process_document_job(self: Task, job_message_json: str) -> dict:
    """
    Main Celery task — processes a single document/audio job end-to-end.

    Parameters
    ----------
    job_message_json : str
        JSON-serialized JobMessage published by the API.

    Returns
    -------
    dict
        {job_id, file_name, markdown, gitlab_url, completed_at}
        Stored in Redis result backend, retrievable by /jobs/{job_id}.
    """
    job = JobMessage.model_validate_json(job_message_json)
    logger.info("=== Starting job %s — file: %s ===", job.job_id, job.file_name)

    try:
        # ── 1. Extract ──────────────────────────────────────────────────────
        self.update_state(state="PROGRESS", meta={"step": "extracting"})
        raw_text, content_type = extract(job.file_path, job.file_type)

        if not raw_text.strip():
            raise ValueError("Extraction returned empty text.")

        logger.info("Extraction complete: %d chars (type=%s)", len(raw_text), content_type)
        logger.info("--- RAW EXTRACTED TEXT PREVIEW ---\n%s\n----------------------------------", raw_text[:1500])

        # ── 2. Redact PII ────────────────────────────────────────────────────
        self.update_state(state="PROGRESS", meta={"step": "redacting"})
        redaction_result = get_redaction_service().redact(raw_text)
        redacted_text    = redaction_result.redacted_text

        logger.info(
            "Redaction complete: %d entities removed.", len(redaction_result.entities)
        )

        # ── 3. Format to Markdown ────────────────────────────────────────────
        self.update_state(state="PROGRESS", meta={"step": "formatting"})
        markdown = _get_formatter().format(redacted_text, content_type)

        # ── 4. Save .md file ─────────────────────────────────────────────────
        job_dir     = Path(job.file_path).parent
        md_filename = Path(job.file_name).stem + ".md"
        md_path     = job_dir / md_filename
        md_path.write_text(markdown, encoding="utf-8")
        logger.info("Markdown saved: %s", md_path)

        # ── 5. Send email ────────────────────────────────────────────────────
        self.update_state(state="PROGRESS", meta={"step": "emailing"})
        try:
            _get_mailer().send(
                to=job.recipient_email,
                job_id=job.job_id,
                file_name=job.file_name,
                markdown=markdown,
                markdown_file=md_path,
            )
        except Exception as mail_exc:
            # Non-fatal — log and continue
            logger.warning("Email delivery failed (non-fatal): %s", mail_exc)

        # ── 6. Push to GitLab ────────────────────────────────────────────────
        self.update_state(state="PROGRESS", meta={"step": "gitlab_push"})
        gitlab_url = ""
        try:
            gitlab_url = _get_pusher().push(
                job_id=job.job_id,
                file_name=job.file_name,
                markdown=markdown,
            )
        except Exception as gl_exc:
            # Non-fatal — log and continue
            logger.warning("GitLab push failed (non-fatal): %s", gl_exc)

        # ── Done ─────────────────────────────────────────────────────────────
        completed_at = datetime.now(timezone.utc).isoformat()
        logger.info("=== Job %s COMPLETE ===", job.job_id)

        return {
            "job_id":       job.job_id,
            "file_name":    job.file_name,
            "markdown":     markdown,
            "gitlab_url":   gitlab_url,
            "completed_at": completed_at,
        }

    except Exception as exc:
        logger.error("Job %s FAILED: %s", job.job_id, exc, exc_info=True)
        # Retry up to max_retries times
        raise self.retry(exc=exc) from exc
