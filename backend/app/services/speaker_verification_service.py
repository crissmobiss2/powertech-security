"""
Speaker verification using SpeechBrain ECAPA-TDNN.

Use cases:
- Enroll known persons (security staff, clients) from voice samples
- Verify whether a recorded voice matches an enrolled speaker
- Cross-camera speaker linking: confirm the voice at Gate A is the same person at Gate B

Model: speechbrain/spkrec-ecapa-voxceleb
  - ECAPA-TDNN trained on VoxCeleb 1+2 (7205 speakers, 2794 hours)
  - State-of-the-art speaker verification EER on VoxCeleb1-O
  - Returns 192-dim x-vectors for speaker embedding

Falls back to energy-based VAD speaker count if SpeechBrain unavailable.
"""
import logging
import os
import tempfile
from dataclasses import dataclass

import numpy as np

logger = logging.getLogger(__name__)

VERIFICATION_THRESHOLD = 0.25   # cosine similarity score threshold (lower = more strict)
MAX_EMBEDDINGS_PER_SPEAKER = 10

SPEECHBRAIN_MODEL_ID = "speechbrain/spkrec-ecapa-voxceleb"
SPEECHBRAIN_SAVE_DIR = os.getenv("SPEECHBRAIN_SAVE_DIR", "/app/models/speechbrain")

_encoder = None


def _load_encoder():
    global _encoder
    if _encoder is not None:
        return _encoder
    try:
        from speechbrain.pretrained import SpeakerRecognition
        _encoder = SpeakerRecognition.from_hparams(
            source=SPEECHBRAIN_MODEL_ID,
            savedir=SPEECHBRAIN_SAVE_DIR,
        )
        logger.info("SpeechBrain ECAPA-TDNN loaded: %s", SPEECHBRAIN_MODEL_ID)
    except ImportError:
        logger.warning("speechbrain not installed — speaker verification unavailable")
    except Exception as e:
        logger.error("SpeechBrain load failed: %s", e)
    return _encoder


@dataclass
class SpeakerProfile:
    speaker_id: str
    display_name: str
    embeddings: list[np.ndarray]

    def mean_embedding(self) -> np.ndarray:
        e = np.stack(self.embeddings).mean(axis=0)
        return e / (np.linalg.norm(e) + 1e-8)


