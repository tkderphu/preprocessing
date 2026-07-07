# 📄 Document Intelligence Pipeline

A production-ready **FastAPI + Celery + RabbitMQ** pipeline that processes audio recordings and documents (PDF/DOCX), extracts content, redacts PII, formats to structured Markdown, then delivers results via email and GitHub.

---

## Architecture

```
Client ──POST /upload──► FastAPI API ──► RabbitMQ ──► Celery Worker
                                                            │
                    ┌───────────────────────────────────────┤
                    │                                       │
              Audio files                          PDF / DOCX files
          faster-whisper                        Apache Tika + Tesseract
        + pyannote diarization                                │
                    │                                       │
                    └──────────────┬────────────────────────┘
                                   │
                           PII Redaction (GLiNER)
                                   │
                       Qwen2.5 Markdown Formatter
                                   │
                    ┌──────────────┴──────────────┐
                    │                             │
              Email (SMTP)              GitHub Push (PAT)
```

---

## Features

| Feature | Technology |
|---|---|
| File Upload API | FastAPI + multipart |
| Message Queue | RabbitMQ (aio-pika) |
| Task Worker | Celery |
| Audio Transcription | faster-whisper |
| Speaker Diarization | pyannote.audio (optional, needs HF token) |
| PDF Extraction | Apache Tika + PyMuPDF + Tesseract |
| DOCX Extraction | Apache Tika + python-docx + Tesseract |
| PII Redaction | GLiNER (multilingual NER) + regex |
| Markdown Formatting | Qwen2.5 via Ollama |
| Email Delivery | aiosmtplib (Gmail / SMTP) |
| GitHub Push | PyGitHub |

---

## Quick Start

### 1. Configure

```bash
cp .env.example .env
# Edit .env with your credentials
```

### 2. Start all services

```bash
docker compose up -d
```

### 3. Pull the Qwen model (first run only)

```bash
docker compose exec ollama ollama pull qwen2.5:7b
```

### 4. Upload a file

```bash
curl -X POST http://localhost:8000/api/v1/upload \
  -F "file=@/path/to/meeting.mp3" \
  -F "recipient_email=you@example.com"
```

Response:
```json
{"job_id": "abc123", "status": "queued"}
```

### 5. Poll for results

```bash
curl http://localhost:8000/api/v1/jobs/abc123
```

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/api/v1/upload` | Upload file for processing |
| `GET` | `/api/v1/jobs/{job_id}` | Poll job status / get result |
| `DELETE` | `/api/v1/jobs/{job_id}` | Cancel a queued job |
| `GET` | `/docs` | Swagger UI |

### POST /api/v1/upload

| Field | Type | Description |
|---|---|---|
| `file` | file | Audio (mp3/wav/m4a/ogg) or PDF/DOCX |
| `recipient_email` | string (opt) | Override recipient email |
| `github_branch` | string (opt) | Override GitHub branch |

---

## Supported File Types

| Type | Extensions | Extractor |
|---|---|---|
| Audio | `.mp3 .wav .ogg .m4a .flac .webm .mp4` | faster-whisper + pyannote |
| PDF | `.pdf` | Tika + PyMuPDF + Tesseract |
| Word | `.docx .doc` | Tika + python-docx + Tesseract |

---

## Markdown Output Template

Each processed file is formatted as:

```markdown
# [Document Title]

## Source
- File type: ...
- Processed at: ...

## Meeting Date
...

## Participants
- Person A (role)
- Person B (role)

## Summary
...

## Key Points
- ...

## Action Items
- [ ] Task — Owner
```

---

## Service URLs (Docker)

| Service | URL | Credentials |
|---|---|---|
| API | http://localhost:8000 | — |
| API Docs | http://localhost:8000/docs | — |
| RabbitMQ UI | http://localhost:15672 | guest / guest |
| Ollama | http://localhost:11434 | — |
| Tika | http://localhost:9998 | — |

---

## Configuration (.env)

| Variable | Default | Description |
|---|---|---|
| `WHISPER_MODEL_SIZE` | `base` | tiny/base/small/medium/large-v3 |
| `WHISPER_DEVICE` | `cpu` | cpu or cuda |
| `HF_TOKEN` | — | HuggingFace token (speaker diarization) |
| `QWEN_MODEL` | `qwen2.5:7b` | Ollama model name |
| `QWEN_API_URL` | — | External API URL (overrides Ollama) |
| `SMTP_HOST` | `smtp.gmail.com` | SMTP server |
| `GITHUB_REPO` | — | `owner/repo` |
| `GITHUB_TOKEN` | — | PAT with repo scope |

---

## Scaling Workers

```bash
docker compose up --scale worker=3
```

Each worker runs 1 concurrent task (`--concurrency=1`) due to ML model memory requirements.

---

## Development (local)

```bash
# Install deps
pip install -r requirements.txt

# Start infrastructure only
docker compose up rabbitmq redis tika ollama -d

# Run API
uvicorn app.main:app --reload --port 8000

# Run worker
celery -A app.worker.celery_app worker --loglevel=info --concurrency=1
```
