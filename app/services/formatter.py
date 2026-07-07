"""
formatter.py
------------
Two-stage document formatting:

  Stage 1 (rule-based): text_preprocessor.text_to_markdown()
      - Normalize → Merge broken lines → Detect headings/lists/tables → Markdown

  Stage 2 (LLM):        Qwen2.5 via Ollama or OpenAI-compatible API
      - Receives already-structured Markdown, polishes grammar/spacing/consistency
      - If LLM is unavailable, Stage 1 output is returned as-is (still useful)
"""

import logging
from datetime import datetime

import httpx

from app.config import get_settings
from app.services.text_preprocessor import text_to_markdown

logger   = logging.getLogger(__name__)
settings = get_settings()

# ── LLM system prompt (polish only — structure already done) ──────────────────

SYSTEM_PROMPT = """You are a Markdown editor. You receive a document that has already been \
converted to Markdown using automatic rules. Your job is to lightly polish it:

- Fix any remaining spacing issues or broken words (e.g. "đồlớp" → "đồ lớp")
- Ensure heading levels are consistent and logical
- Ensure tables are well-formed
- Fix obviously broken list items
- Do NOT summarize, omit content, or add sections that don't exist in the input
- Do NOT change the meaning of any text
- Output ONLY the polished Markdown, nothing else
- Keep all redaction tags like [PERSON_REDACTED] exactly as-is

Add this footer at the very end:
---
*Processed at: {processed_at}*
"""


def _build_user_message(pre_formatted: str) -> str:
    return (
        f"--- BEGIN PRE-FORMATTED MARKDOWN ---\n"
        f"{pre_formatted[:12000]}\n"
        f"--- END PRE-FORMATTED MARKDOWN ---\n\n"
        "Please lightly polish the Markdown above. Preserve all content."
    )


# ── Ollama client ─────────────────────────────────────────────────────────────

def _call_ollama(pre_formatted: str) -> str:
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
            {"role": "user", "content": _build_user_message(pre_formatted)},
        ],
        "options": {"temperature": 0.2, "top_p": 0.9, "num_ctx": 16384},
    }
    with httpx.Client(timeout=300) as client:
        resp = client.post(url, json=payload)
        resp.raise_for_status()
        return resp.json()["message"]["content"]


# ── OpenAI-compatible API client ──────────────────────────────────────────────

def _call_openai_compatible(pre_formatted: str) -> str:
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
            {"role": "user", "content": _build_user_message(pre_formatted)},
        ],
        "temperature": 0.2,
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
    Two-stage formatter:
      1. Rule-based text_to_markdown() — always runs, produces usable output
      2. LLM polish (Qwen) — runs if available, improves quality further
    """

    def format(self, raw_text: str, content_type: str = "document") -> str:
        # ── Stage 1: Rule-based pre-formatting (always runs) ──────────────────
        pre_formatted = text_to_markdown(raw_text)
        logger.info(
            "Stage 1 complete: %d → %d chars (rule-based Markdown)",
            len(raw_text), len(pre_formatted),
        )

        # ── Stage 2: LLM polish (optional) ───────────────────────────────────
        try:
            if settings.qwen_api_url:
                result = _call_openai_compatible(pre_formatted)
            else:
                result = _call_ollama(pre_formatted)
            logger.info("Stage 2 complete: LLM polished output (%d chars)", len(result))
            return result

        except Exception as exc:
            logger.warning(
                "Stage 2 (LLM) unavailable (%s). Returning Stage 1 output.", exc
            )
            # Stage 1 output is already useful — just add the footer
            now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
            return pre_formatted + f"\n\n---\n*Processed at: {now}*"
