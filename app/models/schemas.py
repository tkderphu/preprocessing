"""
schemas.py
----------
Pydantic models for API request/response and internal job messages.
"""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


# ── Enums ─────────────────────────────────────────────────────────────────────

class FileType(str, Enum):
    AUDIO = "audio"
    PDF   = "pdf"
    DOCX  = "docx"
    DOC   = "doc"


class JobStatus(str, Enum):
    QUEUED     = "queued"
    PROCESSING = "processing"
    DONE       = "done"
    FAILED     = "failed"


# ── Job message (published to RabbitMQ) ──────────────────────────────────────

class JobMessage(BaseModel):
    job_id:     str      = Field(default_factory=lambda: uuid4().hex)
    file_path:  str
    file_name:  str
    file_type:  FileType
    created_at: datetime = Field(default_factory=datetime.utcnow)
    # Optional per-job overrides
    recipient_email: str  = ""
    github_branch:   str  = ""


# ── Upload API ────────────────────────────────────────────────────────────────

class UploadResponse(BaseModel):
    job_id:  str
    status:  JobStatus = JobStatus.QUEUED
    message: str = "File uploaded and queued for processing."


# ── Job status API ────────────────────────────────────────────────────────────

class JobResult(BaseModel):
    job_id:     str
    status:     JobStatus
    file_name:  str        = ""
    markdown:   str        = ""          # final formatted Markdown
    error:      str        = ""
    created_at: str        = ""
    completed_at: str      = ""


# ── Extraction results (internal) ─────────────────────────────────────────────

class SpeakerSegment(BaseModel):
    speaker: str
    start:   float
    end:     float
    text:    str


class AudioExtractionResult(BaseModel):
    raw_transcript: str
    segments:       list[SpeakerSegment] = []


class DocumentExtractionResult(BaseModel):
    raw_text: str
    method:   str   # "tika" | "ocr" | "tika+ocr"


class RedactionResult(BaseModel):
    redacted_text: str
    entities:      list[dict[str, Any]] = []
