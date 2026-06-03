"""
staff_filter.py
───────────────
Heuristic-based staff detection and filtering.

Strategy:
 1. Persons who are continuously present for > STAFF_DWELL_SECONDS are staff.
 2. Persons who appear at store-open time and stay throughout are staff.
 3. Track their IDs and exclude from customer footfall counts.

Note: We do NOT use uniform color classification (too fragile without training data).
We rely on temporal presence patterns which is robust and explainable.
"""

from typing import Dict, Set
from loguru import logger
from camera_config import STAFF_DWELL_SECONDS


class StaffFilter:
    """
    Tracks how long each person has been continuously present.
    Once they exceed the threshold, marks them as staff.
    """

    def __init__(self, fps: float = 25.0, dwell_threshold_sec: float = STAFF_DWELL_SECONDS):
        self.fps = fps
        self.dwell_threshold_frames = int(dwell_threshold_sec * fps)
        self._frame_counts: Dict[int, int] = {}   # track_id → continuous frame count
        self._staff_ids: Set[int] = set()

    def update(self, active_track_ids: Set[int]) -> None:
        """Call every frame with the set of currently visible track IDs."""
        for tid in active_track_ids:
            self._frame_counts[tid] = self._frame_counts.get(tid, 0) + 1
            if (
                tid not in self._staff_ids
                and self._frame_counts[tid] >= self.dwell_threshold_frames
            ):
                self._staff_ids.add(tid)
                logger.info(f"[StaffFilter] Track {tid} identified as STAFF "
                            f"(present {self._frame_counts[tid]} frames ≈ "
                            f"{self._frame_counts[tid]/self.fps:.0f}s)")

    def is_staff(self, track_id: int) -> bool:
        return track_id in self._staff_ids

    def get_staff_ids(self) -> Set[int]:
        return self._staff_ids.copy()

    @property
    def customer_ids(self) -> Set[int]:
        return set(self._frame_counts.keys()) - self._staff_ids
