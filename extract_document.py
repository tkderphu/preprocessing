"""
Document Text Extractor
=======================
Extracts text from PDF and DOCX files using:
  - Apache Tika  → for embedded/selectable text
  - Tesseract OCR → for image-based / scanned content

Dependencies (install via requirements.txt):
    tika
    pytesseract
    Pillow
    PyMuPDF  (fitz)  – used to render PDF pages to images for OCR
    python-docx      – used to detect images inside DOCX files
"""

import os
import sys
import io
import logging
from pathlib import Path
from typing import Optional

# ── Third-party ───────────────────────────────────────────────────────────────
try:
    from tika import parser as tika_parser          # Apache Tika
except ImportError:
    tika_parser = None

try:
    import pytesseract                              # Tesseract OCR wrapper
    from PIL import Image

    # ── Windows: auto-detect Tesseract install location ──────────────────────
    if sys.platform == "win32":
        import shutil
        _TESSERACT_WIN_PATHS = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            r"C:\Users\FPT\AppData\Local\Programs\Tesseract-OCR\tesseract.exe",
        ]
        if not shutil.which("tesseract"):
            for _p in _TESSERACT_WIN_PATHS:
                if os.path.isfile(_p):
                    pytesseract.pytesseract.tesseract_cmd = _p
                    break
except ImportError:
    pytesseract = None
    Image = None

try:
    import fitz                                     # PyMuPDF – PDF → image rendering
except ImportError:
    fitz = None

try:
    from docx import Document as DocxDocument       # python-docx – DOCX image extraction
    from docx.oxml.ns import qn
except ImportError:
    DocxDocument = None

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Helper utilities
# ─────────────────────────────────────────────────────────────────────────────

def _check_dependencies() -> None:
    """Raise ImportError with a clear message if required libraries are missing."""
    missing = []
    if tika_parser is None:
        missing.append("tika")
    if pytesseract is None:
        missing.append("pytesseract")
    if Image is None:
        missing.append("Pillow")
    if fitz is None:
        missing.append("PyMuPDF")
    if DocxDocument is None:
        missing.append("python-docx")
    if missing:
        raise ImportError(
            f"Missing required packages: {', '.join(missing)}. "
            "Run:  pip install -r requirements.txt"
        )


def _is_meaningful_text(text: Optional[str], min_chars: int = 50) -> bool:
    """Return True if *text* contains at least *min_chars* non-whitespace characters."""
    if not text:
        return False
    return len(text.strip()) >= min_chars


# ─────────────────────────────────────────────────────────────────────────────
# Tika extraction
# ─────────────────────────────────────────────────────────────────────────────

def extract_text_with_tika(file_path: str) -> str:
    """
    Use Apache Tika to pull selectable/embedded text from *file_path*.

    Returns the extracted text string (may be empty / whitespace-only
    if the file is purely image-based).
    """
    logger.info("Running Apache Tika on: %s", file_path)
    parsed = tika_parser.from_file(file_path)
    content = parsed.get("content") or ""
    return content.strip()


# ─────────────────────────────────────────────────────────────────────────────
# PDF extraction – full per-page (native text + embedded image OCR)
# ─────────────────────────────────────────────────────────────────────────────

_PAGE_TEXT_MIN_CHARS = 20     # chars to treat a page as "has selectable text"
_IMAGE_MIN_PIXELS   = 50 * 50 # ignore tiny icons / decorative images


def _ocr_page_images(page: "fitz.Page", doc: "fitz.Document", dpi: int) -> list[str]:
    """
    Extract every image embedded on *page*, run Tesseract OCR on each one,
    and return a list of non-empty OCR strings.
    """
    ocr_results: list[str] = []
    image_list = page.get_images(full=True)

    for img_index, img_info in enumerate(image_list):
        xref = img_info[0]
        try:
            base_image = doc.extract_image(xref)
            img_bytes  = base_image["image"]
            img        = Image.open(io.BytesIO(img_bytes)).convert("RGB")

            # Skip tiny decorative images (icons, bullets, etc.)
            w, h = img.size
            if w * h < _IMAGE_MIN_PIXELS:
                continue

            ocr_text = pytesseract.image_to_string(img, lang="eng+vie").strip()
            if ocr_text:
                logger.debug(
                    "    Embedded image %d (%dx%d): OCR yielded %d chars",
                    img_index + 1, w, h, len(ocr_text),
                )
                ocr_results.append(ocr_text)
        except Exception as exc:
            logger.debug("    Could not OCR embedded image %d: %s", img_index + 1, exc)

    return ocr_results


