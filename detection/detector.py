"""
detector.py
───────────
YOLOv8-based person detector. Returns normalized detections per frame.
"""

import numpy as np
from pathlib import Path
from typing import List, Tuple
from loguru import logger
from ultralytics import YOLO


class PersonDetector:
    """
    Wraps YOLOv8 to detect persons (class 0) in video frames.
    Returns list of [x1, y1, x2, y2, confidence] in pixel coords.
    """

    PERSON_CLASS_ID = 0

    def __init__(
        self,
        model_name: str = "yolov8n.pt",
        confidence_threshold: float = 0.40,
        device: str = "auto",
    ):
        self.conf = confidence_threshold
        if device == "auto":
            import torch
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device

        logger.info(f"Loading YOLO model: {model_name} on {self.device}")
        self.model = YOLO(model_name)
        self.model.to(self.device)
        logger.info("YOLO model loaded ✓")

    def detect(self, frame: np.ndarray) -> List[List[float]]:
        """
        Args:
            frame: BGR numpy array (H, W, 3)

        Returns:
            List of [x1, y1, x2, y2, confidence] for each detected person.
        """
        results = self.model(
            frame,
            conf=self.conf,
            classes=[self.PERSON_CLASS_ID],
            verbose=False,
            device=self.device,
        )[0]

        detections = []
        if results.boxes is not None:
            for box in results.boxes:
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                conf = float(box.conf[0].cpu().numpy())
                detections.append([float(x1), float(y1), float(x2), float(y2), conf])

        return detections

    def detect_batch(self, frames: List[np.ndarray]) -> List[List[List[float]]]:
        """Batch inference for efficiency."""
        results = self.model(
            frames,
            conf=self.conf,
            classes=[self.PERSON_CLASS_ID],
            verbose=False,
            device=self.device,
        )
        batch_dets = []
        for r in results:
            dets = []
            if r.boxes is not None:
                for box in r.boxes:
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    conf = float(box.conf[0].cpu().numpy())
                    dets.append([float(x1), float(y1), float(x2), float(y2), conf])
            batch_dets.append(dets)
        return batch_dets
