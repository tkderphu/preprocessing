"""
factory.py
----------
Routes files to the correct extractor based on file type.
Returns a unified (raw_text, file_type) tuple for downstream processing.
"""

import logging
from pathlib import Path

from app.models.schemas import AudioExtractionResult, DocumentExtractionResult, FileType
from app.services.extractor.audio import AudioExtractor
from app.services.extractor.document import DocumentExtractor

logger = logging.getLogger(__name__)

# Module-level singletons (models are loaded once per worker process)
_audio_extractor    = None
_document_extractor = None


def _get_audio_extractor() -> AudioExtractor:
    global _audio_extractor
    if _audio_extractor is None:
        _audio_extractor = AudioExtractor()
    return _audio_extractor


def _get_document_extractor() -> DocumentExtractor:
    global _document_extractor
    if _document_extractor is None:
        _document_extractor = DocumentExtractor()
    return _document_extractor


def extract(file_path: str, file_type: FileType) -> tuple[str, str]:
    """
    Extract text from any supported file.

    Parameters
    ----------
    file_path : str
        Absolute path to the uploaded file.
    file_type : FileType
        Pre-detected file type.

    Returns
    -------
    tuple[str, str]
        (raw_text, content_type)
        content_type is "audio_transcript" | "document"
    """
    path = Path(file_path)
    logger.info("Routing file '%s' → extractor for type '%s'", path.name, file_type)

    if file_type == FileType.AUDIO:
        result: AudioExtractionResult = _get_audio_extractor().extract(file_path)
        return result.raw_transcript, "audio_transcript"

    else:
        result: DocumentExtractionResult = _get_document_extractor().extract(file_path)
        return result.raw_text, "document"
