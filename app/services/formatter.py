"""
formatter.py
------------
Two-stage document formatting:

  Stage 1 (rule-based): text_preprocessor.text_to_markdown()
      - Normalize → Merge broken lines → Detect headings/lists/tables → Markdown

  Stage 2 (LLM):        Groq Cloud API (Llama 3)
      - Splits the Markdown into chunks ≤ groq_chunk_size characters
      - Calls Groq once per chunk to polish grammar/spacing/consistency
      - Chunks are split on paragraph/section boundaries to avoid mid-sentence cuts
      - If LLM is unavailable, Stage 1 output is returned as-is (still useful)
"""

import logging
import time
from datetime import datetime
from typing import Generator

import httpx

from app.config import get_settings
from app.services.text_preprocessor import text_to_markdown

logger   = logging.getLogger(__name__)
settings = get_settings()

# ── LLM system prompt (polish only — structure already done) ──────────────────

SYSTEM_PROMPT = """You are a Vietnamese document formatter. You receive a partially-formatted Markdown document extracted from a PDF via OCR. Clean it up and output corrected Markdown following these STRICT rules:

1. **Vietnamese word spacing**: Fix words that are incorrectly joined without spaces (e.g. "hệthống" → "hệ thống", "giỏhàng" → "giỏ hàng", "đồlớp" → "đồ lớp", "Biểuđồ" → "Biểu đồ"). Apply this throughout the entire document.

2. **Page numbers**: Remove standalone page numbers that appear as isolated lines (e.g. a line containing only "1", "2", "3", or "Trang 1").

3. **Broken words across lines**: Fix hyphenated breaks (e.g. "updatePro-\\nfile()" → "updateProfile()", "com-\\nputeTotal()" → "computeTotal()"). The broken word is already joined in the input — just remove the hyphen artifact if still present.

4. **Tables**: 
   - Preserve correct table structure. If a table has 3 columns (e.g. Lớp | Thuộc tính | Methods), keep all 3 columns.
   - Each class row should have: | ClassName | attributes | methods |
   - Do NOT merge all content into one column.
   - If the table structure is wrong, rebuild it correctly from the content.

5. **Lists under headings**: Each bullet item under a section heading (Chương X, Bảng X, etc.) must appear on its own line as either:
   - `- item text` (bullet), OR
   - `1. item text` (numbered)
   Never run multiple items together on one line.

6. **Headings**: Keep the heading hierarchy (# ## ### ####). Do not change heading levels.

7. **Redaction tags**: Keep `[PERSON_REDACTED]`, `[ADDRESS_REDACTED]`, `[EMAIL_REDACTED]` exactly as-is. Do not remove or alter them.

8. **Preserve all content**: Do NOT summarize, omit, or paraphrase any content.

9. **Output**: Return ONLY the corrected Markdown. No explanations, no preamble.
"""

FINAL_CHUNK_SUFFIX = """
Add this footer at the end:
---
*Processed at: {processed_at}*
"""


# ── Text chunker ──────────────────────────────────────────────────────────────

def _split_into_chunks(text: str, max_chars: int) -> Generator[str, None, None]:
    """
    Split *text* into chunks of at most *max_chars* characters.

    Strategy (in priority order):
      1. Split on double-newline (paragraph/section boundary) — preferred
      2. Split on single newline — fallback
      3. Hard split at max_chars — last resort (very long single line)

    Yields non-empty chunks.
    """
    if not text:
        return

    # Walk through the text respecting paragraph boundaries
    start = 0
    length = len(text)

    while start < length:
        end = start + max_chars

        if end >= length:
            # Last piece
            chunk = text[start:]
            if chunk.strip():
                yield chunk
            break

        # Look backward from `end` for the best split point
        # Priority 1: double newline (paragraph break)
        split_pos = text.rfind('\n\n', start, end)
        if split_pos != -1 and split_pos > start:
            chunk = text[start:split_pos]
            if chunk.strip():
                yield chunk
            start = split_pos + 2   # skip the '\n\n'
            continue

        # Priority 2: single newline
        split_pos = text.rfind('\n', start, end)
        if split_pos != -1 and split_pos > start:
            chunk = text[start:split_pos]
            if chunk.strip():
                yield chunk
            start = split_pos + 1
            continue

        # Priority 3: hard cut at max_chars
        chunk = text[start:end]
        if chunk.strip():
            yield chunk
        start = end


