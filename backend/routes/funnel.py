"""routes/funnel.py — GET /funnel"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db.database import get_db
from db import crud
from schemas.events import FunnelResponse, FunnelStage

router = APIRouter()


@router.get("/funnel", response_model=FunnelResponse, summary="Customer conversion funnel")
def get_funnel(db: Session = Depends(get_db)):
    """
    4-stage conversion funnel showing customer drop-off at each stage:

    1. **Entered** — walked into the store
    2. **Browsed** — visited at least one product zone
    3. **Engaged** — dwelled > 60 seconds (picked up / examined products)
    4. **Purchased** — completed a transaction

    The funnel reveals where customers are lost and helps optimize store layout.
    """
    data = crud.get_funnel_data(db)

    entered   = data["entered"]
    browsed   = min(data["browsed_zones"], entered) if entered > 0 else 0
    engaged   = min(data["engaged"],       browsed) if browsed > 0 else 0
    purchased = min(data["purchased"],     engaged) if entered > 0 else data["purchased"]

    # Base percentage on entered; if no CCTV data yet, use purchased as proxy denominator
    base = entered if entered > 0 else max(purchased, 1)

    stages = [
        FunnelStage(
            stage="entered",
            count=entered,
            percentage=100.0,
            drop_off=0.0,
        ),
        FunnelStage(
            stage="browsed_zones",
            count=browsed,
            percentage=round(browsed / base * 100, 1) if base > 0 else 0.0,
            drop_off=round((entered - browsed) / base * 100, 1) if base > 0 else 0.0,
        ),
        FunnelStage(
            stage="engaged",
            count=engaged,
            percentage=round(engaged / base * 100, 1) if base > 0 else 0.0,
            drop_off=round((browsed - engaged) / base * 100, 1) if base > 0 else 0.0,
        ),
        FunnelStage(
            stage="purchased",
            count=purchased,
            percentage=round(purchased / base * 100, 1) if base > 0 else 0.0,
            drop_off=round((engaged - purchased) / base * 100, 1) if base > 0 and engaged >= purchased else 0.0,
        ),
    ]

    return FunnelResponse(stages=stages)
