"""
zone_mapper.py
──────────────
Maps pixel-space bbox center coordinates to named store zones.
Uses the CameraConfig zone definitions from camera_config.py.
"""

from typing import Optional
from camera_config import CameraConfig, ZoneRegion, ZONE_UNKNOWN


class ZoneMapper:
    """
    Given a detection bbox and the camera config, determines which zone
    the detected person is currently in.
    """

    def __init__(self, cam_config: CameraConfig):
        self.cam_config = cam_config

    def get_zone(
        self,
        bbox: list,          # [x1, y1, x2, y2] in pixels
        frame_w: int,
        frame_h: int,
    ) -> str:
        """
        Convert pixel bbox → fractional center → zone name.

        Uses the bottom-center of the bbox (feet position) for more accurate
        zone attribution — this matters especially in wide-angle cameras.
        """
        x1, y1, x2, y2 = bbox
        # Use feet position (bottom center) for zone attribution
        cx = (x1 + x2) / 2 / frame_w
        cy = y2 / frame_h   # bottom of bbox = feet

        for zone in self.cam_config.zones:
            if zone.contains(cx, cy):
                return zone.name

        return self.cam_config.primary_zone  # fallback to camera's primary zone

    def is_crossing_entry_line(
        self,
        prev_cy_frac: Optional[float],
        curr_cy_frac: float,
        direction: str = "enter",  # "enter" | "exit"
    ) -> bool:
        """
        For entry/exit cameras, determine if a person crossed the line.

        Entry  = moving from outside (higher y fraction) into the store (lower y).
        Exit   = moving from inside (lower y fraction) to outside (higher y).

        In CAM 3 (entrance), the store interior is at the top of frame (y=0)
        and the street/mall corridor is at the bottom (y=1.0).
        """
        if prev_cy_frac is None:
            return False

        threshold = self.cam_config.entry_line_y

        if direction == "enter":
            # Was above the line, now below (moving into store)
            return prev_cy_frac < threshold and curr_cy_frac >= threshold
        else:
            # Was below the line, now above (moving out of store)
            return prev_cy_frac >= threshold and curr_cy_frac < threshold
