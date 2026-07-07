"""
redaction.py
------------
Service wrapper around the GLiNER-based VietnameseRedactor.
"""

import logging
import re
from typing import Any

from app.models.schemas import RedactionResult

logger = logging.getLogger(__name__)

# ── Patterns ──────────────────────────────────────────────────────────────────

EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PHONE_PATTERN = re.compile(r"(?:\+84|0)[35789]\d{8}")
CCCD_PATTERN  = re.compile(r"\b\d{12}\b")
CMND_PATTERN  = re.compile(r"\b\d{9}\b")


def _load_gliner():
    try:
        from gliner import GLiNER
        model = GLiNER.from_pretrained("urchade/gliner_multi-v2.1")
        logger.info("GLiNER model loaded.")
        return model
    except Exception as exc:
        logger.warning("GLiNER unavailable (%s). Only regex redaction will run.", exc)
        return None


class RedactionService:
    """
    PII redaction combining:
    - Regex rules for email, phone, CCCD, CMND
    - GLiNER NER for person, location, organization (multilingual)
    """

    LABELS = ["person", "location", "organization"]

    def __init__(self):
        self._model = None

    def _get_model(self):
        if self._model is None:
            self._model = _load_gliner()
        return self._model

    # ── Detection ─────────────────────────────────────────────────────────────

    def _detect_regex(self, text: str) -> list[dict[str, Any]]:
        entities = []
        for m in EMAIL_PATTERN.finditer(text):
            entities.append({"start": m.start(), "end": m.end(), "label": "EMAIL"})
        for m in PHONE_PATTERN.finditer(text):
            entities.append({"start": m.start(), "end": m.end(), "label": "PHONE"})
        for m in CCCD_PATTERN.finditer(text):
            entities.append({"start": m.start(), "end": m.end(), "label": "CCCD"})
        for m in CMND_PATTERN.finditer(text):
            entities.append({"start": m.start(), "end": m.end(), "label": "CMND"})
        return entities

    def _detect_ai(self, text: str) -> list[dict[str, Any]]:
        model = self._get_model()
        if model is None:
            return []
        label_map = {"person": "PERSON", "location": "ADDRESS", "organization": "ORGANIZATION"}
        entities = []
        try:
            # GLiNER has a 512 token limit — chunk long texts
            chunk_size = 2000
            for i in range(0, len(text), chunk_size):
                chunk  = text[i: i + chunk_size]
                offset = i
                for item in model.predict_entities(chunk, self.LABELS):
                    label = label_map.get(item["label"].lower())
                    if label:
                        entities.append({
                            "start": item["start"] + offset,
                            "end":   item["end"]   + offset,
                            "label": label,
                        })
        except Exception as exc:
            logger.warning("GLiNER prediction failed: %s", exc)
        return entities

    @staticmethod
    def _merge_entities(entities: list[dict]) -> list[dict]:
        entities.sort(key=lambda x: (x["start"], -(x["end"] - x["start"])))
        merged, current_end = [], -1
        for e in entities:
            if e["start"] >= current_end:
                merged.append(e)
                current_end = e["end"]
        return merged

    # ── Public API ────────────────────────────────────────────────────────────

    def redact(self, text: str) -> RedactionResult:
        """Detect and redact all PII from *text*."""
        logger.info("Running PII redaction on %d chars...", len(text))

        all_entities = self._merge_entities(
            self._detect_regex(text) + self._detect_ai(text)
        )

        # Apply redactions from end → start to preserve indices
        redacted = text
        for e in sorted(all_entities, key=lambda x: x["start"], reverse=True):
            replacement = f"[{e['label']}_REDACTED]"
            redacted = redacted[: e["start"]] + replacement + redacted[e["end"] :]

        logger.info(
            "Redaction complete. %d entities found.", len(all_entities)
        )
        return RedactionResult(redacted_text=redacted, entities=all_entities)


# ── Module-level singleton ────────────────────────────────────────────────────
_redaction_service: RedactionService | None = None


def get_redaction_service() -> RedactionService:
    global _redaction_service
    if _redaction_service is None:
        _redaction_service = RedactionService()
    return _redaction_service
