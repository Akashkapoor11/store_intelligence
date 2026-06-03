"""routes/hourly.py — GET /hourly"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db.database import get_db
from db import crud
from schemas.events import HourlyResponse

router = APIRouter()


@router.get("/hourly", response_model=HourlyResponse, summary="Hourly footfall breakdown")
def get_hourly(db: Session = Depends(get_db)):
    """
    Returns per-hour visitor counts for the store day.
    Used to render the hourly footfall bar chart on the dashboard.
    Falls back to realistic demo data if detection pipeline hasn't run.
    """
    data = crud.get_hourly_footfall(db)

    if data:
        return HourlyResponse(
            hours=data,
            peak_hour=max(data, key=lambda x: x["visitors"])["hour"] if data else None,
            source="live",
        )

    # Fallback: realistic demo data based on Brigade Road 10 April 2026 patterns
    demo = [
        {"hour": 12, "visitors": 8},
        {"hour": 13, "visitors": 12},
        {"hour": 14, "visitors": 15},
        {"hour": 15, "visitors": 18},
        {"hour": 16, "visitors": 22},
        {"hour": 17, "visitors": 28},
        {"hour": 18, "visitors": 35},
        {"hour": 19, "visitors": 42},
        {"hour": 20, "visitors": 38},
        {"hour": 21, "visitors": 25},
        {"hour": 22, "visitors": 12},
    ]
    return HourlyResponse(hours=demo, peak_hour=19, source="demo")
