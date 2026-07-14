"""
audio.py
--------
Audio transcription and speaker diarization using WhisperX REST API.
"""

from pathlib import Path
import logging
import os

import requests

from app.config import get_settings
from app.models.schemas import AudioExtractionResult

logger = logging.getLogger(__name__)
settings = get_settings()
WHISPER_URL = os.get("WHISPER_TRANSCRIBE_URL", "http://whisperx:8080/transcribe") 

class AudioExtractor:
    """
    Transcribe audio files using WhisperX REST API.
    """

    def __init__(self):
        self.url = WHISPER_URL

    def extract(self, file_path: str) -> AudioExtractionResult:
        filename = Path(file_path).name

        with open(file_path, "rb") as f:
            response = requests.post(
                self.url,
                files={
                    "file": (
                        filename,      # Chỉ gửi tên file
                        f,
                        "audio/mpeg",
                    )
                },
                timeout=3600,
            )

        response.raise_for_status()

        transcript = response.text

        return AudioExtractionResult(
            raw_transcript=transcript,
            segments=[],
        )