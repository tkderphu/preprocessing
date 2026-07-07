"""
document.py
-----------
Service wrapper around the existing extract_document.py logic.
Supports PDF, DOCX, and DOC files via Apache Tika + Tesseract OCR.
"""

import logging
import os
import sys
from pathlib import Path

from app.config import get_settings
from app.models.schemas import DocumentExtractionResult

logger   = logging.getLogger(__name__)
settings = get_settings()

# Configure Tika to use Docker container
os.environ.setdefault("TIKA_SERVER_ENDPOINT", settings.tika_server_url)

# ── Import extraction utilities ───────────────────────────────────────────────
try:
    from tika import parser as tika_parser
except ImportError:
    tika_parser = None

try:
    import pytesseract
    from PIL import Image
    import io
except ImportError:
    pytesseract = Image = io = None

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

try:
    from docx import Document as DocxDocument
except ImportError:
    DocxDocument = None

# ── Tesseract binary path (Windows fallback) ──────────────────────────────────
if sys.platform == "win32" and pytesseract is not None:
    import shutil
    _WIN_PATHS = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        r"C:\Users\FPT\AppData\Local\Programs\Tesseract-OCR\tesseract.exe",
    ]
    if not shutil.which("tesseract"):
        for _p in _WIN_PATHS:
            if os.path.isfile(_p):
                pytesseract.pytesseract.tesseract_cmd = _p
                break

_PAGE_TEXT_MIN = 20
_IMAGE_MIN_PX  = 50 * 50


def _ocr_page_images(page, doc, lang: str) -> list[str]:
    results = []
    for img_info in page.get_images(full=True):
        xref = img_info[0]
        try:
            base_image = doc.extract_image(xref)
            img        = Image.open(io.BytesIO(base_image["image"])).convert("RGB")
            if img.size[0] * img.size[1] < _IMAGE_MIN_PX:
                continue
            text = pytesseract.image_to_string(img, lang=lang).strip()
            if text:
                results.append(text)
        except Exception as exc:
            logger.debug("Could not OCR embedded image: %s", exc)
    return results


def _extract_pdf(file_path: str, lang: str, dpi: int = 200) -> str:
    doc   = fitz.open(file_path)
    total = len(doc)
    zoom  = dpi / 72
    mat   = fitz.Matrix(zoom, zoom)
    pages = []

    for page_num, page in enumerate(doc, 1):
        parts       = []
        native_text = page.get_text("text").strip()
        has_native  = len(native_text) >= _PAGE_TEXT_MIN

        if has_native:
            parts.append(native_text)

        img_texts = _ocr_page_images(page, doc, lang)
        parts.extend(img_texts)

        # Full-page OCR fallback for fully scanned pages
        if not has_native and not img_texts:
            pix  = page.get_pixmap(matrix=mat, alpha=False)
            img  = Image.open(io.BytesIO(pix.tobytes("png")))
            text = pytesseract.image_to_string(img, lang=lang).strip()
            if text:
                parts.append(text)
            elif native_text:
                parts.append(native_text)

        if parts:
            pages.append("\n".join(parts))

        logger.info("  PDF page %d/%d processed", page_num, total)

    doc.close()
    return "\n\n".join(pages)


def _extract_docx_images(file_path: str, lang: str) -> str:
    doc   = DocxDocument(file_path)
    texts = []
    for rel in doc.part.rels.values():
        if "image" in rel.reltype:
            try:
                img  = Image.open(io.BytesIO(rel.target_part.blob))
                text = pytesseract.image_to_string(img, lang=lang).strip()
                if text:
                    texts.append(text)
            except Exception as exc:
                logger.warning("Could not OCR DOCX image: %s", exc)
    return "\n\n".join(texts)


class DocumentExtractor:
    """
    Extract text from PDF / DOCX / DOC using Apache Tika + Tesseract OCR.
    """

    def __init__(self):
        self.lang = settings.tesseract_lang

    def extract(self, file_path: str) -> DocumentExtractionResult:
        path   = Path(file_path).resolve()
        suffix = path.suffix.lower()

        logger.info("Extracting document: %s", path.name)

        # ── Step 1: Apache Tika ───────────────────────────────────────────────
        tika_text = ""
        if tika_parser:
            try:
                parsed    = tika_parser.from_file(str(path), settings.tika_server_url)
                tika_text = (parsed.get("content") or "").strip()
                logger.info("Tika extracted %d chars", len(tika_text))
            except Exception as exc:
                logger.warning("Tika failed: %s", exc)

        tika_ok = len(tika_text.strip()) >= 50

        # ── Step 2: OCR ───────────────────────────────────────────────────────
        method     = "tika"
        final_text = tika_text

        if suffix == ".pdf" and fitz and pytesseract:
            try:
                pdf_text = _extract_pdf(str(path), self.lang)
                if pdf_text:
                    final_text = pdf_text
                    method     = "ocr" if not tika_ok else "tika+ocr"
            except Exception as exc:
                logger.warning("PDF OCR failed: %s", exc)

        elif suffix in {".docx", ".doc"} and DocxDocument and pytesseract:
            parts = []
            if tika_ok:
                parts.append(tika_text)
            try:
                img_text = _extract_docx_images(str(path), self.lang)
                if img_text:
                    parts.append(img_text)
                    method = "tika+ocr" if tika_ok else "ocr"
            except Exception as exc:
                logger.warning("DOCX image OCR failed: %s", exc)
            final_text = "\n\n".join(parts)

        logger.info("Extraction complete. Method=%s, Total=%d chars", method, len(final_text))
        return DocumentExtractionResult(raw_text=final_text, method=method)
