"""routes/zones.py — GET /zones"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from db.database import get_db
from db import crud
from schemas.events import ZonesResponse, ZoneMetrics

router = APIRouter()


@router.get("/zones", response_model=ZonesResponse, summary="Per-zone analytics")
def get_zones(db: Session = Depends(get_db)):
    """
    Per-zone breakdown:
    - Unique visitors
    - Average and max dwell time
    - Share of total footfall

    Zones: entrance, makeup_zone, skincare_zone, haircare_zone, checkout_zone
    """
    footfall_data = crud.get_zone_footfall(db)
    dwell_data    = crud.get_avg_dwell_by_zone(db)

    # Build lookup for dwell data
    dwell_lookup = {d["zone"]: d for d in dwell_data}
    total_visitors = sum(z["unique_visitors"] for z in footfall_data) or 1

    zone_metrics = []
    for z in footfall_data:
        zone_name = z["zone"]
        dwell_info = dwell_lookup.get(zone_name, {})
        zone_metrics.append(ZoneMetrics(
            zone              = zone_name,
            unique_visitors   = z["unique_visitors"],
            avg_dwell_seconds = round(float(dwell_info.get("avg_dwell_seconds") or 0), 1),
            max_dwell_seconds = round(float(dwell_info.get("max_dwell_seconds") or 0), 1),
            share_of_footfall = round(z["unique_visitors"] / total_visitors * 100, 1),
        ))

    return ZonesResponse(zones=zone_metrics)
