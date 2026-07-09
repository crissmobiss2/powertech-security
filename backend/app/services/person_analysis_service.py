"""
Advanced person analysis using DeepFace + MediaPipe.

DeepFace provides real deep-learning-based:
- Emotion detection (7 classes via FER-2013 trained model)
- Age estimation (regression, ±5 years accuracy)
- Gender classification (binary, >96% accuracy)

MediaPipe provides full-body pose landmark detection for
body language interpretation.
"""
import logging
import os
from datetime import datetime, timezone

import numpy as np

logger = logging.getLogger(__name__)

_cv2 = None
_mp = None
_deepface = None
_mivolo = None


def _get_cv2():
    global _cv2
    if _cv2 is None:
        import cv2
        _cv2 = cv2
    return _cv2


def _get_mediapipe():
    global _mp
    if _mp is None:
        import mediapipe as mp
        _mp = mp
    return _mp


def _get_deepface():
    global _deepface
    if _deepface is None:
        try:
            from deepface import DeepFace
            _deepface = DeepFace
            logger.info("DeepFace loaded")
        except Exception as e:
            logger.warning("DeepFace unavailable: %s", e)
    return _deepface


def _get_mivolo():
    """
    Lazy-load MiVOLO age/gender estimator.

    MiVOLO uses a ViT model trained on Lagenda + IMDB-clean datasets,
    taking both face AND body bounding boxes for more accurate estimation.
    Install: pip install git+https://github.com/WildChlamydia/MiVOLO.git
    Falls back to DeepFace if unavailable.
    """
    global _mivolo
    if _mivolo is not None:
        return _mivolo
    try:
        from mivolo.model.mi_volo import MiVOLO
        import torch
        checkpoint = os.getenv("MIVOLO_CHECKPOINT", "")
        if not checkpoint:
            logger.debug("MIVOLO_CHECKPOINT not set — MiVOLO disabled, using DeepFace fallback")
            return None
        model = MiVOLO(
            checkpoint,
            device="cpu",
            half=False,
            use_persons=True,
            disable_faces=False,
        )
        _mivolo = model
        logger.info("MiVOLO age/gender model loaded from %s", checkpoint)
        return _mivolo
    except ImportError:
        return None  # Silent — DeepFace handles it
    except Exception as e:
        logger.warning("MiVOLO load failed: %s", e)
        return None


THREAT_EMOTIONS = {"angry", "fear", "disgust"}
CALM_EMOTIONS = {"happy", "neutral"}

AGE_RANGES = [
    (0, 5, "infant"), (6, 12, "child"), (13, 17, "teenager"),
    (18, 25, "young_adult"), (26, 35, "adult"), (36, 50, "middle_aged"),
    (51, 65, "senior"), (66, 120, "elderly"),
]

BODY_INDICATORS = {
    "aggressive_stance": 0.8,
    "hands_concealed": 0.7,
    "hands_raised": 0.5,
    "hunched_posture": 0.4,
    "peripheral_position": 0.2,
    "close_proximity": 0.25,
}


