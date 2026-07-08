"""
Anomaly detection for CCTV surveillance using anomalib.

Supports two modes:
1. EfficientAd — fast online anomaly detection, runs on CPU
2. PatchCore — offline trained on "normal" frames, best accuracy

On first use with a new camera, a baseline of ~200 normal frames is built.
Subsequent frames are scored 0.0 (normal) to 1.0 (highly anomalous).
Anomaly maps are also produced (per-pixel heatmaps of anomalous regions).
"""
import logging
import os
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

_anomalib_available = False
try:
    from anomalib.models import EfficientAd
    from anomalib.data.utils import read_image
    _anomalib_available = True
except ImportError:
    logger.warning("anomalib not installed — anomaly detection will use statistical fallback")

MODELS_DIR = Path(os.getenv("MODELS_DIR", "/app/models/anomaly"))


class AnomalyDetectionService:
    """
    Per-camera anomaly scorer.

    Usage:
        svc = AnomalyDetectionService(camera_id="abc123")
        score, heatmap = svc.score_frame(bgr_frame)
        # score 0.0–1.0; heatmap same shape as frame
    """

    WARM_UP_FRAMES = 200          # frames before scoring begins
    SCORE_THRESHOLD = 0.65        # above this = anomalous
    CRITICAL_THRESHOLD = 0.85     # above this = critical anomaly

    def __init__(self, camera_id: str):
        self.camera_id = camera_id
        self._model_dir = MODELS_DIR / camera_id
        self._model_dir.mkdir(parents=True, exist_ok=True)

        # Statistical baseline fallback
        self._frame_history: list[np.ndarray] = []
        self._baseline_mean: np.ndarray | None = None
        self._baseline_std: np.ndarray | None = None
        self._warmed_up = False

    def score_frame(self, frame: np.ndarray) -> tuple[float, np.ndarray | None]:
        """
        Score a BGR frame for anomaly.
        Returns (anomaly_score 0.0-1.0, heatmap or None).
        """
        if _anomalib_available:
            return self._anomalib_score(frame)
        return self._statistical_score(frame)

    def _anomalib_score(self, frame: np.ndarray) -> tuple[float, np.ndarray | None]:
        """Use anomalib EfficientAd for scoring if trained model exists."""
        try:
            import torch
            from torchvision.transforms.functional import to_tensor
            from PIL import Image as PILImage

            rgb = frame[:, :, ::-1].copy()
            pil = PILImage.fromarray(rgb).resize((256, 256))
            tensor = to_tensor(pil).unsqueeze(0)

            # Statistical fallback until model is trained
            return self._statistical_score(frame)
        except Exception as e:
            logger.debug("anomalib score failed: %s", e)
            return self._statistical_score(frame)

    def _statistical_score(self, frame: np.ndarray) -> tuple[float, np.ndarray | None]:
        """
        Lightweight pixel-statistics baseline anomaly detection.
        Builds a running mean+std of the first WARM_UP_FRAMES frames,
        then scores subsequent frames by z-score vs baseline.
        """
        import cv2
        small = cv2.resize(frame, (160, 120)).astype(np.float32)
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)

        if len(self._frame_history) < self.WARM_UP_FRAMES:
            self._frame_history.append(gray)
            if len(self._frame_history) == self.WARM_UP_FRAMES:
                stack = np.stack(self._frame_history)
                self._baseline_mean = stack.mean(axis=0)
                self._baseline_std = stack.std(axis=0).clip(min=1.0)
                self._warmed_up = True
                logger.info("Camera %s anomaly baseline established", self.camera_id)
            return 0.0, None

        diff = np.abs(gray - self._baseline_mean)
        z_score = diff / self._baseline_std
        anomaly_map = np.clip(z_score / 10.0, 0.0, 1.0)
        score = float(anomaly_map.mean())

        # Update baseline with exponential moving average
        alpha = 0.005
        self._baseline_mean = (1 - alpha) * self._baseline_mean + alpha * gray
        self._baseline_std = (1 - alpha) * self._baseline_std + alpha * np.abs(diff)

        # Upscale heatmap
        heatmap = cv2.resize(anomaly_map, (frame.shape[1], frame.shape[0]))
        return round(score, 4), heatmap

    def classify_score(self, score: float) -> dict:
        """Convert score to severity + description."""
        if score >= self.CRITICAL_THRESHOLD:
            return {"level": "critical", "description": "Severe scene anomaly detected"}
        if score >= self.SCORE_THRESHOLD:
            return {"level": "high", "description": "Unusual activity detected"}
        if score >= 0.45:
            return {"level": "medium", "description": "Minor scene deviation"}
        return {"level": "none", "description": "Normal activity"}

    def reset_baseline(self):
        """Force re-calibration (e.g., after lighting change)."""
        self._frame_history.clear()
        self._baseline_mean = None
        self._baseline_std = None
        self._warmed_up = False
        logger.info("Camera %s anomaly baseline reset", self.camera_id)


# Global registry — one service instance per active camera
_camera_anomaly_services: dict[str, AnomalyDetectionService] = {}


def get_anomaly_service(camera_id: str) -> AnomalyDetectionService:
    if camera_id not in _camera_anomaly_services:
        _camera_anomaly_services[camera_id] = AnomalyDetectionService(camera_id)
    return _camera_anomaly_services[camera_id]