class SpeakerVerificationService:
    """Enroll and verify speakers from audio clips."""

    def __init__(self):
        self._gallery: dict[str, SpeakerProfile] = {}

    # ── Enrollment ────────────────────────────────────────────────────────────

    def enroll(
        self,
        speaker_id: str,
        display_name: str,
        audio_bytes: bytes,
        sample_rate: int = 16000,
    ) -> dict:
        """
        Enroll a speaker's voice from audio bytes.

        Args:
            speaker_id: unique ID (UUID of person record)
            display_name: human name for logs
            audio_bytes: raw PCM int16 or WAV bytes
            sample_rate: PCM sample rate

        Returns:
            {success, speaker_id, embedding_count, message}
        """
        embedding = self._extract_embedding(audio_bytes, sample_rate)
        if embedding is None:
            return {
                "success": False,
                "speaker_id": speaker_id,
                "message": "Embedding extraction failed — check audio quality",
            }

        if speaker_id not in self._gallery:
            self._gallery[speaker_id] = SpeakerProfile(
                speaker_id=speaker_id,
                display_name=display_name,
                embeddings=[],
            )

        profile = self._gallery[speaker_id]
        profile.embeddings.append(embedding)
        if len(profile.embeddings) > MAX_EMBEDDINGS_PER_SPEAKER:
            profile.embeddings = profile.embeddings[-MAX_EMBEDDINGS_PER_SPEAKER:]

        return {
            "success": True,
            "speaker_id": speaker_id,
            "display_name": display_name,
            "embedding_count": len(profile.embeddings),
            "message": f"Enrolled voice sample {len(profile.embeddings)}/{MAX_EMBEDDINGS_PER_SPEAKER}",
        }

    # ── Verification ──────────────────────────────────────────────────────────

    def verify(
        self,
        speaker_id: str,
        audio_bytes: bytes,
        sample_rate: int = 16000,
    ) -> dict:
        """
        Verify whether audio matches the enrolled speaker.

        Returns:
            {verified, speaker_id, score, threshold, confidence, message}
        """
        if speaker_id not in self._gallery:
            return {
                "verified": False,
                "speaker_id": speaker_id,
                "score": 0.0,
                "message": "Speaker not enrolled",
            }

        embedding = self._extract_embedding(audio_bytes, sample_rate)
        if embedding is None:
            return {
                "verified": False,
                "speaker_id": speaker_id,
                "score": 0.0,
                "message": "Embedding extraction failed",
            }

        profile = self._gallery[speaker_id]
        mean_embed = profile.mean_embedding()
        score = float(np.dot(embedding, mean_embed))
        verified = score >= VERIFICATION_THRESHOLD

        return {
            "verified": verified,
            "speaker_id": speaker_id,
            "display_name": profile.display_name,
            "score": round(score, 4),
            "threshold": VERIFICATION_THRESHOLD,
            "confidence": round(min(score / 0.5, 1.0), 3) if verified else round(score / VERIFICATION_THRESHOLD, 3),
            "message": "Voice match confirmed" if verified else "Voice does not match",
        }

    def identify(self, audio_bytes: bytes, sample_rate: int = 16000) -> list[dict]:
        """
        Open-set speaker identification: find the best matching enrolled speaker.
        Returns top matches sorted by score.
        """
        embedding = self._extract_embedding(audio_bytes, sample_rate)
        if embedding is None or not self._gallery:
            return []

        results = []
        for sid, profile in self._gallery.items():
            mean_embed = profile.mean_embedding()
            score = float(np.dot(embedding, mean_embed))
            results.append({
                "speaker_id": sid,
                "display_name": profile.display_name,
                "score": round(score, 4),
                "verified": score >= VERIFICATION_THRESHOLD,
            })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:5]

    # ── Internal ──────────────────────────────────────────────────────────────

    def _extract_embedding(self, audio_bytes: bytes, sample_rate: int) -> np.ndarray | None:
        encoder = _load_encoder()
        if encoder is not None:
            return self._speechbrain_embed(encoder, audio_bytes, sample_rate)
        return self._energy_embed(audio_bytes, sample_rate)

    def _speechbrain_embed(self, encoder, audio_bytes: bytes, sample_rate: int) -> np.ndarray | None:
        try:
            import torch

            # Write to temp WAV for SpeechBrain
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                self._write_wav(tmp, audio_bytes, sample_rate)
                tmp_path = tmp.name

            signal, sr = encoder.load_audio(tmp_path)
            os.unlink(tmp_path)

            # Resample if needed
            if sr != 16000:
                import torchaudio
                signal = torchaudio.functional.resample(signal, sr, 16000)

            signal = signal.unsqueeze(0)
            with torch.no_grad():
                embedding = encoder.encode_batch(signal)
            emb = embedding.squeeze().cpu().numpy()
            return emb / (np.linalg.norm(emb) + 1e-8)
        except Exception as e:
            logger.debug("SpeechBrain embed failed: %s", e)
            return None

    def _energy_embed(self, audio_bytes: bytes, sample_rate: int) -> np.ndarray | None:
        """
        Simple energy-based embedding fallback.
        Not a real speaker embedding — for testing only.
        """
        try:
            audio = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
            if len(audio) < sample_rate * 0.5:  # < 0.5s
                return None

            # 32-dim feature: RMS energy per 100ms window
            hop = sample_rate // 10
            features = []
            for i in range(0, min(len(audio) - hop, hop * 32), hop):
                chunk = audio[i:i + hop]
                features.append(float(np.sqrt(np.mean(chunk ** 2))))
            if len(features) < 16:
                return None

            emb = np.array(features[:32], dtype=np.float32)
            return emb / (np.linalg.norm(emb) + 1e-8)
        except Exception as e:
            logger.debug("Energy embed failed: %s", e)
            return None

    def _write_wav(self, file_obj, pcm_bytes: bytes, sample_rate: int):
        import struct
        n_ch, bits = 1, 16
        data_len = len(pcm_bytes)
        byte_rate = sample_rate * n_ch * bits // 8
        header = struct.pack(
            "<4sI4s4sIHHIIHH4sI",
            b"RIFF", 36 + data_len, b"WAVE",
            b"fmt ", 16, 1, n_ch, sample_rate,
            byte_rate, n_ch * bits // 8, bits,
            b"data", data_len,
        )
        file_obj.write(header)
        file_obj.write(pcm_bytes)
        file_obj.flush()

    def gallery_summary(self) -> dict:
        return {
            "enrolled_speakers": len(self._gallery),
            "speakers": [
                {"speaker_id": k, "display_name": v.display_name, "samples": len(v.embeddings)}
                for k, v in self._gallery.items()
            ],
            "model_loaded": _encoder is not None,
        }


_tenants: dict[str, SpeakerVerificationService] = {}


def get_speaker_verification_service(tenant_id: str = "default") -> SpeakerVerificationService:
    if tenant_id not in _tenants:
        _tenants[tenant_id] = SpeakerVerificationService()
    return _tenants[tenant_id]
