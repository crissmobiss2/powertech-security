"""
Speaker diarization from CCTV audio streams using pyannote.audio.

Identifies WHO is speaking WHEN in an audio recording. Outputs a timeline
of speaker segments with start/end timestamps and anonymous speaker IDs
(SPEAKER_00, SPEAKER_01, ...).

Requires:
  - pyannote.audio>=3.3.0
  - HF_AUTH_TOKEN env var (accept model terms at huggingface.co/pyannote)

Falls back to energy-based voice activity detection (VAD) if pyannote
is unavailable or token is missing.

Usage:
    svc = SpeakerDiarizationService()
    segments = await svc.diarize_audio_bytes(wav_bytes, sample_rate=16000)
    # Returns: [{"speaker": "SPEAKER_00", "start": 0.5, "end": 3.2, "duration": 2.7}, ...]
"""
import io
import logging
import os
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

HF_AUTH_TOKEN = os.getenv("HF_AUTH_TOKEN", "")
DIARIZATION_MODEL = os.getenv(
    "PYANNOTE_MODEL", "pyannote/speaker-diarization-3.1"
)

_pyannote_available = False
_pipeline = None

try:
    from pyannote.audio import Pipeline
    _pyannote_available = True
except ImportError:
    logger.warning(
        "pyannote.audio not installed — speaker diarization will use VAD fallback. "
        "Install with: pip install pyannote.audio>=3.3.0"
    )


def _get_pipeline():
    global _pipeline
    if _pipeline is not None:
        return _pipeline
    if not _pyannote_available:
        return None
    if not HF_AUTH_TOKEN:
        logger.warning(
            "HF_AUTH_TOKEN not set — cannot load pyannote diarization model. "
            "Set env var and accept model at https://hf.co/pyannote/speaker-diarization-3.1"
        )
        return None
    try:
        from pyannote.audio import Pipeline as PyannotePipeline
        logger.info("Loading pyannote diarization pipeline: %s", DIARIZATION_MODEL)
        _pipeline = PyannotePipeline.from_pretrained(
            DIARIZATION_MODEL, use_auth_token=HF_AUTH_TOKEN
        )
        logger.info("pyannote diarization pipeline loaded")
        return _pipeline
    except Exception as e:
        logger.error("Failed to load pyannote pipeline: %s", e)
        return None


