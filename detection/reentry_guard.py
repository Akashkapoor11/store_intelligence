"""
reentry_guard.py
────────────────
Prevents double-counting when the same person exits and re-enters the store.

Strategy:
 - When a person exits (disappears from entry camera after crossing line),
   record their appearance embedding and exit timestamp.
 - If a NEW track appears within REENTRY_COOLDOWN_SECONDS, check if their
   initial position is close to where the previous person exited.
 - If yes: same person → re-entry, not a new visitor.

Since we don't have ReID training here, we use position-based heuristic
for the entry camera (CAM 3) which has a narrow FOV at the door.
"""

from typing import Dict, Tuple, Optional
from datetime import datetime, timedelta
from loguru import logger
from camera_config import REENTRY_COOLDOWN_SECONDS


class ReentryGuard:
    """
    Tracks exit events and suppresses duplicate entry counts.
    Uses spatial proximity at the entry line as the matching signal.
    """

    def __init__(self, cooldown_seconds: float = REENTRY_COOLDOWN_SECONDS):
        self.cooldown = timedelta(seconds=cooldown_seconds)
        # Maps exit_position (cx_frac, cy_frac) → exit_timestamp
        self._recent_exits: Dict[int, Tuple[float, float, datetime]] = {}
        self._reentry_ids: set = set()    # global track IDs marked as re-entries

    def record_exit(self, track_id: int, cx_frac: float, cy_frac: float, ts: datetime):
        """Call when a person crosses the exit line."""
        self._recent_exits[track_id] = (cx_frac, cy_frac, ts)
        logger.debug(f"[ReentryGuard] Recorded exit for track {track_id} at {ts}")

    def is_reentry(
        self,
        new_track_id: int,
        cx_frac: float,
        cy_frac: float,
        ts: datetime,
        position_tolerance: float = 0.25,
    ) -> bool:
        """
        Returns True if this new track is likely a re-entry of a known exited person.
        """
        now = ts
        for tid, (ex, ey, exit_ts) in list(self._recent_exits.items()):
            # Expired entries — clean up
            if now - exit_ts > self.cooldown:
                del self._recent_exits[tid]
                continue

            # Check spatial proximity at entry door
            dist = ((cx_frac - ex) ** 2 + (cy_frac - ey) ** 2) ** 0.5
            if dist < position_tolerance:
                self._reentry_ids.add(new_track_id)
                logger.info(
                    f"[ReentryGuard] Track {new_track_id} is RE-ENTRY of {tid} "
                    f"(dist={dist:.3f}, gap={now - exit_ts})"
                )
                return True

        return False

    def get_reentry_ids(self) -> set:
        return self._reentry_ids.copy()
