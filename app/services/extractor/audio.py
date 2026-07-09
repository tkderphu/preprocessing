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

        # Create a temporary directory for whisperx outputs
        with tempfile.TemporaryDirectory() as temp_dir:
            cmd = [
                "whisperx", str(path),
                "--language", "vi",
                "--model", "large-v2",
                "--align_model", "WAV2VEC2_ASR_LARGE_LV60K_960H",
                "--diarize",
                "--output_dir", temp_dir,
                "--output_format", "json",
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

            # The output JSON file will have the same stem as the input file
            output_json_path = Path(temp_dir) / f"{path.stem}.json"
            
            if not output_json_path.exists():
                logger.error("Expected JSON output not found at %s", output_json_path)
                raise FileNotFoundError("whisperX did not produce the expected JSON output.")

            # Parse the JSON output
            with open(output_json_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            raw_segments = data.get("segments", [])
            segments: list[SpeakerSegment] = []

            for seg in raw_segments:
                segments.append(SpeakerSegment(
                    speaker=seg.get("speaker", "UNKNOWN"),
                    start=float(seg.get("start", 0.0)),
                    end=float(seg.get("end", 0.0)),
                    text=seg.get("text", "").strip()
                ))

            transcript = _build_raw_transcript(segments)
            logger.info("Audio extraction complete. Transcript length: %d chars", len(transcript))

            return AudioExtractionResult(
                raw_transcript=transcript,
                segments=segments,
            )
