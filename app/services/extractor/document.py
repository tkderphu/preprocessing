"""
document.py
-----------
Service wrapper for Document Extraction using unstructured.io via Docker.
Supports PDF, DOCX, and DOC files.
"""

import logging
from pathlib import Path
import httpx

from app.config import get_settings
from app.models.schemas import DocumentExtractionResult

logger = logging.getLogger(__name__)
settings = get_settings()


class DocumentExtractor:
    """
    Extract text from PDF / DOCX / DOC using Apache Tika container.
    """

    def __init__(self):
        self.api_url = f"{settings.tika_url}/tika"

    def extract(self, file_path: str) -> DocumentExtractionResult:
        path = Path(file_path).resolve()
        logger.info("Extracting document using Apache Tika: %s", path.name)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        try:
            with open(path, "rb") as f:
                headers = {"Accept": "text/plain"}
                with httpx.Client(timeout=600) as client:
                    response = client.put(self.api_url, content=f, headers=headers)
                    response.raise_for_status()
                    
                    final_text = response.text
                    method = "apache_tika"
                    logger.info("Extraction complete. Method=%s, Total=%d chars", method, len(final_text))
                    
                    return DocumentExtractionResult(raw_text=final_text, method=method)
                    
        except httpx.HTTPStatusError as exc:
            logger.error("Apache Tika returned error status %s: %s", exc.response.status_code, exc.response.text)
            raise
        except Exception as exc:
            logger.error("Failed to extract using Apache Tika: %s", exc)
            raise
