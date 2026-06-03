"""routes/metrics.py — GET /metrics"""

import sqlalchemy as sa
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime

from db.database import get_db
from db import crud
from schemas.events import MetricsResponse

router = APIRouter()


@router.get("/metrics", response_model=MetricsResponse, summary="Store-level KPIs")
def get_metrics(db: Session = Depends(get_db)):
    """
    Returns the core store intelligence metrics:

    - **total_footfall**: unique customer entries detected
    - **total_buyers**: number of purchases (from sales CSV)
    - **conversion_rate_pct**: buyers / footfall × 100
    - **avg_dwell_time_sec**: average time a customer spends in store
    - **peak_hour**: busiest hour of the day
    - **revenue_per_visitor**: total GMV / footfall
    """
    footfall = crud.get_total_footfall(db)
    sales    = crud.get_sales_metrics(db)
    buyers   = sales["total_orders"]   # 1 order = 1 customer session

    conversion_rate = round((buyers / footfall * 100) if footfall > 0 else 0.0, 2)

    # Average dwell from zone_exit events
    dwell_data = crud.get_avg_dwell_by_zone(db)
    avg_dwell = 0.0
    if dwell_data:
        avg_dwell = round(sum(d["avg_dwell_seconds"] for d in dwell_data) / len(dwell_data), 1)

    # Peak hour
    hourly = crud.get_hourly_footfall(db)
    peak_hour = max(hourly, key=lambda x: x["visitors"])["hour"] if hourly else None

    # Staff count
    staff_count = db.execute(
        sa.text("SELECT COUNT(DISTINCT person_id) FROM events WHERE is_staff = TRUE")
    ).scalar() or 0

    revenue_per_visitor = round(sales["total_revenue"] / footfall, 2) if footfall > 0 else 0.0

    return MetricsResponse(
        total_footfall      = footfall,
        total_buyers        = buyers,
        conversion_rate_pct = conversion_rate,
        avg_dwell_time_sec  = avg_dwell,
        peak_hour           = peak_hour,
        revenue_per_visitor = revenue_per_visitor,
        total_revenue       = sales["total_revenue"],
        total_orders        = sales["total_orders"],
        avg_order_value     = sales["avg_order_value"],
        staff_count         = int(staff_count),
    )