class SpeakerDiarizationService:
    """
    Identifies speaker segments in audio recordings.

    For CCTV use: connects to camera mic audio, identifies guard vs visitor
    voices, flags unknown speakers, tracks conversation patterns.
    """

    MIN_SEGMENT_DURATION = 0.5   # seconds — shorter segments are noise
    MAX_SPEAKERS = 10

    def diarize_audio_file(self, file_path: str) -> list[dict]:
        """
        Diarize an audio file on disk.
        Returns list of speaker segments with start/end times.
        """
        pipeline = _get_pipeline()
        if pipeline is not None:
            return self._pyannote_diarize_file(pipeline, file_path)
        return self._vad_fallback_file(file_path)

    def diarize_audio_bytes(
        self,
        audio_bytes: bytes,
        sample_rate: int = 16000,
        num_channels: int = 1,
    ) -> list[dict]:
        """
        Diarize raw PCM audio bytes.
        audio_bytes: raw 16-bit PCM samples (int16)
        Returns list of speaker segments.
        """
        pipeline = _get_pipeline()

        # Convert bytes to numpy float32 array
        audio_arr = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0

        if pipeline is not None:
            return self._pyannote_diarize_array(pipeline, audio_arr, sample_rate)
        return self._vad_fallback_array(audio_arr, sample_rate)

    def diarize_wav_bytes(self, wav_bytes: bytes) -> list[dict]:
        """Diarize from raw WAV file bytes."""
        import tempfile
        pipeline = _get_pipeline()
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as tmp:
            tmp.write(wav_bytes)
            tmp.flush()
            if pipeline is not None:
                return self._pyannote_diarize_file(pipeline, tmp.name)
            return self._vad_fallback_file(tmp.name)

    def _pyannote_diarize_file(self, pipeline: Any, file_path: str) -> list[dict]:
        try:
            diarization = pipeline(file_path, max_speakers=self.MAX_SPEAKERS)
            return self._diarization_to_segments(diarization)
        except Exception as e:
            logger.error("pyannote diarization failed: %s", e)
            return self._vad_fallback_file(file_path)

    def _pyannote_diarize_array(
        self, pipeline: Any, audio_arr: np.ndarray, sample_rate: int
    ) -> list[dict]:
        try:
            import torch
            # pyannote accepts tensor with shape (1, num_samples)
            tensor = torch.from_numpy(audio_arr).unsqueeze(0)
            diarization = pipeline(
                {"waveform": tensor, "sample_rate": sample_rate},
                max_speakers=self.MAX_SPEAKERS,
            )
            return self._diarization_to_segments(diarization)
        except Exception as e:
            logger.error("pyannote diarization (array) failed: %s", e)
            return self._vad_fallback_array(audio_arr, sample_rate)

    def _diarization_to_segments(self, diarization: Any) -> list[dict]:
        """Convert pyannote Annotation to list of segment dicts."""
        segments = []
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            duration = turn.end - turn.start
            if duration < self.MIN_SEGMENT_DURATION:
                continue
            segments.append({
                "speaker": speaker,
                "start": round(turn.start, 3),
                "end": round(turn.end, 3),
                "duration": round(duration, 3),
            })
        return sorted(segments, key=lambda s: s["start"])

    def _vad_fallback_file(self, file_path: str) -> list[dict]:
        """Energy-based VAD fallback — cannot distinguish speakers."""
        try:
            import wave
            with wave.open(file_path, "rb") as wf:
                frames = wf.readframes(wf.getnframes())
                sample_rate = wf.getframerate()
            audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
            return self._vad_fallback_array(audio, sample_rate)
        except Exception as e:
            logger.error("VAD fallback file read failed: %s", e)
            return []

    def _vad_fallback_array(self, audio: np.ndarray, sample_rate: int) -> list[dict]:
        """
        Simple energy-based voice activity detection.
        Cannot distinguish speakers — all active segments labeled SPEAKER_00.
        """
        frame_size = int(sample_rate * 0.03)  # 30ms frames
        threshold = 0.01   # RMS energy threshold

        segments = []
        in_speech = False
        seg_start = 0.0

        for i in range(0, len(audio) - frame_size, frame_size):
            frame = audio[i:i + frame_size]
            rms = float(np.sqrt(np.mean(frame ** 2)))
            t = i / sample_rate

            if rms > threshold and not in_speech:
                in_speech = True
                seg_start = t
            elif rms <= threshold and in_speech:
                in_speech = False
                duration = t - seg_start
                if duration >= self.MIN_SEGMENT_DURATION:
                    segments.append({
                        "speaker": "SPEAKER_00",
                        "start": round(seg_start, 3),
                        "end": round(t, 3),
                        "duration": round(duration, 3),
                    })

        if in_speech:
            end = len(audio) / sample_rate
            segments.append({
                "speaker": "SPEAKER_00",
                "start": round(seg_start, 3),
                "end": round(end, 3),
                "duration": round(end - seg_start, 3),
            })

        return segments

    def summarize_segments(self, segments: list[dict]) -> dict:
        """
        Summarize diarization output for security logging.
        Returns speaker count, total talk time, longest speaker, etc.
        """
        if not segments:
            return {
                "speaker_count": 0, "total_duration": 0.0,
                "speakers": [], "dominant_speaker": None,
            }

        speaker_times: dict[str, float] = {}
        for seg in segments:
            speaker_times[seg["speaker"]] = (
                speaker_times.get(seg["speaker"], 0.0) + seg["duration"]
            )

        dominant = max(speaker_times, key=speaker_times.get)
        total = sum(speaker_times.values())
        return {
            "speaker_count": len(speaker_times),
            "total_duration": round(total, 3),
            "dominant_speaker": dominant,
            "speakers": [
                {
                    "id": spk,
                    "total_duration": round(dur, 3),
                    "percentage": round(dur / total * 100, 1),
                }
                for spk, dur in sorted(
                    speaker_times.items(), key=lambda x: x[1], reverse=True
                )
            ],
            "segment_count": len(segments),
            "diarization_model": DIARIZATION_MODEL if _pyannote_available else "vad_fallback",
        }


# Module-level singleton
_diarization_service: SpeakerDiarizationService | None = None


def get_diarization_service() -> SpeakerDiarizationService:
    global _diarization_service
    if _diarization_service is None:
        _diarization_service = SpeakerDiarizationService()
    return _diarization_service
