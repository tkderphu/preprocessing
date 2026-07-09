"""
audio.py
--------
Audio transcription and speaker diarization using whisperX via CLI.
"""

import logging
import os
import subprocess
import tempfile
import json
from pathlib import Path

from app.config import get_settings
from app.models.schemas import AudioExtractionResult, SpeakerSegment

logger = logging.getLogger(__name__)
settings = get_settings()


def _build_raw_transcript(segments: list[SpeakerSegment]) -> str:
    """Format segments into a readable transcript string."""
    lines = []
    current_speaker = None
    buffer = []

    for seg in segments:
        speaker_label = seg.speaker or "UNKNOWN"
        if speaker_label != current_speaker:
            if buffer and current_speaker:
                lines.append(f"[{current_speaker}]: {' '.join(buffer)}")
            current_speaker = speaker_label
            buffer = [seg.text.strip()]
        else:
            buffer.append(seg.text.strip())

    if buffer and current_speaker:
        lines.append(f"[{current_speaker}]: {' '.join(buffer)}")

    return "\n".join(lines)


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