def _extract_pdf_pages(file_path: str, dpi: int = 200) -> str:
    """
    Extract text from every PDF page combining TWO sources per page:

    1. **Native text layer** – selectable text embedded by the PDF author.
       Extracted directly via PyMuPDF (fast, lossless).

    2. **Embedded image OCR** – any images placed on the page (diagrams,
       screenshots, scanned figures) are individually OCR'd with Tesseract.

    Both sources are used on *every* page, so a page that mixes text paragraphs
    with architecture diagrams / screenshots will have all content captured.

    For pages with *no* native text at all (fully scanned), the whole page is
    rendered at *dpi* resolution and OCR'd as a single image.

    Returns concatenated text for the whole document.
    """
    doc   = fitz.open(file_path)
    total = len(doc)
    logger.info("Processing PDF (%d pages): %s", total, file_path)

    zoom = dpi / 72
    mat  = fitz.Matrix(zoom, zoom)
    page_texts: list[str] = []

    for page_num, page in enumerate(doc, start=1):
        parts: list[str] = []

        # ── 1. Native selectable text ─────────────────────────────────────────
        native_text = page.get_text("text").strip()
        has_native  = len(native_text) >= _PAGE_TEXT_MIN_CHARS

        if has_native:
            parts.append(native_text)
            logger.info(
                "  Page %d/%d: native text (%d chars)", page_num, total, len(native_text)
            )

        # ── 2. OCR every embedded image on this page ──────────────────────────
        img_ocr_texts = _ocr_page_images(page, doc, dpi)
        if img_ocr_texts:
            logger.info(
                "  Page %d/%d: %d embedded image(s) OCR'd",
                page_num, total, len(img_ocr_texts),
            )
            parts.extend(img_ocr_texts)

        # ── 3. Whole-page OCR fallback for fully scanned pages ────────────────
        if not has_native and not img_ocr_texts:
            logger.info(
                "  Page %d/%d: no text / images found → whole-page OCR",
                page_num, total,
            )
            pix      = page.get_pixmap(matrix=mat, alpha=False)
            img      = Image.open(io.BytesIO(pix.tobytes("png")))
            fallback = pytesseract.image_to_string(img, lang="eng+vie").strip()
            if fallback:
                parts.append(fallback)
            elif native_text:
                parts.append(native_text)

        if parts:
            page_texts.append("\n".join(parts))

    doc.close()
    return "\n\n".join(page_texts)


# ─────────────────────────────────────────────────────────────────────────────
# OCR extraction – DOCX
# ─────────────────────────────────────────────────────────────────────────────