class PersonAnalysisService:
    """Full-spectrum person analysis: emotion, age/gender, body language."""

    def __init__(self):
        self._pose_detector = None

    def _load_pose(self):
        if self._pose_detector is not None:
            return
        try:
            mp = _get_mediapipe()
            self._pose_detector = mp.solutions.pose.Pose(
                static_image_mode=False,
                model_complexity=1,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5,
            )
        except Exception as e:
            logger.warning("MediaPipe pose unavailable: %s", e)

    def analyze_person_full(
        self,
        frame: np.ndarray,
        face_bbox: dict,
        person_bbox: dict | None = None,
    ) -> dict:
        """
        Complete analysis of a detected person from a frame.
        Returns demographics, emotion, body language, threat assessment.
        """
        cv2 = _get_cv2()
        x, y, w, h = face_bbox["x"], face_bbox["y"], face_bbox["w"], face_bbox["h"]
        fh, fw = frame.shape[:2]
        x, y = max(0, x), max(0, y)
        face_crop = frame[y:min(y + h, fh), x:min(x + w, fw)]

        if face_crop.size == 0:
            return self._empty_analysis()

        # Use MiVOLO for age/gender if available (more accurate, uses full body)
        # Otherwise fall back to DeepFace face-only analysis
        demographics = self._mivolo_demographics(face_crop, frame, person_bbox) or \
                       self._deepface_demographics(face_crop)
        emotion = self._deepface_emotion(face_crop)
        body_language = self._analyze_body_language(frame, face_bbox, person_bbox)
        appearance = self._analyze_appearance(frame, face_bbox, person_bbox)
        threat_score = self._compute_threat_score(emotion, body_language)

        return {
            "demographics": demographics,
            "emotion": emotion,
            "body_language": body_language,
            "appearance": appearance,
            "threat_assessment": {
                "score": threat_score,
                "level": self._threat_level(threat_score),
                "factors": self._threat_factors(emotion, body_language),
            },
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        }

    def _mivolo_demographics(
        self,
        face_crop: np.ndarray,
        frame: np.ndarray,
        person_bbox: dict | None,
    ) -> dict | None:
        """
        MiVOLO full-body age/gender estimation.
        Uses both face and body bounding boxes for higher accuracy.
        Returns None if MiVOLO is not installed or checkpoint not configured.
        """
        model = _get_mivolo()
        if model is None:
            return None
        try:
            cv2 = _get_cv2()
            # Prepare body crop if bbox available
            body_img = None
            if person_bbox:
                px, py = person_bbox.get("x", 0), person_bbox.get("y", 0)
                pw, ph = person_bbox.get("w", 0), person_bbox.get("h", 0)
                fh, fw = frame.shape[:2]
                body_crop = frame[max(0, py):min(py + ph, fh), max(0, px):min(px + pw, fw)]
                if body_crop.size > 0:
                    body_img = cv2.resize(body_crop, (224, 224))

            # MiVOLO inference
            face_resized = cv2.resize(face_crop, (224, 224))
            result = model.predict(face_resized, body_img)

            age = int(result.get("age", 0))
            gender_raw = result.get("gender", "")
            gender = "male" if gender_raw.lower() in ("male", "m") else "female"
            age_range = next((l for lo, hi, l in AGE_RANGES if lo <= age <= hi), "adult")

            return {
                "estimated_age": age,
                "age_range": age_range,
                "age_confidence": round(result.get("age_confidence", 0.85), 3),
                "gender": gender,
                "gender_confidence": round(result.get("gender_confidence", 0.85), 3),
                "ethnicity": None,
                "source": "mivolo",
            }
        except Exception as e:
            logger.debug("MiVOLO inference failed: %s", e)
            return None

    def _deepface_demographics(self, face_crop: np.ndarray) -> dict:
        """Age + gender via DeepFace (real model inference)."""
        DeepFace = _get_deepface()
        result = {
            "estimated_age": None,
            "age_range": None,
            "age_confidence": 0.0,
            "gender": None,
            "gender_confidence": 0.0,
            "ethnicity": None,
        }

        if DeepFace is not None:
            try:
                analysis = DeepFace.analyze(
                    img_path=face_crop,
                    actions=["age", "gender"],
                    detector_backend="skip",
                    enforce_detection=False,
                    silent=True,
                )
                if isinstance(analysis, list):
                    analysis = analysis[0]

                age = int(analysis.get("age", 0))
                result["estimated_age"] = age
                result["age_confidence"] = 0.8

                dominant_gender = analysis.get("dominant_gender", "")
                gender_scores = analysis.get("gender", {})
                if dominant_gender.lower() in ("man", "male"):
                    result["gender"] = "male"
                    result["gender_confidence"] = round(gender_scores.get("Man", 0) / 100, 3)
                elif dominant_gender.lower() in ("woman", "female"):
                    result["gender"] = "female"
                    result["gender_confidence"] = round(gender_scores.get("Woman", 0) / 100, 3)

                for low, high, label in AGE_RANGES:
                    if low <= age <= high:
                        result["age_range"] = label
                        break

            except Exception as e:
                logger.debug("DeepFace demographics failed: %s", e)
                result.update(self._fallback_demographics(face_crop))
        else:
            result.update(self._fallback_demographics(face_crop))

        return result

    def _fallback_demographics(self, face_crop: np.ndarray) -> dict:
        """Simple heuristic demographics when DeepFace is unavailable."""
        cv2 = _get_cv2()
        gray = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY)
        wrinkle_score = cv2.Laplacian(gray, cv2.CV_64F).var()
        if wrinkle_score > 1000:
            age = 55
        elif wrinkle_score > 500:
            age = 40
        elif wrinkle_score > 200:
            age = 30
        elif wrinkle_score > 80:
            age = 22
        else:
            age = 16
        age_range = next((l for lo, hi, l in AGE_RANGES if lo <= age <= hi), "adult")
        return {"estimated_age": age, "age_range": age_range, "age_confidence": 0.3,
                "gender": None, "gender_confidence": 0.0, "ethnicity": None}

    def _deepface_emotion(self, face_crop: np.ndarray) -> dict:
        """Emotion detection via DeepFace FER model."""
        DeepFace = _get_deepface()

        if DeepFace is not None:
            try:
                analysis = DeepFace.analyze(
                    img_path=face_crop,
                    actions=["emotion"],
                    detector_backend="skip",
                    enforce_detection=False,
                    silent=True,
                )
                if isinstance(analysis, list):
                    analysis = analysis[0]

                emotions_raw = analysis.get("emotion", {})
                total = sum(emotions_raw.values()) or 1.0
                scores = {k.lower(): round(v / total, 3) for k, v in emotions_raw.items()}
                primary = analysis.get("dominant_emotion", "neutral").lower()
                confidence = scores.get(primary, 0.0)

                mood_map = {
                    "happy": "positive", "angry": "hostile", "disgust": "hostile",
                    "fear": "distressed", "sad": "distressed", "surprise": "alert",
                    "neutral": "neutral",
                }
                return {
                    "primary_emotion": primary,
                    "confidence": confidence,
                    "all_emotions": scores,
                    "mood_category": mood_map.get(primary, "neutral"),
                    "is_threat_indicator": primary in THREAT_EMOTIONS,
                    "valence": round(
                        scores.get("happy", 0) + scores.get("neutral", 0) * 0.5
                        - scores.get("angry", 0) - scores.get("fear", 0)
                        - scores.get("disgust", 0) - scores.get("sad", 0) * 0.5,
                        3,
                    ),
                }
            except Exception as e:
                logger.debug("DeepFace emotion failed: %s", e)

        return self._fallback_emotion(face_crop)

    def _fallback_emotion(self, face_crop: np.ndarray) -> dict:
        """Histogram-based heuristic emotion when DeepFace is unavailable."""
        cv2 = _get_cv2()
        gray = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY)
        resized = cv2.resize(gray, (48, 48))
        brightness = resized.mean()
        contrast = resized.std()
        mouth = resized[32:44, 12:36].std()
        eyebrow = resized[8:18, 10:38].std()

        scores = {"neutral": 0.3, "happy": 0.0, "sad": 0.0, "angry": 0.0,
                  "surprise": 0.0, "fear": 0.0, "disgust": 0.0}
        if mouth > 45:
            scores["happy"] += 0.4
        if eyebrow > 40:
            scores["angry"] += 0.3
        if brightness < 100:
            scores["sad"] += 0.2
        if contrast > 60:
            scores["surprise"] += 0.15

        total = sum(scores.values()) or 1
        scores = {k: round(v / total, 3) for k, v in scores.items()}
        primary = max(scores, key=scores.get)
        return {
            "primary_emotion": primary,
            "confidence": scores[primary],
            "all_emotions": scores,
            "mood_category": "neutral",
            "is_threat_indicator": primary in THREAT_EMOTIONS,
            "valence": 0.0,
        }

    def _analyze_body_language(
        self,
        frame: np.ndarray,
        face_bbox: dict,
        person_bbox: dict | None,
    ) -> dict:
        """MediaPipe pose landmark body language analysis."""
        cv2 = _get_cv2()
        self._load_pose()

        result = {
            "posture": "unknown", "stance": "unknown", "hand_position": "unknown",
            "movement_type": "stationary", "indicators": [], "confidence": 0.0,
        }

        if self._pose_detector is not None and person_bbox:
            px, py = person_bbox.get("x", 0), person_bbox.get("y", 0)
            pw, ph = person_bbox.get("w", 0), person_bbox.get("h", 0)
            fh, fw = frame.shape[:2]
            crop = frame[max(0, py):min(py + ph, fh), max(0, px):min(px + pw, fw)]
            if crop.size > 0:
                rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
                pose_result = self._pose_detector.process(rgb)
                if pose_result.pose_landmarks:
                    result = self._interpret_landmarks(pose_result.pose_landmarks.landmark)
        else:
            # Approximate from face bbox position
            face_h = face_bbox.get("h", 0)
            img_h, img_w = frame.shape[:2]
            cx = (face_bbox.get("x", 0) + face_bbox.get("w", 0) / 2) / max(img_w, 1)

            if face_h / max(img_h, 1) > 0.3:
                result["stance"] = "close"
                result["indicators"].append("close_proximity")
            if cx < 0.15 or cx > 0.85:
                result["indicators"].append("peripheral_position")
            result["confidence"] = 0.3

        return result

    def _interpret_landmarks(self, landmarks) -> dict:
        mp = _get_mediapipe()
        PL = mp.solutions.pose.PoseLandmark

        lw = landmarks[PL.LEFT_WRIST.value]
        rw = landmarks[PL.RIGHT_WRIST.value]
        ls = landmarks[PL.LEFT_SHOULDER.value]
        rs = landmarks[PL.RIGHT_SHOULDER.value]
        lh = landmarks[PL.LEFT_HIP.value]
        rh = landmarks[PL.RIGHT_HIP.value]
        nose = landmarks[PL.NOSE.value]

        indicators = []
        shoulder_w = abs(ls.x - rs.x)
        hip_w = abs(lh.x - rh.x)

        hands_raised = lw.y < ls.y or rw.y < rs.y
        hands_behind = lw.visibility < 0.3 and rw.visibility < 0.3
        wide_stance = hip_w > shoulder_w * 1.3
        hunched = nose.y > ls.y

        posture = "hunched" if hunched else "upright"
        if hunched:
            indicators.append("hunched_posture")

        hand_pos = "at_sides"
        if hands_raised:
            hand_pos = "raised"
            indicators.append("hands_raised")
        elif hands_behind:
            hand_pos = "concealed"
            indicators.append("hands_concealed")

        stance = "wide" if wide_stance else "normal"
        if wide_stance:
            indicators.append("aggressive_stance")

        return {
            "posture": posture, "stance": stance, "hand_position": hand_pos,
            "movement_type": "stationary", "indicators": indicators, "confidence": 0.75,
        }

    def _analyze_appearance(
        self,
        frame: np.ndarray,
        face_bbox: dict,
        person_bbox: dict | None,
    ) -> dict:
        """Dominant clothing colors and accessory detection."""
        cv2 = _get_cv2()
        region = person_bbox or face_bbox
        x = max(0, region.get("x", 0))
        y = max(0, region.get("y", 0))
        w, h = region.get("w", 0), region.get("h", 0)
        fh, fw = frame.shape[:2]

        result = {
            "dominant_colors": [], "has_bag": False,
            "has_hat": False, "has_mask": False, "clothing_description": "unknown",
        }

        torso = frame[y + int(h * 0.25):min(y + int(h * 0.65), fh), x:min(x + w, fw)]
        if torso.size > 0:
            hsv = cv2.cvtColor(torso, cv2.COLOR_BGR2HSV)
            color_ranges = [
                ([0, 0, 0], [180, 255, 50], "black"),
                ([0, 0, 200], [180, 30, 255], "white"),
                ([0, 100, 100], [10, 255, 255], "red"),
                ([100, 100, 100], [130, 255, 255], "blue"),
                ([35, 100, 100], [85, 255, 255], "green"),
                ([20, 100, 100], [35, 255, 255], "yellow"),
                ([0, 0, 50], [180, 50, 200], "gray"),
            ]
            colors = []
            for lo, hi, name in color_ranges:
                mask = cv2.inRange(hsv, np.array(lo), np.array(hi))
                ratio = mask.sum() / (255 * max(mask.size, 1))
                if ratio > 0.15:
                    colors.append({"color": name, "percentage": round(ratio * 100, 1)})
            colors.sort(key=lambda c: c["percentage"], reverse=True)
            result["dominant_colors"] = colors[:3]
            if colors:
                result["clothing_description"] = f"{colors[0]['color']} clothing"

        above = frame[max(0, y - int(h * 0.5)):y, x:min(x + w, fw)]
        if above.size > 0:
            edges = cv2.Canny(cv2.cvtColor(above, cv2.COLOR_BGR2GRAY), 50, 150)
            if edges.sum() > edges.size * 30:
                result["has_hat"] = True

        return result

    def _compute_threat_score(self, emotion: dict, body_language: dict) -> float:
        score = 0.0
        if emotion.get("is_threat_indicator"):
            score += 0.3 * emotion.get("confidence", 0.5)
        for ind in body_language.get("indicators", []):
            score += BODY_INDICATORS.get(ind, 0.0) * 0.35
        if emotion.get("valence", 0) < -0.3:
            score += 0.1
        return round(min(score, 1.0), 3)

    def _threat_level(self, score: float) -> str:
        if score >= 0.7: return "critical"
        if score >= 0.5: return "high"
        if score >= 0.3: return "medium"
        if score >= 0.1: return "low"
        return "none"

    def _threat_factors(self, emotion: dict, body_language: dict) -> list[str]:
        factors = []
        if emotion.get("is_threat_indicator"):
            factors.append(f"hostile_emotion:{emotion['primary_emotion']}")
        factors.extend(f"body:{i}" for i in body_language.get("indicators", []))
        if emotion.get("valence", 0) < -0.3:
            factors.append("negative_valence")
        return factors

    def _empty_analysis(self) -> dict:
        return {
            "demographics": {"estimated_age": None, "age_range": None, "age_confidence": 0.0,
                             "gender": None, "gender_confidence": 0.0, "ethnicity": None},
            "emotion": {"primary_emotion": "unknown", "confidence": 0.0, "all_emotions": {},
                        "mood_category": "unknown", "is_threat_indicator": False, "valence": 0.0},
            "body_language": {"posture": "unknown", "stance": "unknown", "hand_position": "unknown",
                              "movement_type": "unknown", "indicators": [], "confidence": 0.0},
            "appearance": {"dominant_colors": [], "clothing_description": "unknown"},
            "threat_assessment": {"score": 0.0, "level": "none", "factors": []},
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        }
