"""
Video action recognition for CCTV surveillance.

Primary: VideoMAE (MCG-NJU/videomae-base-finetuned-kinetics) — 16-frame clips
Secondary: TimeSformer (facebook/timesformer-base-finetuned-k400) — 8-frame clips
Fallback: Optical flow (Lucas-Kanade) + pose-based motion analysis

Security actions detected:
  fighting / physical_altercation
  falling / collapse
  running / fleeing
  crowd_formation
  loitering
  normal_activity
  suspicious_movement

The service maintains a per-camera frame buffer. When the buffer fills (CLIP_LENGTH
frames), it runs a full VideoMAE inference. Between clips, optical flow gives
a continuous fast motion score that can flag rapid movement.
"""
import logging
import os
from collections import deque

import numpy as np

logger = logging.getLogger(__name__)

# VideoMAE/TimeSformer availability flags
_videomae_available = False
_timesformer_available = False

try:
    from transformers import VideoMAEImageProcessor, VideoMAEForVideoClassification
    _videomae_available = True
except ImportError:
    logger.warning("VideoMAE (transformers) not installed — using optical flow fallback")

try:
    from transformers import AutoImageProcessor, TimesformerForVideoClassification
    _timesformer_available = True
except ImportError:
    pass  # timesformer is optional; videomae preferred

# Kinetics-400 classes mapped to security categories
KINETICS_SECURITY_MAP: dict[str, str] = {
    # Physical conflict
    "wrestling": "fighting",
    "punching bag": "fighting",
    "punching person (boxing)": "fighting",
    "kickboxing": "fighting",
    "sword fighting": "fighting",
    "mixed martial arts": "fighting",
    "arm wrestling": "fighting",
    "sumo wrestling": "fighting",
    "slacklining": "falling",
    # Falling / injury
    "falling or walking with limping": "falling",
    "belly flopping": "falling",
    "diving cliff": "falling",
    "diving": "falling",
    # Rapid movement / fleeing
    "running": "running",
    "jogging": "running",
    "sprinting": "running",
    # Crowd / group
    "crowd surfing": "crowd",
    # Suspicious
    "crawling": "suspicious_movement",
    "crouching": "suspicious_movement",
    "sneaking": "suspicious_movement",
}

CLIP_LENGTH = 16          # frames per VideoMAE clip
FRAME_SIZE = (224, 224)   # VideoMAE input resolution
TIMESFORMER_FRAMES = 8    # TimeSformer uses fewer frames

# Singleton model holders
_videomae_model = None
_videomae_processor = None
_timesformer_model = None
_timesformer_processor = None


def _load_videomae():
    global _videomae_model, _videomae_processor
    if _videomae_model is not None:
        return True
    if not _videomae_available:
        return False
    try:
        model_name = os.getenv("VIDEOMAE_MODEL", "MCG-NJU/videomae-base-finetuned-kinetics")
        logger.info("Loading VideoMAE model: %s (first load ~1.7 GB download)", model_name)
        _videomae_processor = VideoMAEImageProcessor.from_pretrained(model_name)
        _videomae_model = VideoMAEForVideoClassification.from_pretrained(model_name)
        _videomae_model.eval()
        logger.info("VideoMAE loaded successfully")
        return True
    except Exception as e:
        logger.error("VideoMAE load failed: %s — using optical flow fallback", e)
        return False


def _load_timesformer():
    global _timesformer_model, _timesformer_processor
    if _timesformer_model is not None:
        return True
    if not _timesformer_available:
        return False
    try:
        model_name = os.getenv("TIMESFORMER_MODEL", "facebook/timesformer-base-finetuned-k400")
        _timesformer_processor = AutoImageProcessor.from_pretrained(model_name)
        _timesformer_model = TimesformerForVideoClassification.from_pretrained(model_name)
        _timesformer_model.eval()
        logger.info("TimeSformer loaded successfully")
        return True
    except Exception as e:
        logger.warning("TimeSformer load failed: %s", e)
        return False


