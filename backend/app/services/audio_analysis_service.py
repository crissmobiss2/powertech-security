"""
Audio intelligence service using faster-whisper.

Capabilities:
- Real-time speech transcription from IP camera audio streams
- Language detection
- Gunshot / glass-break / scream detection via amplitude analysis
- Speaker diarization hooks (pyannote-audio integration ready)

faster-whisper is a CTranslate2 re-implementation of OpenAI Whisper.
It runs 4–8× faster than the original on CPU and supports int8 quantization.
Models: tiny (39M), base (74M), small (244M), medium (769M), large-v3 (1.5B)
"""
import logging
import os
import tempfile
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

_whisper_model = None
_whisper_model_size = os.getenv("WHISPER_MODEL", "base")


def _get_whisper():
    """Lazy-load faster-whisper model."""
    global _whisper_model
    if _whisper_model is None:
        try:
            from faster_whisper import WhisperModel
            _whisper_model = WhisperModel(
                _whisper_model_size,
                device="cpu",
                compute_type="int8",
                num_workers=2,
            )
            logger.info("faster-whisper '%s' model loaded", _whisper_model_size)
        except ImportError:
            logger.warning("faster-whisper not installed — audio transcription disabled")
        except Exception as e:
            logger.error("faster-whisper failed to load: %s", e)
    return _whisper_model


# Acoustic event thresholds
GUNSHOT_AMPLITUDE_THRESHOLD = 0.92       # Peak normalized amplitude
SCREAM_FREQUENCY_PEAK_HZ = (2000, 4000)  # Dominant freq range for screams
GLASS_BREAK_HZ = (6000, 8000)            # High-frequency spike for glass
MIN_SPEECH_DURATION_S = 0.8              # Ignore sub-second audio blips


