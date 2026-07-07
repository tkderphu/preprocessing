"""
audio.py
--------
Audio transcription using faster-whisper + speaker diarization via pyannote.audio.

Pipeline:
  1. faster-whisper  → word-level transcript with timestamps
  2. pyannote.audio  → speaker diarization segments
  3. Merge           → assign speaker label to each transcript segment
"""

import logging
import os
from pathlib import Path

from app.config import get_settings
from app.models.schemas import AudioExtractionResult, SpeakerSegment

logger   = logging.getLogger(__name__)
settings = get_settings()

# ── Lazy imports (heavy ML libraries) ────────────────────────────────────────

def _load_whisper():
    try:
        from faster_whisper import WhisperModel
        return WhisperModel
    except ImportError:
        raise ImportError(
            "faster-whisper is not installed. "
            "Run: pip install faster-whisper"
        )


def _load_diarization_pipeline():
    if not settings.huggingface_token:
        logger.warning(
            "HF_TOKEN not set — speaker diarization is DISABLED. "
            "Set HF_TOKEN in .env to enable pyannote.audio."
        )
        return None
    try:
        from pyannote.audio import Pipeline
        pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            use_auth_token=settings.huggingface_token,
        )
        return pipeline
    except Exception as exc:
        logger.warning("Failed to load diarization pipeline: %s", exc)
        return None


def _merge_transcript_and_diarization(
    whisper_segments: list,
    diarization,
) -> list[SpeakerSegment]:
    """
    Merge whisper word segments with pyannote speaker diarization turns.
    Each whisper segment is assigned the speaker label that overlaps most.
    """
    merged: list[SpeakerSegment] = []

    for seg in whisper_segments:
        seg_start = seg.start
        seg_end   = seg.end
        seg_text  = seg.text.strip()

        speaker = "UNKNOWN"
        best_overlap = 0.0

        if diarization is not None:
            for turn, _, label in diarization.itertracks(yield_label=True):
                overlap = min(turn.end, seg_end) - max(turn.start, seg_start)
                if overlap > best_overlap:
                    best_overlap = overlap
                    speaker = label

        merged.append(SpeakerSegment(
            speaker=speaker,
            start=seg_start,
            end=seg_end,
            text=seg_text,
        ))

    return merged


def _build_raw_transcript(segments: list[SpeakerSegment]) -> str:
    """Format segments into a readable transcript string."""
    lines = []
    current_speaker = None
    buffer = []

    for seg in segments:
        if seg.speaker != current_speaker:
            if buffer and current_speaker:
                lines.append(f"[{current_speaker}]: {' '.join(buffer)}")
            current_speaker = seg.speaker
            buffer = [seg.text]
        else:
            buffer.append(seg.text)

    if buffer and current_speaker:
        lines.append(f"[{current_speaker}]: {' '.join(buffer)}")

    return "\n".join(lines)


class AudioExtractor:
    """
    Transcribe audio files and optionally diarize speakers.
    """

    def __init__(self):
        self._whisper_model   = None
        self._diarize_pipeline = None

    def _get_whisper(self):
        if self._whisper_model is None:
            WhisperModel = _load_whisper()
            self._whisper_model = WhisperModel(
                model_size_or_path=settings.whisper_model_size,
                device=settings.whisper_device,
                compute_type=settings.whisper_compute_type,
            )
            logger.info(
                "Loaded Whisper model '%s' on device '%s'",
                settings.whisper_model_size, settings.whisper_device,
            )
        return self._whisper_model

    def _get_diarization(self):
        if self._diarize_pipeline is None:
            self._diarize_pipeline = _load_diarization_pipeline()
        return self._diarize_pipeline

    def extract(self, file_path: str) -> AudioExtractionResult:
        path = Path(file_path).resolve()
        logger.info("Transcribing audio: %s", path.name)

        # ── Step 1: Whisper transcription ─────────────────────────────────────
        model = self._get_whisper()
        whisper_segments, info = model.transcribe(
            str(path),
            beam_size=5,
            language=None,   # auto-detect
            word_timestamps=True,
            vad_filter=True,  # Voice Activity Detection — skip silence
        )
        whisper_segments = list(whisper_segments)   # materialize generator

        logger.info(
            "Whisper detected language '%s' (%.0f%% confidence), %d segments",
            info.language, info.language_probability * 100, len(whisper_segments),
        )

        # ── Step 2: Speaker diarization (optional) ────────────────────────────
        diarization = None
        diarize_pipeline = self._get_diarization()
        if diarize_pipeline is not None:
            try:
                import torch
                waveform_input = {"uri": path.stem, "audio": str(path)}
                diarization = diarize_pipeline(waveform_input)
                logger.info("Speaker diarization complete.")
            except Exception as exc:
                logger.warning("Diarization failed: %s", exc)

        # ── Step 3: Merge ──────────────────────────────────────────────────────
        segments = _merge_transcript_and_diarization(whisper_segments, diarization)
        transcript = _build_raw_transcript(segments)

        logger.info("Audio extraction complete. Transcript length: %d chars", len(transcript))

        return AudioExtractionResult(
            raw_transcript=transcript,
            segments=segments,
        )
