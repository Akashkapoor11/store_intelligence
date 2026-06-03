"""
tracker.py
──────────
ByteTrack-compatible multi-object tracker.
Wraps the SORT/ByteTrack algorithm using ultralytics' built-in tracker.
Each tracked person gets a persistent integer track_id across frames.
"""

import numpy as np
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from loguru import logger
from ultralytics import YOLO


@dataclass
class Track:
    track_id: int
    bbox: List[float]       # [x1, y1, x2, y2] in pixels
    confidence: float
    frame_num: int
    lost_frames: int = 0
    is_confirmed: bool = False
    history: List[List[float]] = field(default_factory=list)  # past bboxes


class ByteTracker:
    """
    Multi-object tracker using ultralytics' built-in ByteTrack.
    Produces stable track IDs across frames.
    """

    def __init__(self, model: YOLO, tracker_config: str = "bytetrack.yaml"):
        self.model = model
        self.tracker_config = tracker_config
        self._active_tracks: Dict[int, Track] = {}

    def update(
        self,
        frame: np.ndarray,
        frame_num: int,
        confidence_threshold: float = 0.40,
    ) -> List[Track]:
        """
        Run detection + tracking on a single frame.

        Returns list of currently active Track objects.
        """
        results = self.model.track(
            frame,
            persist=True,
            tracker=self.tracker_config,
            conf=confidence_threshold,
            classes=[0],   # persons only
            verbose=False,
        )

        current_ids = set()
        updated_tracks = []

        if results[0].boxes is not None and results[0].boxes.id is not None:
            boxes = results[0].boxes
            for i in range(len(boxes)):
                tid  = int(boxes.id[i].item())
                bbox = boxes.xyxy[i].cpu().numpy().tolist()
                conf = float(boxes.conf[i].item())

                if tid not in self._active_tracks:
                    self._active_tracks[tid] = Track(
                        track_id=tid,
                        bbox=bbox,
                        confidence=conf,
                        frame_num=frame_num,
                        is_confirmed=False,
                    )
                else:
                    t = self._active_tracks[tid]
                    t.bbox       = bbox
                    t.confidence = conf
                    t.frame_num  = frame_num
                    t.lost_frames = 0
                    t.history.append(bbox)
                    if len(t.history) >= 3:
                        t.is_confirmed = True

                current_ids.add(tid)
                updated_tracks.append(self._active_tracks[tid])

        # Increment lost_frames for absent tracks
        for tid in list(self._active_tracks.keys()):
            if tid not in current_ids:
                self._active_tracks[tid].lost_frames += 1

        return updated_tracks

    def get_center(self, track: Track) -> tuple:
        x1, y1, x2, y2 = track.bbox
        return ((x1 + x2) / 2, (y1 + y2) / 2)

    def get_all_active(self) -> Dict[int, Track]:
        return self._active_tracks
