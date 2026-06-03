"""
camera_config.py
────────────────
Ground-truth zone definitions for each camera based on visual inspection
of the actual CCTV footage frames from Brigade Road Bangalore store.

Zone boundaries are expressed as fractions of frame (0.0 → 1.0) so they
are resolution-independent.
"""

from dataclasses import dataclass, field
from typing import List, Tuple

# Zone names used throughout the system
ZONE_ENTRANCE   = "entrance"
ZONE_MAKEUP     = "makeup_zone"
ZONE_SKINCARE   = "skincare_zone"
ZONE_HAIRCARE   = "haircare_zone"
ZONE_CHECKOUT   = "checkout_zone"
ZONE_UNKNOWN    = "unknown"

ALL_ZONES = [ZONE_ENTRANCE, ZONE_MAKEUP, ZONE_SKINCARE,
             ZONE_HAIRCARE, ZONE_CHECKOUT]


@dataclass
class ZoneRegion:
    """Axis-aligned bounding box in fractional frame coords."""
    name: str
    x1: float   # left  (0.0 = leftmost pixel)
    y1: float   # top
    x2: float   # right (1.0 = rightmost pixel)
    y2: float   # bottom

    def contains(self, cx: float, cy: float) -> bool:
        """Returns True if point (cx, cy) — in fractions — is inside zone."""
        return self.x1 <= cx <= self.x2 and self.y1 <= cy <= self.y2


@dataclass
class CameraConfig:
    name: str
    filename: str           # MP4 filename inside the ZIP
    primary_zone: str       # dominant zone this camera monitors
    zones: List[ZoneRegion] = field(default_factory=list)
    is_entry_exit: bool = False
    entry_line_y: float = 0.85   # horizontal line fraction for entry/exit


# ─────────────────────────────────────────────────────────────────────────────
# Camera configurations derived from visual inspection of extracted frames and
# the official Store layouts provided in the ZIPs:
# ─────────────────────────────────────────────────────────────────────────────

CAMERA_CONFIGS = {
    # ── STORE 1 ──
    "CAM 1": CameraConfig(
        name="CAM 1",
        filename="Store 1/CAM 1 - zone.mp4",
        primary_zone=ZONE_SKINCARE,
        is_entry_exit=False,
        zones=[
            ZoneRegion(ZONE_SKINCARE,   0.0, 0.0, 0.65, 1.0),
            ZoneRegion(ZONE_CHECKOUT,   0.65, 0.3, 1.0, 1.0),
        ],
    ),
    "CAM 2": CameraConfig(
        name="CAM 2",
        filename="Store 1/CAM 2 - zone.mp4",
        primary_zone=ZONE_MAKEUP,
        is_entry_exit=False,
        zones=[
            ZoneRegion(ZONE_MAKEUP,     0.15, 0.0, 1.0, 1.0),
            ZoneRegion(ZONE_SKINCARE,   0.0,  0.0, 0.15, 1.0),
        ],
    ),
    "CAM 3": CameraConfig(
        name="CAM 3",
        filename="Store 1/CAM 3 - entry.mp4",
        primary_zone=ZONE_ENTRANCE,
        is_entry_exit=True,
        entry_line_y=0.75,
        zones=[
            ZoneRegion(ZONE_ENTRANCE,   0.0, 0.0, 1.0, 1.0),
        ],
    ),
    "CAM 5": CameraConfig(
        name="CAM 5",
        filename="Store 1/CAM 5 - billing.mp4",
        primary_zone=ZONE_CHECKOUT,
        is_entry_exit=False,
        zones=[
            ZoneRegion(ZONE_CHECKOUT,   0.0, 0.0, 1.0, 1.0),
        ],
    ),

    # ── STORE 2 ──
    "Store2_Entry1": CameraConfig(
        name="Store2_Entry1",
        filename="Store 2/entry 1.mp4",
        primary_zone=ZONE_ENTRANCE,
        is_entry_exit=True,
        entry_line_y=0.75,
        zones=[
            ZoneRegion(ZONE_ENTRANCE,   0.0, 0.0, 1.0, 1.0),
        ],
    ),
    "Store2_Entry2": CameraConfig(
        name="Store2_Entry2",
        filename="Store 2/entry 2.mp4",
        primary_zone=ZONE_ENTRANCE,
        is_entry_exit=True,
        entry_line_y=0.75,
        zones=[
            ZoneRegion(ZONE_ENTRANCE,   0.0, 0.0, 1.0, 1.0),
        ],
    ),
    "Store2_Zone": CameraConfig(
        name="Store2_Zone",
        filename="Store 2/zone.mp4",
        primary_zone=ZONE_MAKEUP,
        is_entry_exit=False,
        zones=[
            ZoneRegion(ZONE_MAKEUP,     0.0, 0.0, 1.0, 1.0),
        ],
    ),
    "Store2_Billing": CameraConfig(
        name="Store2_Billing",
        filename="Store 2/billing_area.mp4",
        primary_zone=ZONE_CHECKOUT,
        is_entry_exit=False,
        zones=[
            ZoneRegion(ZONE_CHECKOUT,   0.0, 0.0, 1.0, 1.0),
        ],
    ),
}

# Minimum pixels² a detected bbox must cover to count as a valid person
MIN_BBOX_AREA_FRACTION = 0.002   # 0.2% of frame area

# Maximum frames a track can be lost before we consider them gone
MAX_LOST_FRAMES = 30  # ~1 second at 30fps

# Staff are people who appear in frame for longer than this (likely employees)
STAFF_DWELL_SECONDS = 600  # 10 minutes continuous presence

# Re-entry cooldown: same person returning within this window = re-entry (not new visitor)
REENTRY_COOLDOWN_SECONDS = 120  # 2 minutes
