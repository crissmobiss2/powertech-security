"""
Violence detection using nickmuchi/video-classification-fine-tuned-violence-detection.

VideoMAE fine-tuned on the RWF-2000 real-world fighting surveillance dataset.
Classifies video clips as Violence / NonViolence with much higher accuracy than
general Kinetics-400 models for security-specific scenarios.

HuggingFace: nickmuchi/video-classification-fine-tuned-violence-detection
Base model: MCG-NJU/videomae-base | Dataset: RWF-2000
"""
import logging
import os
from collections import deque

import numpy as np

logger = logging.getLogger(__name__)

VIOLENCE_MODEL_ID = os.getenv(
    "VIOLENCE_MODEL_ID",
    "nickmuchi/video-classification-fine-tuned-violence-detection",
)
CLIP_LENGTH = 16
INFERENCE_INTERVAL = 8         # run every N frames
VIOLENCE_THRESHOLD = 0.70      # confidence to trigger alert

_processor = None
_model = None


def _load_model():
    global _processor, _model
    if _model is not None:
        return _processor, _model
    try:
        from transformers import VideoMAEForVideoClassification, VideoMAEImageProcessor
        _processor = VideoMAEImageProcessor.from_pretrained(VIOLENCE_MODEL_ID)
        _model = VideoMAEForVideoClassification.from_pretrained(VIOLENCE_MODEL_ID)
        _model.eval()
        logger.info("Violence model loaded: %s", VIOLENCE_MODEL_ID)
    except ImportError:
        logger.warning("transformers not installed — violence detection unavailable")
    except Exception as e:
        logger.error("Violence model load failed: %s", e)
    return _processor, _model


class ViolenceDetectionService:
    """Per-camera violence detection with buffered frame inference."""

    def __init__(self, camera_id: str = "default"):
        self.camera_id = camera_id
        self._buffer: deque = deque(maxlen=CLIP_LENGTH)
        self._frame_count = 0
        self._latest: dict | None = None
        self._alerts: list[dict] = []

    def push_frame(self, frame: np.ndarray) -> dict | None:
        """Accept BGR frame; return inference result when clip is ready."""
        import cv2
        from PIL import Image

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        self._buffer.append(Image.fromarray(rgb).resize((224, 224)))
        self._frame_count += 1

        if self._frame_count % INFERENCE_INTERVAL == 0 and len(self._buffer) >= 8:
            result = self._infer()
            if result:
                self._latest = result
                if self.is_alert_worthy(result):
                    self._alerts.append(result)
                    if len(self._alerts) > 100:
                        self._alerts = self._alerts[-100:]
            return result
        return None

    def _infer(self) -> dict | None:
        processor, model = _load_model()
        if model is None:
            return self._flow_fallback()

        try:
            import torch

            frames = list(self._buffer)
            # Pad to CLIP_LENGTH
            while len(frames) < CLIP_LENGTH:
                frames.append(frames[-1])
            frames = frames[-CLIP_LENGTH:]

            inputs = processor(frames, return_tensors="pt")
            with torch.no_grad():
                outputs = model(**inputs)

            probs = torch.softmax(outputs.logits, dim=-1)[0]
            id2label = model.config.id2label
            ranked = sorted(
                [{"label": id2label[i], "score": float(probs[i])} for i in range(len(id2label))],
                key=lambda x: x["score"],
                reverse=True,
            )

            _VIOLENT_KEYWORDS = ("fight", "violen", "aggress")
            top = ranked[0]
            is_violent = any(kw in top["label"].lower() for kw in _VIOLENT_KEYWORDS)
            confidence = top["score"]

            if not is_violent:
                for r in ranked:
                    if any(kw in r["label"].lower() for kw in _VIOLENT_KEYWORDS):
                        is_violent = r["score"] > VIOLENCE_THRESHOLD
                        if is_violent:
                            confidence = r["score"]
                        break

            return {
                "is_violent": is_violent,
                "confidence": round(confidence, 3),
                "label": top["label"],
                "top_labels": ranked[:3],
                "severity": "critical" if (is_violent and confidence > 0.85) else "high" if is_violent else "info",
                "source": "videomae_rwf2000",
                "camera_id": self.camera_id,
            }
        except Exception as e:
            logger.debug("Violence inference error: %s", e)
            return self._flow_fallback()

    def _flow_fallback(self) -> dict | None:
        """Farneback optical flow motion heuristic when model is unavailable."""
        import cv2

        frames = list(self._buffer)
        if len(frames) < 4:
            return None
        try:
            scores = []
            for i in range(1, min(len(frames), 8)):
                prev = cv2.cvtColor(np.array(frames[i - 1]), cv2.COLOR_RGB2GRAY)
                curr = cv2.cvtColor(np.array(frames[i]), cv2.COLOR_RGB2GRAY)
                flow = cv2.calcOpticalFlowFarneback(prev, curr, None, 0.5, 3, 15, 3, 5, 1.2, 0)
                mag, _ = cv2.cartToPolar(flow[..., 0], flow[..., 1])
                scores.append(float(np.mean(mag)))

            avg = sum(scores) / len(scores) if scores else 0
            is_violent = avg > 18.0
            return {
                "is_violent": is_violent,
                "confidence": round(min(avg / 30.0, 0.85), 3),
                "label": "fight" if is_violent else "non-violence",
                "top_labels": [],
                "severity": "high" if is_violent else "info",
                "source": "optical_flow_fallback",
                "camera_id": self.camera_id,
            }
        except Exception as e:
            logger.debug("Flow fallback failed: %s", e)
            return None

    def get_latest(self) -> dict | None:
        return self._latest

    def get_alerts(self, limit: int = 10) -> list[dict]:
        return self._alerts[-limit:]

    def is_alert_worthy(self, result: dict | None) -> bool:
        return bool(result and result.get("is_violent") and result.get("confidence", 0) >= VIOLENCE_THRESHOLD)


_registry: dict[str, ViolenceDetectionService] = {}


def get_violence_service(camera_id: str = "default") -> ViolenceDetectionService:
    if camera_id not in _registry:
        _registry[camera_id] = ViolenceDetectionService(camera_id)
    return _registry[camera_id]
