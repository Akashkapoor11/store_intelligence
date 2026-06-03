"""routes/events.py — GET /events"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime

from db.database import get_db
from db import crud
from schemas.events import EventOut, EventsResponse

router = APIRouter()


@router.get(
    "/events",
    response_model=EventsResponse,
    summary="Raw event stream with schema validation",
)
def get_events(
    event_type: Optional[str] = Query(
        None,
        description="Filter by type: person_entered | zone_enter | zone_exit | person_exited | staff_detected",
    ),
    zone:       Optional[str] = Query(None, description="Filter by zone name"),
    camera_id:  Optional[str] = Query(None, description="Filter by camera: 'CAM 1', 'CAM 2', etc."),
    limit:      int           = Query(100,  ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """
    Structured event log from the CCTV detection pipeline.

    Each event carries: **event_id**, **event_type**, **person_id**, **timestamp**,
    **camera_id**, **zone**, **dwell_seconds**, **is_staff**, **confidence**, and **bbox**.

    Supports filtering by event type, zone, and camera.
    """
    rows = crud.get_events(
        db,
        event_type=event_type,
        zone=zone,
        camera_id=camera_id,
        limit=limit,
    )
    events = [EventOut.model_validate(r) for r in rows]
    return EventsResponse(events=events, total=len(events))
