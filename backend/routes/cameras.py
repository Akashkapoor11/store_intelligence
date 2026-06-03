"""
routes/cameras.py — GET /cameras
──────────────────────────────────
Per-camera analytics endpoint.
Shows footfall, zone coverage, and event counts broken down per camera.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import sqlalchemy as sa
from datetime import datetime
from typing import List
from pydantic import BaseModel, Field

from db.database import get_db

router = APIRouter()


class CameraMetrics(BaseModel):
    camera_id:         str
    primary_zone:      str
    total_events:      int  = Field(description="All events logged for this camera")
    person_entries:    int  = Field(description="person_entered events (CAM 3 only)")
    zone_entries:      int  = Field(description="zone_enter events")
    zone_exits:        int  = Field(description="zone_exit events with dwell data")
    unique_persons:    int  = Field(description="Distinct person IDs seen")
    avg_dwell_seconds: float= Field(description="Average zone dwell time (seconds)")
    staff_detected:    int  = Field(description="Staff-classified tracks seen")


class CamerasResponse(BaseModel):
    cameras:      List[CameraMetrics]
    generated_at: datetime = Field(default_factory=datetime.utcnow)


# Camera → zone mapping (mirrors camera_config.py)
_CAMERA_ZONE = {
    "CAM 1": "skincare_zone",
    "CAM 2": "makeup_zone",
    "CAM 3": "entrance",
    "CAM 4": "haircare_zone",
    "CAM 5": "checkout_zone",
}


@router.get("/cameras", response_model=CamerasResponse, summary="Per-camera analytics")
def get_cameras(db: Session = Depends(get_db)):
    """
    Returns analytics broken down per camera feed:

    - **total_events**: total rows in the events table for this camera
    - **person_entries**: customers who crossed the entry line (CAM 3)
    - **zone_entries / zone_exits**: zone transition event counts
    - **unique_persons**: distinct CCTV track IDs observed
    - **avg_dwell_seconds**: mean zone dwell across all zone_exit events
    - **staff_detected**: staff-classified persons (excluded from footfall)

    Useful for diagnosing camera coverage gaps and calibration issues.
    """
    rows = db.execute(sa.text("""
        SELECT
            camera_id,
            COUNT(*)                                                        AS total_events,
            COUNT(*) FILTER (WHERE event_type = 'person_entered')          AS person_entries,
            COUNT(*) FILTER (WHERE event_type = 'zone_enter')              AS zone_entries,
            COUNT(*) FILTER (WHERE event_type = 'zone_exit')               AS zone_exits,
            COUNT(DISTINCT person_id) FILTER (WHERE is_staff = FALSE)      AS unique_persons,
            COALESCE(AVG(dwell_seconds) FILTER (
                WHERE event_type = 'zone_exit' AND dwell_seconds IS NOT NULL
                  AND is_staff = FALSE
            ), 0)                                                           AS avg_dwell_seconds,
            COUNT(DISTINCT person_id) FILTER (WHERE is_staff = TRUE)       AS staff_detected
        FROM events
        WHERE camera_id IS NOT NULL
        GROUP BY camera_id
        ORDER BY camera_id
    """)).fetchall()

    cameras = []
    for r in rows:
        cameras.append(CameraMetrics(
            camera_id         = r.camera_id,
            primary_zone      = _CAMERA_ZONE.get(r.camera_id, "unknown"),
            total_events      = int(r.total_events),
            person_entries    = int(r.person_entries),
            zone_entries      = int(r.zone_entries),
            zone_exits        = int(r.zone_exits),
            unique_persons    = int(r.unique_persons),
            avg_dwell_seconds = round(float(r.avg_dwell_seconds), 1),
            staff_detected    = int(r.staff_detected),
        ))

    # If no data yet, return placeholder rows so reviewers can see the schema
    if not cameras:
        for cam_id, zone in _CAMERA_ZONE.items():
            cameras.append(CameraMetrics(
                camera_id=cam_id, primary_zone=zone,
                total_events=0, person_entries=0, zone_entries=0,
                zone_exits=0, unique_persons=0, avg_dwell_seconds=0.0,
                staff_detected=0,
            ))

    return CamerasResponse(cameras=cameras)