class AudioAnalysisService:
    """Analyze audio from camera streams: transcription + acoustic events."""

    def __init__(self):
        self._sample_rate = 16000  # Whisper expects 16kHz

    def transcribe_audio_bytes(self, audio_bytes: bytes, language: str | None = None) -> dict:
        """
        Transcribe raw PCM audio (16kHz, mono, int16 or float32).
        Returns transcript segments with timestamps.
        """
        model = _get_whisper()
        if model is None:
            return {"transcript": "", "language": None, "segments": [], "error": "whisper_unavailable"}

        try:
            # Write to temp WAV file for faster-whisper
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp_path = tmp.name
                self._write_wav(tmp, audio_bytes)

            segments_iter, info = model.transcribe(
                tmp_path,
                language=language,
                beam_size=5,
                word_timestamps=True,
                vad_filter=True,
                vad_parameters={"min_silence_duration_ms": 500},
            )

            segments = []
            full_text = []
            for seg in segments_iter:
                segments.append({
                    "start": round(seg.start, 2),
                    "end": round(seg.end, 2),
                    "text": seg.text.strip(),
                    "confidence": round(1.0 - seg.no_speech_prob, 3),
                })
                full_text.append(seg.text.strip())

            os.unlink(tmp_path)

            return {
                "transcript": " ".join(full_text),
                "language": info.language,
                "language_probability": round(info.language_probability, 3),
                "duration": round(info.duration, 2),
                "segments": segments,
                "error": None,
            }
        except Exception as e:
            logger.error("Transcription failed: %s", e)
            return {"transcript": "", "language": None, "segments": [], "error": str(e)}

    def detect_acoustic_events(self, audio_array: np.ndarray, sample_rate: int = 16000) -> list[dict]:
        """
        Detect gunshots, screams, glass breaks from PCM audio array.
        Uses FFT and amplitude analysis — no ML model required.
        """
        events = []
        if audio_array.size == 0:
            return events

        if audio_array.dtype != np.float32:
            audio_array = audio_array.astype(np.float32)
            if audio_array.max() > 1.0:
                audio_array /= 32768.0  # int16 → float32

        peak_amplitude = float(np.abs(audio_array).max())

        # Gunshot: sudden very high amplitude impulse
        if peak_amplitude > GUNSHOT_AMPLITUDE_THRESHOLD:
            events.append({
                "event_type": "gunshot",
                "severity": "critical",
                "confidence": min(peak_amplitude, 1.0),
                "description": f"Possible gunshot detected (peak amplitude: {peak_amplitude:.2f})",
            })

        # Frequency analysis for screams and glass breaks
        try:
            fft = np.abs(np.fft.rfft(audio_array))
            freqs = np.fft.rfftfreq(len(audio_array), d=1.0 / sample_rate)
            total_energy = fft.sum() or 1.0

            # Scream: high energy in 2–4kHz range
            scream_mask = (freqs >= SCREAM_FREQUENCY_PEAK_HZ[0]) & (freqs <= SCREAM_FREQUENCY_PEAK_HZ[1])
            scream_energy = fft[scream_mask].sum() / total_energy
            if scream_energy > 0.35 and peak_amplitude > 0.3:
                events.append({
                    "event_type": "scream",
                    "severity": "high",
                    "confidence": round(min(scream_energy * 2.5, 0.95), 3),
                    "description": "Possible scream or distress call detected",
                })

            # Glass break: spike in 6–8kHz range
            glass_mask = (freqs >= GLASS_BREAK_HZ[0]) & (freqs <= GLASS_BREAK_HZ[1])
            glass_energy = fft[glass_mask].sum() / total_energy
            if glass_energy > 0.25:
                events.append({
                    "event_type": "glass_break",
                    "severity": "high",
                    "confidence": round(min(glass_energy * 3, 0.9), 3),
                    "description": "Possible glass breaking detected",
                })

        except Exception as e:
            logger.debug("FFT analysis failed: %s", e)

        return events

    def _write_wav(self, file_obj, pcm_bytes: bytes, sample_rate: int = 16000):
        """Write PCM bytes as a WAV file."""
        import struct
        n_channels = 1
        bit_depth = 16
        data_size = len(pcm_bytes)
        byte_rate = sample_rate * n_channels * bit_depth // 8

        header = struct.pack(
            "<4sI4s4sIHHIIHH4sI",
            b"RIFF",
            36 + data_size,
            b"WAVE",
            b"fmt ",
            16, 1, n_channels, sample_rate,
            byte_rate, n_channels * bit_depth // 8, bit_depth,
            b"data", data_size,
        )
        file_obj.write(header)
        file_obj.write(pcm_bytes)
        file_obj.flush()

    def analyze_camera_audio_chunk(
        self,
        audio_bytes: bytes,
        camera_id: str,
        language: str | None = None,
        run_diarization: bool = False,
    ) -> dict:
        """
        Full audio analysis pipeline for a chunk from a camera feed.
        Returns transcript + acoustic events + optional speaker diarization.
        """
        audio_array = np.frombuffer(audio_bytes, dtype=np.int16)
        acoustic_events = self.detect_acoustic_events(audio_array, self._sample_rate)

        transcript_result = {"transcript": "", "segments": [], "language": None, "error": None}
        if len(audio_array) / self._sample_rate >= MIN_SPEECH_DURATION_S:
            transcript_result = self.transcribe_audio_bytes(audio_bytes, language)

        diarization_result = None
        if run_diarization:
            try:
                from app.services.speaker_diarization_service import get_diarization_service
                diar_svc = get_diarization_service()
                segments = diar_svc.diarize_audio_bytes(audio_bytes, sample_rate=self._sample_rate)
                diarization_result = diar_svc.summarize_segments(segments)
            except Exception as e:
                logger.debug("Diarization in audio pipeline failed: %s", e)

        result = {
            "camera_id": camera_id,
            "transcript": transcript_result.get("transcript", ""),
            "language": transcript_result.get("language"),
            "segments": transcript_result.get("segments", []),
            "acoustic_events": acoustic_events,
            "has_critical_event": any(
                e["severity"] == "critical" for e in acoustic_events
            ),
        }
        if diarization_result:
            result["speaker_diarization"] = diarization_result
        return result
