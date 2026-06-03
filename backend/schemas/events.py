"""
schemas/events.py  —  Pydantic schemas for events and API responses
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime


class EventOut(BaseModel):
    event_id:       str
    event_type:     str
    person_id:      str
    timestamp:      datetime
    camera_id:      Optional[str] = None
    zone:           Optional[str] = None
    dwell_seconds:  Optional[float] = None
    is_staff:       bool
    purchased:      Optional[bool] = None
    confidence:     Optional[float] = None
    bbox:           Optional[str]  = Field(default=None, description="JSON serialized [x1, y1, x2, y2] in pixels")

    model_config = {"from_attributes": True, "extra": "ignore"}


class MetricsResponse(BaseModel):
    total_footfall:       int   = Field(description="Unique customers who entered store")
    total_buyers:         int   = Field(description="Customers who made a purchase")
    conversion_rate_pct:  float = Field(description="Buyers / Footfall × 100")
    avg_dwell_time_sec:   float = Field(description="Average time in store per customer")
    peak_hour:            Optional[int] = Field(description="Hour with most footfall (0-23)")
    revenue_per_visitor:  float = Field(description="Total revenue / footfall")
    total_revenue:        float
    total_orders:         int
    avg_order_value:      float
    staff_count:          int
    timestamp:            datetime = Field(default_factory=datetime.utcnow)


class FunnelStage(BaseModel):
    stage:       str
    count:       int
    percentage:  float
    drop_off:    float


class FunnelResponse(BaseModel):
    stages:       List[FunnelStage]
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class ZoneMetrics(BaseModel):
    zone:              str
    unique_visitors:   int
    avg_dwell_seconds: float
    max_dwell_seconds: float
    share_of_footfall: float


class ZonesResponse(BaseModel):
    zones:        List[ZoneMetrics]
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class Anomaly(BaseModel):
    type:        str
    severity:    str   # high | medium | low
    description: str
    timestamp:   Optional[str] = None
    details:     Optional[Any] = None


class AnomaliesResponse(BaseModel):
    anomalies:    List[Anomaly]
    total:        int
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class HealthResponse(BaseModel):
    status:       str
    db_connected: bool
    event_count:  int
    version:      str = "1.0.0"
    generated_at: datetime = Field(default_factory=datetime.utcnow)


# ── New schemas ───────────────────────────────────────────────────────────────

class HourlyBucket(BaseModel):
    hour:     int   = Field(description="Hour of day (0-23)")
    visitors: int   = Field(description="Unique visitors in that hour")


class HourlyResponse(BaseModel):
    hours:        List[HourlyBucket]
    peak_hour:    Optional[int] = None
    source:       str = Field(description="'live' if from DB, 'demo' if fallback")
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class DepartmentSales(BaseModel):
    department: str
    orders:     int
    revenue:    float
    share_pct:  float


class SalespersonMetrics(BaseModel):
    name:    str
    orders:  int
    revenue: float


class BrandMetrics(BaseModel):
    brand:   str
    orders:  int
    revenue: float


class SalesBreakdownResponse(BaseModel):
    by_department:  List[DepartmentSales]
    by_salesperson: List[SalespersonMetrics]
    top_brands:     List[BrandMetrics]
    total_orders:   int
    total_revenue:  float
    generated_at:   datetime = Field(default_factory=datetime.utcnow)


# ── Events endpoint response (structured, not raw list) ───────────────────────

class EventsResponse(BaseModel):
    events:       List[EventOut]
    total:        int   = Field(description="Total events matching filter")
    generated_at: datetime = Field(default_factory=datetime.utcnow)