# ── Groq API client ─────────────────────────────────────────────────────────────

def _build_user_message(chunk: str, is_last: bool, processed_at: str) -> str:
    """Build the user message for a single chunk."""
    footer_instruction = (
        FINAL_CHUNK_SUFFIX.format(processed_at=processed_at)
        if is_last
        else "Do NOT add a footer — this is not the final chunk."
    )
    return (
        f"--- BEGIN MARKDOWN CHUNK ---\n"
        f"{chunk}\n"
        f"--- END MARKDOWN CHUNK ---\n\n"
        f"Please lightly polish the Markdown above. Preserve all content.\n"
        f"{footer_instruction}"
    )


def _call_groq_once(chunk: str, is_last: bool, processed_at: str) -> str:
    """Send a single chunk to Groq and return the polished text."""
    url = "https://api.groq.com/openai/v1/chat/completions"
    if not settings.groq_api_key:
        raise ValueError("GROQ_API_KEY is not set")

    headers = {"Authorization": f"Bearer {settings.groq_api_key}"}
    payload = {
        "model": settings.groq_model,
        "messages": [
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": _build_user_message(chunk, is_last, processed_at),
            },
        ],
        "temperature": 0.2,
        "top_p": 0.9,
        "max_tokens": 4096,
    }
    with httpx.Client(timeout=300) as client:
        resp = client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]


def _call_groq(pre_formatted: str) -> str:
    """
    Split *pre_formatted* into chunks and call Groq once per chunk.
    Results are joined in order and returned as a single string.

    A small delay is added between calls to respect Groq's rate limits.
    """
    chunk_size  = settings.groq_chunk_size
    processed_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    chunks = list(_split_into_chunks(pre_formatted, chunk_size))
    total  = len(chunks)

    if total == 0:
        return pre_formatted

    logger.info("Groq Stage 2: %d chunk(s) of ≤%d chars each", total, chunk_size)

    polished_parts: list[str] = []
    for idx, chunk in enumerate(chunks):
        is_last = idx == total - 1
        logger.debug("  → chunk %d/%d (%d chars)", idx + 1, total, len(chunk))

        polished = _call_groq_once(chunk, is_last, processed_at)
        polished_parts.append(polished)

        # Respect Groq rate limits (skip delay after last chunk)
        if not is_last:
            time.sleep(1)

    return "\n\n".join(polished_parts)


# ── Public API ────────────────────────────────────────────────────────────────

class MarkdownFormatter:
    """
    Two-stage formatter:
      1. Rule-based text_to_markdown() — always runs, produces usable output
      2. LLM polish (Groq) — splits into chunks and calls API in a loop
    """

    def format(self, raw_text: str, content_type: str = "document") -> str:
        # ── Stage 1: Rule-based pre-formatting (always runs) ──────────────────
        pre_formatted = text_to_markdown(raw_text)
        logger.info(
            "Stage 1 complete: %d → %d chars (rule-based Markdown)",
            len(raw_text), len(pre_formatted),
        )

        # ── Stage 2: LLM polish (chunked) ────────────────────────────────────
        try:
            result = _call_groq(pre_formatted)
            logger.info("Stage 2 complete: LLM polished output (%d chars)", len(result))
            return result

        except Exception as exc:
            logger.warning(
                "Stage 2 (LLM) unavailable (%s). Returning Stage 1 output.", exc
            )
            # Stage 1 output is already useful — just add the footer
            now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
            return pre_formatted + f"\n\n---\n*Processed at: {now}*"
