"""
OCR service for license plates, text, and ID cards from CCTV footage.

Primary engine: PaddleOCR (paddlepaddle + paddleocr)
  - Supports 80+ languages including Filipino
  - Excellent at license plates, signage, and printed text
  - PP-OCRv4 model series (lightweight, production-grade)

Fallback: Florence-2 OCR task (scene_understanding_service)
  - Uses <OCR_WITH_REGION> task for text with bounding boxes
  - No additional install needed if Florence-2 is loaded
"""
import logging
import os

import numpy as np

logger = logging.getLogger(__name__)

PADDLE_LANG = os.getenv("PADDLE_OCR_LANG", "en")  # 'en', 'ch', 'fil', etc.
PADDLE_USE_GPU = os.getenv("PADDLE_USE_GPU", "false").lower() == "true"
PLATE_CONFIDENCE_THRESHOLD = 0.75

_paddle_ocr = None


def _load_paddle():
    global _paddle_ocr
    if _paddle_ocr is not None:
        return _paddle_ocr
    try:
        from paddleocr import PaddleOCR
        _paddle_ocr = PaddleOCR(
            use_angle_cls=True,
            lang=PADDLE_LANG,
            use_gpu=PADDLE_USE_GPU,
            show_log=False,
        )
        logger.info("PaddleOCR loaded (lang=%s, gpu=%s)", PADDLE_LANG, PADDLE_USE_GPU)
    except ImportError:
        logger.warning("PaddleOCR not installed — falling back to Florence-2")
    except Exception as e:
        logger.error("PaddleOCR load failed: %s", e)
    return _paddle_ocr


class OCRService:
    """Extract text from camera frames with coordinate output."""

    def read_frame(self, frame: np.ndarray, target: str = "general") -> dict:
        """
        Run OCR on a camera frame.

        Args:
            frame: BGR np.ndarray (OpenCV)
            target: hint for post-processing — "license_plate", "id_card", "general"

        Returns:
            {texts: [{text, confidence, bbox}], raw_text: str, source: str}
        """
        engine = _load_paddle()
        if engine is not None:
            return self._paddle_ocr(frame, engine, target)
        return self._florence_ocr(frame, target)

    def _paddle_ocr(self, frame: np.ndarray, engine, target: str) -> dict:
        try:
            import cv2
            # PaddleOCR expects RGB
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = engine.ocr(rgb, cls=True)

            texts = []
            if results and results[0]:
                for line in results[0]:
                    if line is None:
                        continue
                    bbox_pts, (text, conf) = line
                    if conf < PLATE_CONFIDENCE_THRESHOLD:
                        continue
                    x_coords = [p[0] for p in bbox_pts]
                    y_coords = [p[1] for p in bbox_pts]
                    texts.append({
                        "text": text,
                        "confidence": round(float(conf), 3),
                        "bbox": [min(x_coords), min(y_coords), max(x_coords), max(y_coords)],
                    })

            raw_text = " ".join(t["text"] for t in texts)

            if target == "license_plate":
                texts = self._filter_plates(texts)
                raw_text = " ".join(t["text"] for t in texts)

            return {
                "texts": texts,
                "raw_text": raw_text,
                "source": "paddleocr",
                "target": target,
                "error": None,
            }
        except Exception as e:
            logger.error("PaddleOCR inference failed: %s", e)
            return self._florence_ocr(frame, target)

    def _florence_ocr(self, frame: np.ndarray, target: str) -> dict:
        """Florence-2 OCR fallback."""
        try:
            from app.services.scene_understanding_service import get_scene_service
            svc = get_scene_service()
            florence_texts = svc.read_text(frame)

            texts = [
                {
                    "text": t["text"],
                    "confidence": 0.85,  # Florence-2 doesn't output confidence
                    "bbox": t.get("bbox", []),
                }
                for t in florence_texts
                if t.get("text")
            ]
            raw_text = " ".join(t["text"] for t in texts)

            return {
                "texts": texts,
                "raw_text": raw_text,
                "source": "florence2_ocr",
                "target": target,
                "error": None,
            }
        except Exception as e:
            logger.error("Florence-2 OCR fallback failed: %s", e)
            return {
                "texts": [],
                "raw_text": "",
                "source": "none",
                "target": target,
                "error": str(e),
            }

    def _filter_plates(self, texts: list[dict]) -> list[dict]:
        """
        Post-filter OCR results to likely license plate strings.
        Philippine plates: ABC 1234 or 1234 ABC pattern.
        """
        import re
        plate_pattern = re.compile(
            r"^([A-Z]{2,3}\s?\d{4}|\d{4}\s?[A-Z]{2,3}|[A-Z]{1,3}\s?\d{3}[A-Z]?)$",
            re.IGNORECASE,
        )
        plate_texts = [t for t in texts if plate_pattern.match(t["text"].strip())]
        if plate_texts:
            return plate_texts
        # Fallback: return any text that looks plate-like (alphanumeric 5-8 chars)
        return [t for t in texts if re.match(r"^[A-Z0-9\s]{5,8}$", t["text"].strip(), re.IGNORECASE)]

    def read_license_plate(self, frame: np.ndarray) -> str | None:
        """
        Extract the most likely license plate string from the frame.
        Returns the cleaned plate text or None if nothing found.
        """
        result = self.read_frame(frame, target="license_plate")
        texts = result.get("texts", [])
        if not texts:
            return None
        best = max(texts, key=lambda t: t["confidence"])
        return best["text"].upper().replace(" ", "")

    def read_region(self, frame: np.ndarray, bbox: list[int]) -> str:
        """OCR a specific rectangular region [x1, y1, x2, y2]."""
        x1, y1, x2, y2 = [int(v) for v in bbox]
        h, w = frame.shape[:2]
        crop = frame[max(0, y1):min(h, y2), max(0, x1):min(w, x2)]
        if crop.size == 0:
            return ""
        result = self.read_frame(crop, target="general")
        return result.get("raw_text", "")


_svc: OCRService | None = None


def get_ocr_service() -> OCRService:
    global _svc
    if _svc is None:
        _svc = OCRService()
    return _svc
