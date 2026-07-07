"""
Document Text Extractor (CLI)
=============================
Extracts text from PDF and DOCX files using the Unstructured.io API via Docker.

Usage:
    python extract_document.py <input_file> [output_txt_file]
"""

import os
import sys
import logging
from pathlib import Path

# Add project root to python path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.extractor.document import DocumentExtractor
from app.models.schemas import DocumentExtractionResult

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def _auto_output_path(input_path: str) -> str:
    p = Path(input_path)
    return str(p.with_suffix(".txt"))


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) >= 3 else _auto_output_path(input_file)

    try:
        extractor = DocumentExtractor()
        result: DocumentExtractionResult = extractor.extract(input_file)
        
        text = result.raw_text
        if text:
            out = Path(output_file)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(text, encoding="utf-8")
            
            print(f"\n✓ Extraction complete. Text saved to: {output_file}")
            print(f"  Total characters extracted: {len(text)}")
        else:
            print("\n⚠ No text could be extracted from the file.")
            sys.exit(2)
            
    except (FileNotFoundError, ValueError, ImportError) as exc:
        logger.error("%s", exc)
        sys.exit(1)
    except Exception as exc:
        logger.exception("An error occurred during extraction:")
        sys.exit(1)


if __name__ == "__main__":
    main()
