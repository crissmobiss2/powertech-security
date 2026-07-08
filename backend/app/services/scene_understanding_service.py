"""
Scene understanding via Microsoft Florence-2.

Florence-2 is a unified vision model supporting multiple vision tasks
with a single architecture via task prompts. Well-suited for CCTV analysis.

Tasks supported:
  <CAPTION>                    — one-sentence scene description
  <DETAILED_CAPTION>           — multi-sentence description
  <DENSE_REGION_CAPTION>       — describe each region/object separately
  <OPEN_VOCABULARY_DETECTION>  — detect "person with weapon", "unattended bag"
  <OCR_WITH_REGION>            — read all text with bounding boxes
  <VQA>                        — "Is anyone running?" "How many people?"

HuggingFace: microsoft/Florence-2-base-ft (272M params)
"""
import logging
import os

import numpy as np

logger = logging.getLogger(__name__)

FLORENCE_MODEL_ID = os.getenv("FLORENCE_MODEL_ID", "microsoft/Florence-2-base-ft")

_model = None
_processor = None


def _load_florence():
    global _model, _processor
    if _model is not None:
        return _processor, _model
    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoProcessor

        _processor = AutoProcessor.from_pretrained(FLORENCE_MODEL_ID, trust_remote_code=True)
        _model = AutoModelForCausalLM.from_pretrained(
            FLORENCE_MODEL_ID,
            torch_dtype=torch.float32,
            trust_remote_code=True,
        )
        _model.eval()
        logger.info("Florence-2 loaded: %s", FLORENCE_MODEL_ID)
    except ImportError:
        logger.warning("transformers not installed — Florence-2 unavailable")
    except Exception as e:
        logger.error("Florence-2 load failed: %s", e)
    return _processor, _model


VALID_TASKS = {
    "caption": "<CAPTION>",
    "detailed_caption": "<DETAILED_CAPTION>",
    "dense_region_caption": "<DENSE_REGION_CAPTION>",
    "detect": "<OPEN_VOCABULARY_DETECTION>",
    "ocr": "<OCR_WITH_REGION>",
    "vqa": "<VQA>",
    "region_proposal": "<REGION_PROPOSAL>",
}


class SceneUnderstandingService:
    """Wraps Florence-2 for CCTV scene analysis tasks."""

    def analyze(
        self,
        image: "np.ndarray | PIL.Image.Image",
        task: str = "caption",
        query: str | None = None,
    ) -> dict:
        """
        Run Florence-2 on a frame.

        Args:
            image: BGR np.ndarray (OpenCV) or PIL.Image
            task:  one of VALID_TASKS keys or a raw Florence-2 task token
            query: required for 'vqa' and 'detect' tasks

        Returns:
            dict with 'task', 'result', 'raw', 'source'
        """
        processor, model = _load_florence()
        if model is None:
            return {"task": task, "result": None, "error": "florence2_unavailable", "source": "florence2"}

        try:
            from PIL import Image
            import torch

            if isinstance(image, np.ndarray):
                import cv2
                rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                pil_image = Image.fromarray(rgb)
            else:
                pil_image = image

            task_token = VALID_TASKS.get(task, task)
            prompt = task_token if query is None else f"{task_token}{query}"

            inputs = processor(text=prompt, images=pil_image, return_tensors="pt")

            with torch.no_grad():
                generated_ids = model.generate(
                    input_ids=inputs["input_ids"],
                    pixel_values=inputs["pixel_values"],
                    max_new_tokens=1024,
                    early_stopping=False,
                    do_sample=False,
                    num_beams=3,
                )

            raw_output = processor.batch_decode(generated_ids, skip_special_tokens=False)[0]
            parsed = processor.post_process_generation(
                raw_output,
                task=task_token,
                image_size=(pil_image.width, pil_image.height),
            )

            return {
                "task": task,
                "result": parsed,
                "raw": raw_output,
                "source": "florence2",
                "error": None,
            }
        except Exception as e:
            logger.error("Florence-2 inference error [%s]: %s", task, e)
            return {"task": task, "result": None, "error": str(e), "source": "florence2"}

    def caption(self, image: "np.ndarray") -> str:
        """Quick one-sentence scene caption."""
        result = self.analyze(image, task="caption")
        parsed = result.get("result", {})
        if isinstance(parsed, dict):
            return parsed.get("<CAPTION>", "")
        return str(parsed) if parsed else ""

    def detect_objects(self, image: "np.ndarray", query: str = "person") -> list[dict]:
        """
        Open-vocabulary detection: find 'person with weapon', 'unattended bag', etc.
        Returns list of {label, bbox: [x1,y1,x2,y2]}.
        """
        result = self.analyze(image, task="detect", query=query)
        parsed = result.get("result", {})
        bboxes = parsed.get("<OPEN_VOCABULARY_DETECTION>", {})
        objects = []
        if isinstance(bboxes, dict):
            labels = bboxes.get("labels", [])
            boxes = bboxes.get("bboxes", [])
            for label, box in zip(labels, boxes):
                objects.append({"label": label, "bbox": box})
        return objects

    def read_text(self, image: "np.ndarray") -> list[dict]:
        """OCR with bounding boxes. Returns list of {text, bbox}."""
        result = self.analyze(image, task="ocr")
        parsed = result.get("result", {})
        ocr_data = parsed.get("<OCR_WITH_REGION>", {})
        texts = []
        if isinstance(ocr_data, dict):
            for text, bbox in zip(ocr_data.get("labels", []), ocr_data.get("quad_boxes", [])):
                texts.append({"text": text, "bbox": bbox})
        return texts

    def ask(self, image: "np.ndarray", question: str) -> str:
        """Visual question answering. E.g. 'Is anyone running?'"""
        result = self.analyze(image, task="vqa", query=question)
        parsed = result.get("result", {})
        if isinstance(parsed, dict):
            return parsed.get("<VQA>", "")
        return str(parsed) if parsed else ""


_svc: SceneUnderstandingService | None = None


def get_scene_service() -> SceneUnderstandingService:
    global _svc
    if _svc is None:
        _svc = SceneUnderstandingService()
    return _svc