class VideoActionService:
    """
    Per-camera video action recognition.

    Usage:
        svc = VideoActionService(camera_id="abc123")
        svc.push_frame(bgr_frame)           # add frame to buffer
        result = svc.get_latest_action()    # get most recent classification
    """

    def __init__(self, camera_id: str, use_videomae: bool = True):
        self.camera_id = camera_id
        self.use_videomae = use_videomae
        self._frame_buffer: deque[np.ndarray] = deque(maxlen=CLIP_LENGTH)
        self._prev_gray: np.ndarray | None = None
        self._motion_scores: deque[float] = deque(maxlen=30)
        self._latest_result: dict = _make_result("normal_activity", 0.0)
        self._clip_results: deque[dict] = deque(maxlen=10)
        self._frame_count = 0

    def push_frame(self, frame: np.ndarray) -> dict | None:
        """
        Add a BGR frame to the buffer.
        Returns a new classification result when a full clip is ready,
        or None when still buffering.
        Also updates optical flow motion score on every frame.
        """
        import cv2

        self._frame_count += 1

        # Always run optical flow for fast continuous motion scoring
        gray = cv2.cvtColor(cv2.resize(frame, (160, 120)), cv2.COLOR_BGR2GRAY)
        if self._prev_gray is not None:
            flow = cv2.calcOpticalFlowFarneback(
                self._prev_gray, gray, None,
                pyr_scale=0.5, levels=3, winsize=15,
                iterations=3, poly_n=5, poly_sigma=1.2, flags=0,
            )
            mag, _ = cv2.cartToPolar(flow[..., 0], flow[..., 1])
            motion_score = float(np.percentile(mag, 95))
            self._motion_scores.append(motion_score)

            # Fast optical flow alert for very rapid motion (fighting/running)
            if len(self._motion_scores) >= 5:
                recent_avg = np.mean(list(self._motion_scores)[-5:])
                if recent_avg > 8.0:  # threshold: pixels/frame
                    action = "fighting" if recent_avg > 15.0 else "running"
                    flow_result = _make_result(action, min(recent_avg / 25.0, 0.95),
                                               source="optical_flow")
                    self._latest_result = flow_result

        self._prev_gray = gray

        # Resize and add to clip buffer
        resized = cv2.resize(frame, FRAME_SIZE)
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        self._frame_buffer.append(rgb)

        # Run deep model when clip is full
        if len(self._frame_buffer) == CLIP_LENGTH and self._frame_count % CLIP_LENGTH == 0:
            clip_result = self._run_clip_inference(list(self._frame_buffer))
            if clip_result is not None:
                self._latest_result = clip_result
                self._clip_results.append(clip_result)
            return clip_result

        return None

    def _run_clip_inference(self, frames_rgb: list[np.ndarray]) -> dict | None:
        """Run VideoMAE or TimeSformer on a clip of frames."""
        if self.use_videomae and _load_videomae():
            return self._videomae_inference(frames_rgb)
        if _load_timesformer():
            return self._timesformer_inference(frames_rgb[:TIMESFORMER_FRAMES])
        return self._optical_flow_classify()

    def _videomae_inference(self, frames_rgb: list[np.ndarray]) -> dict | None:
        """VideoMAE clip classification."""
        try:
            import torch
            from PIL import Image as PILImage

            pil_frames = [PILImage.fromarray(f) for f in frames_rgb]
            inputs = _videomae_processor(pil_frames, return_tensors="pt")

            with torch.no_grad():
                outputs = _videomae_model(**inputs)

            logits = outputs.logits[0]
            probs = torch.softmax(logits, dim=-1)
            top5_prob, top5_idx = probs.topk(5)

            best_action = "normal_activity"
            best_conf = 0.0
            best_security_cat = "normal_activity"

            for prob, idx in zip(top5_prob.tolist(), top5_idx.tolist()):
                label = _videomae_model.config.id2label[idx].lower()
                sec_cat = KINETICS_SECURITY_MAP.get(label)
                if sec_cat and prob > best_conf:
                    best_action = label
                    best_conf = prob
                    best_security_cat = sec_cat

            if best_conf < 0.15:
                # No security-relevant action detected at meaningful confidence
                top_label = _videomae_model.config.id2label[top5_idx[0].item()].lower()
                best_security_cat = "normal_activity"
                best_conf = float(top5_prob[0])

            return _make_result(best_security_cat, best_conf,
                                raw_label=best_action, source="videomae")
        except Exception as e:
            logger.error("VideoMAE inference error: %s", e)
            return None

    def _timesformer_inference(self, frames_rgb: list[np.ndarray]) -> dict | None:
        """TimeSformer clip classification."""
        try:
            import torch
            from PIL import Image as PILImage

            pil_frames = [PILImage.fromarray(f) for f in frames_rgb]
            inputs = _timesformer_processor(pil_frames, return_tensors="pt")

            with torch.no_grad():
                outputs = _timesformer_model(**inputs)

            logits = outputs.logits[0]
            probs = torch.softmax(logits, dim=-1)
            top_prob, top_idx = probs.max(dim=-1)
            label = _timesformer_model.config.id2label[top_idx.item()].lower()
            sec_cat = KINETICS_SECURITY_MAP.get(label, "normal_activity")
            return _make_result(sec_cat, float(top_prob), raw_label=label, source="timesformer")
        except Exception as e:
            logger.error("TimeSformer inference error: %s", e)
            return None

    def _optical_flow_classify(self) -> dict:
        """Classify based on accumulated optical flow scores when no deep model available."""
        if not self._motion_scores:
            return _make_result("normal_activity", 0.0, source="optical_flow")

        recent = list(self._motion_scores)[-10:]
        avg_motion = float(np.mean(recent))
        peak_motion = float(np.max(recent))

        if peak_motion > 20.0:
            return _make_result("fighting", min(peak_motion / 30.0, 0.9), source="optical_flow")
        if avg_motion > 10.0:
            return _make_result("running", min(avg_motion / 15.0, 0.85), source="optical_flow")
        if avg_motion > 5.0:
            return _make_result("suspicious_movement", min(avg_motion / 10.0, 0.7), source="optical_flow")
        return _make_result("normal_activity", 1.0 - (avg_motion / 5.0), source="optical_flow")

    def get_latest_action(self) -> dict:
        """Return the most recent action classification."""
        return self._latest_result

    def get_action_history(self) -> list[dict]:
        """Return recent clip-level classifications."""
        return list(self._clip_results)

    def is_alert_worthy(self, result: dict | None = None) -> bool:
        """True if the current action warrants a security alert."""
        r = result or self._latest_result
        return (
            r["security_category"] in ("fighting", "falling", "suspicious_movement")
            and r["confidence"] >= 0.55
        )


