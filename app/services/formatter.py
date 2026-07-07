"""
formatter.py
------------
Format extracted (and redacted) text into a structured Markdown document
using the Qwen2.5 model via Ollama (local) or an OpenAI-compatible API.

Output template:
  # [Document Title]
  ## Source
  ## Meeting Date
  ## Participants
  ## Summary
  ## Key Points
  ## Action Items
"""

import logging
from datetime import datetime

import httpx

from app.config import get_settings

logger   = logging.getLogger(__name__)
settings = get_settings()

# ── Text pre-processor ────────────────────────────────────────────────────────

def clean_text(text: str) -> str:
    """
    Clean fragmented OCR output before sending to the LLM.

    Problems fixed:
    1. Single-word lines (scanned columns split every word onto its own line)
       → joined back into flowing paragraphs.
    2. Diagram/table OCR garbage (lines with >60% non-alphabetic chars)
       → removed so they don't confuse the LLM.
    3. Excessive blank lines → collapsed to max 2.
    """
    lines = text.splitlines()
    cleaned: list[str] = []
    paragraph_buffer: list[str] = []

    def _is_garbage(line: str) -> bool:
        stripped = line.strip()
        if len(stripped) < 3:
            return False
        alpha = sum(1 for c in stripped if c.isalpha())
        ratio = alpha / len(stripped)
        # Lines with <40% alphabetic chars = likely diagram/table OCR garbage
        return ratio < 0.40

    def _flush_buffer() -> None:
        if paragraph_buffer:
            cleaned.append(" ".join(paragraph_buffer))
            paragraph_buffer.clear()

    for line in lines:
        stripped = line.strip()

        if not stripped:
            _flush_buffer()
            cleaned.append("")
            continue

        if _is_garbage(stripped):
            continue

        words = stripped.split()

        if len(words) == 1:
            # Single-word line — likely a column-layout fragment; buffer it
            paragraph_buffer.append(stripped)
        else:
            _flush_buffer()
            cleaned.append(stripped)

    _flush_buffer()

    # Collapse runs of >2 blank lines
    result_lines: list[str] = []
    blank_count = 0
    for ln in cleaned:
        if ln == "":
            blank_count += 1
            if blank_count <= 2:
                result_lines.append(ln)
        else:
            blank_count = 0
            result_lines.append(ln)

    return "\n".join(result_lines).strip()


# ── Prompt ────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a document formatter. Your ONLY job is to clean up and reformat raw text extracted from a PDF or DOCX file into clean, readable Markdown.

RULES:
- PRESERVE all original content. Do NOT summarize, omit, or paraphrase anything.
- Fix broken formatting: join words that were split across lines, fix spacing, fix capitalization where obvious.
- Detect and apply proper Markdown structure: headings (#, ##, ###), bullet lists, numbered lists, tables (if present), bold/italic where appropriate.
- Remove clearly garbage characters from OCR (random symbols, broken Unicode, garbled diagram text).
- Keep all names, numbers, dates, technical terms, and code exactly as they appear.
- Do NOT add any commentary, summary sections, or metadata that was not in the original.
- Output ONLY the cleaned Markdown content. No preamble, no explanation.
- Add a single line at the very end: `---\\n*Processed at: {processed_at}*`
"""


def _build_user_message(raw_text: str, content_type: str) -> str:
    return (
        f"Content type: {content_type}\n\n"
        f"--- BEGIN RAW TEXT ---\n{raw_text[:12000]}\n--- END RAW TEXT ---\n\n"
        "Clean up and reformat the above text into proper Markdown. "
        "Preserve ALL content. Do not summarize."
    )


# ── Ollama client ─────────────────────────────────────────────────────────────

def _call_ollama(raw_text: str, content_type: str) -> str:
    url     = f"{settings.ollama_base_url}/api/chat"
    payload = {
        "model": settings.qwen_model,
        "stream": False,
        "messages": [
            {
                "role": "system",
                "content": SYSTEM_PROMPT.format(
                    processed_at=datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
                ),
            },
            {
                "role": "user",
                "content": _build_user_message(raw_text, content_type),
            },
        ],
        "options": {
            "temperature": 0.3,
            "top_p": 0.9,
            "num_ctx": 16384,
        },
    }
    with httpx.Client(timeout=300) as client:
        resp = client.post(url, json=payload)
        resp.raise_for_status()
        return resp.json()["message"]["content"]


# ── OpenAI-compatible API client ──────────────────────────────────────────────

def _call_openai_compatible(raw_text: str, content_type: str) -> str:
    url     = f"{settings.qwen_api_url}/chat/completions"
    headers = {"Authorization": f"Bearer {settings.qwen_api_key}"}
    payload = {
        "model": settings.qwen_model,
        "messages": [
            {
                "role": "system",
                "content": SYSTEM_PROMPT.format(
                    processed_at=datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
                ),
            },
            {
                "role": "user",
                "content": _build_user_message(raw_text, content_type),
            },
        ],
        "temperature": 0.3,
        "top_p": 0.9,
        "max_tokens": 4096,
    }
    with httpx.Client(timeout=300) as client:
        resp = client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]


# ── Public API ────────────────────────────────────────────────────────────────

class MarkdownFormatter:
    """
    Format raw extracted text into structured Markdown using Qwen2.5.
    Cleans fragmented OCR text before sending to the LLM.
    Falls back to a minimal template if the LLM is unavailable.
    """

    def format(self, raw_text: str, content_type: str = "document") -> str:
        # Pre-process: fix word-per-line fragmentation and remove OCR garbage
        cleaned = clean_text(raw_text)
        logger.info(
            "Text cleaned: %d → %d chars. Formatting with Qwen (%s)...",
            len(raw_text), len(cleaned), settings.qwen_model,
        )
        try:
            if settings.qwen_api_url:
                markdown = _call_openai_compatible(cleaned, content_type)
            else:
                markdown = _call_ollama(cleaned, content_type)

            logger.info("LLM formatting complete (%d chars output).", len(markdown))
            return markdown

        except Exception as exc:
            logger.warning("LLM formatting failed (%s). Using fallback template.", exc)
            return self._fallback_template(cleaned, content_type)

    @staticmethod
    def _fallback_template(raw_text: str, content_type: str) -> str:
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        return (
            f"# Document\n\n"
            f"## Source\n- **File type**: {content_type}\n- **Processed at**: {now}\n\n"
            f"## Meeting Date\nUnknown\n\n"
            f"## Participants\nUnknown\n\n"
            f"## Summary\n*(LLM formatting unavailable — raw text below)*\n\n"
            f"## Raw Content\n\n```\n{raw_text[:5000]}\n```\n\n"
            f"---\n*Auto-generated by Document Intelligence Pipeline*\n"
        )
