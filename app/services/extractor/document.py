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
    Extract text from PDF / DOCX / DOC using unstructured.io API container.
    """

    def __init__(self):
        self.api_url = f"{settings.unstructured_url}/general/v0/general"

    def extract(self, file_path: str) -> DocumentExtractionResult:
        path = Path(file_path).resolve()
        logger.info("Extracting document using unstructured API: %s", path.name)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        try:
            with open(path, "rb") as f:
                files = {"files": (path.name, f, "application/octet-stream")}
                # Use strategy="hi_res" to ensure good OCR for scanned PDFs
                # or "auto" for unstructured to decide. We use "hi_res" for safety
                # with Vietnamese scanned documents.
                data = {
                    "strategy": "hi_res",
                    "languages": "eng,vie"
                }
                
                with httpx.Client(timeout=600) as client:
                    response = client.post(self.api_url, files=files, data=data)
                    response.raise_for_status()
                    
                    elements = response.json()
                    
                    # Elements is a list of dicts, each with a 'text' field
                    extracted_texts = [el.get("text", "") for el in elements if el.get("text")]
                    
                    # Our text_preprocessor handles formatting, so we just join with double newlines
                    # so the preprocessor can do its job.
                    final_text = "\n\n".join(extracted_texts)
                    
                    method = "unstructured"
                    logger.info("Extraction complete. Method=%s, Total=%d chars", method, len(final_text))
                    
                    return DocumentExtractionResult(raw_text=final_text, method=method)
                    
        except httpx.HTTPStatusError as exc:
            logger.error("Unstructured API returned error status %s: %s", exc.response.status_code, exc.response.text)
            raise
        except Exception as exc:
            logger.error("Failed to extract using Unstructured API: %s", exc)
            raise
