"""
audio.py
--------
Audio transcription and speaker diarization using whisperX via CLI.
"""

import requests
import logging

from app.config import get_settings
from app.models.schemas import AudioExtractionResult

logger = logging.getLogger(__name__)
settings = get_settings()

class AudioExtractor:
    """
    Transcribe audio files and diarize speakers using whisperX CLI.
    """

    def __init__(self):
        self.hf_token = settings.huggingface_token

    def extract(self, file_path: str) -> AudioExtractionResult:
        url = "http://103.82.20.31:8080/transcribe"

        with open(file_path, "rb") as f:
            response = requests.post(
                url,
                files={
                    "file": (file_path, f, "audio/mpeg")
                },
                timeout=3600,  # 1 giờ
            )

        response.raise_for_status()

        transcript = response.text

        return AudioExtractionResult(
            raw_transcript=transcript,
            segments=[],  # No structured segments when parsing from raw txt
        )