def _ocr_docx_images(file_path: str) -> str:
    """
    Extract every embedded image from a DOCX file and run Tesseract OCR on each.

    Returns concatenated OCR text for all images found.
    """
    logger.info("Extracting images from DOCX for OCR: %s", file_path)
    doc = DocxDocument(file_path)
    texts: list[str] = []

    # Iterate over all relationships to find image parts
    for rel in doc.part.rels.values():
        if "image" in rel.reltype:
            img_bytes = rel.target_part.blob
            try:
                img = Image.open(io.BytesIO(img_bytes))
                img_text = pytesseract.image_to_string(img, lang="eng+vie")
                if img_text.strip():
                    texts.append(img_text.strip())
            except Exception as exc:
                logger.warning("  Could not OCR an embedded image: %s", exc)

    return "\n\n".join(texts)


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def extract_text_from_document(
    file_path: str,
    output_txt_path: Optional[str] = None,
    tika_min_chars: int = 50,
    ocr_dpi: int = 200,
) -> str:
    """
    Extract text from a PDF or DOCX file using Apache Tika and/or Tesseract OCR.

    Strategy
    --------
    1. Try Apache Tika first.
       • If it returns meaningful selectable text → use it.
    2. Fall back to Tesseract OCR.
       • For PDFs  → render pages to images with PyMuPDF, then OCR each page.
       • For DOCX  → extract embedded images, then OCR each image.
    3. If BOTH sources yield text → concatenate (Tika text first, then OCR text).

    Parameters
    ----------
    file_path       : Path to the PDF or DOCX file.
    output_txt_path : Optional path to save the extracted text as a .txt file.
                      If omitted, the text is returned but NOT saved automatically.
    tika_min_chars  : Minimum non-whitespace characters required for Tika's result
                      to be considered "meaningful" (default 50).
    ocr_dpi         : Resolution used when rendering PDF pages for OCR (default 200).

    Returns
    -------
    str : All extracted text.

    Raises
    ------
    ValueError      : If the file extension is not .pdf or .docx/.doc.
    FileNotFoundError: If *file_path* does not exist.
    ImportError     : If required third-party packages are missing.
    """
    _check_dependencies()

    path = Path(file_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    suffix = path.suffix.lower()
    if suffix not in {".pdf", ".docx", ".doc"}:
        raise ValueError(
            f"Unsupported file type '{suffix}'. Only .pdf, .doc, .docx are supported."
        )

    # ── Step 1: Apache Tika ───────────────────────────────────────────────────
    tika_text = extract_text_with_tika(str(path))
    tika_has_text = _is_meaningful_text(tika_text, min_chars=tika_min_chars)

    if tika_has_text:
        logger.info("Apache Tika extracted %d characters of text.", len(tika_text))
    else:
        logger.info(
            "Apache Tika found little or no selectable text (%d chars). "
            "Proceeding to OCR.",
            len(tika_text),
        )

    # ── Step 2: Extract per-page (PDF) or OCR images (DOCX) ──────────────────
    # PDFs use the smart per-page extractor: native text layer when available,
    # Tesseract OCR for image-only / scanned pages.  DOCX uses Tika text +
    # OCR on any embedded images.
    extracted_text = ""

    try:
        if suffix == ".pdf":
            # Per-page smart extraction supersedes Tika for PDFs
            extracted_text = _extract_pdf_pages(str(path), dpi=ocr_dpi)
            if extracted_text:
                logger.info(
                    "Per-page extraction yielded %d characters.", len(extracted_text)
                )
            else:
                logger.warning("Per-page extraction returned no text.")
        elif suffix in {".docx", ".doc"}:
            # For DOCX, layer Tika text + OCR of embedded images
            ocr_images_text = _ocr_docx_images(str(path))
            parts_docx: list[str] = []
            if tika_has_text:
                parts_docx.append(tika_text)
            if _is_meaningful_text(ocr_images_text, min_chars=tika_min_chars):
                logger.info(
                    "DOCX image OCR yielded %d characters.", len(ocr_images_text)
                )
                parts_docx.append(ocr_images_text)
            extracted_text = "\n\n".join(parts_docx)
    except Exception as ocr_err:
        logger.warning(
            "Extraction error: %s\n"
            "  ► Ensure Tesseract is installed and in your PATH.\n"
            "  ► Windows: download from https://github.com/UB-Mannheim/tesseract/wiki\n"
            "  ► Falling back to Apache Tika result only.",
            ocr_err,
        )
        extracted_text = tika_text  # graceful fallback

    # ── Step 3: Finalise result ───────────────────────────────────────────────
    parts: list[str] = []
    # For PDF: per-page result is authoritative; ignore separate Tika pass
    if suffix == ".pdf":
        if extracted_text:
            parts.append(extracted_text)
        elif tika_has_text:          # last-resort fallback
            parts.append(tika_text)
    else:
        if extracted_text:
            parts.append(extracted_text)

    if not parts:
        logger.warning("No text could be extracted from: %s", path)
        final_text = ""
    else:
        final_text = "\n\n".join(parts)

    # ── Step 4: Save to file (optional) ──────────────────────────────────────
    if output_txt_path:
        _save_text_file(final_text, output_txt_path)

    return final_text


# ─────────────────────────────────────────────────────────────────────────────
# File I/O helpers
# ─────────────────────────────────────────────────────────────────────────────

def _save_text_file(text: str, output_path: str) -> None:
    """Write *text* to *output_path* (UTF-8, creates parent directories)."""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    logger.info("Extracted text saved to: %s", out.resolve())


def _auto_output_path(input_path: str) -> str:
    """Derive a default .txt output path from the input file path."""
    p = Path(input_path)
    return str(p.with_suffix(".txt"))


# ─────────────────────────────────────────────────────────────────────────────
# CLI entry-point
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    """
    Usage:
        python extract_document.py <input_file> [output_txt_file]

    Examples:
        python extract_document.py report.pdf
        python extract_document.py report.pdf output/report.txt
        python extract_document.py contract.docx
    """
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) >= 3 else _auto_output_path(input_file)

    try:
        text = extract_text_from_document(
            file_path=input_file,
            output_txt_path=output_file,
        )
        if text:
            print(f"\n✓ Extraction complete. Text saved to: {output_file}")
            print(f"  Total characters extracted: {len(text)}")
        else:
            print("\n⚠ No text could be extracted from the file.")
            sys.exit(2)
    except (FileNotFoundError, ValueError, ImportError) as exc:
        logger.error("%s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