def _make_result(
    security_category: str,
    confidence: float,
    raw_label: str | None = None,
    source: str = "unknown",
) -> dict:
    severity_map = {
        "fighting": "critical",
        "falling": "high",
        "crowd_formation": "high",
        "running": "medium",
        "suspicious_movement": "medium",
        "loitering": "low",
        "normal_activity": "none",
    }
    description_map = {
        "fighting": "Physical altercation detected between individuals",
        "falling": "Person falling or collapsing detected",
        "crowd_formation": "Unusual crowd gathering detected",
        "running": "Person running at speed — possible pursuit or flight",
        "suspicious_movement": "Suspicious body movement pattern detected",
        "loitering": "Extended stationary presence in area",
        "normal_activity": "Normal activity",
    }
    return {
        "security_category": security_category,
        "raw_kinetics_label": raw_label or security_category,
        "confidence": round(confidence, 3),
        "severity": severity_map.get(security_category, "low"),
        "description": description_map.get(security_category, "Unknown action"),
        "source": source,
    }


# Global per-camera registry
_camera_action_services: dict[str, VideoActionService] = {}


def get_video_action_service(camera_id: str) -> VideoActionService:
    """Get or create a VideoActionService for a camera."""
    if camera_id not in _camera_action_services:
        _camera_action_services[camera_id] = VideoActionService(camera_id)
    return _camera_action_services[camera_id]
