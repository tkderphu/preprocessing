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
        path = Path(file_path).resolve()
        logger.info("Transcribing audio using whisperX: %s", path.name)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        if not self.hf_token:
            logger.warning("HF_TOKEN is not set. Diarization may fail or be disabled.")

        # Set output directory to the same folder as the input file
        output_dir = path.parent

        cmd = [
            "whisperx", str(path),
            "--language", "vi",
            "--model", "large-v2",
            "--align_model", "WAV2VEC2_ASR_LARGE_LV60K_960H",
            "--diarize",
            "--output_dir", str(output_dir),
            "--output_format", "txt",
        ]
        
        if self.hf_token:
            cmd.extend(["--hf_token", self.hf_token])

        logger.info("Running whisperX command: %s", " ".join(cmd))
        
        try:
            # Run the subprocess
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                check=True
            )
            logger.debug("whisperX stdout: %s", result.stdout)
        except subprocess.CalledProcessError as exc:
            logger.error("whisperX failed with exit code %d\nstdout: %s\nstderr: %s", 
                            exc.returncode, exc.stdout, exc.stderr)
            raise RuntimeError(f"WhisperX extraction failed: {exc.stderr}") from exc

        # The output TXT file will have the same stem as the input file
        output_txt_path = output_dir / f"{path.stem}.txt"
        
        if not output_txt_path.exists():
            logger.error("Expected TXT output not found at %s", output_txt_path)
            raise FileNotFoundError("whisperX did not produce the expected TXT output.")

        # Read the raw text output
        transcript = output_txt_path.read_text(encoding="utf-8").strip()

        logger.info("Audio extraction complete. Transcript length: %d chars", len(transcript))

        return AudioExtractionResult(
            raw_transcript=transcript,
            segments=[],  # No structured segments when parsing from raw txt
        )
