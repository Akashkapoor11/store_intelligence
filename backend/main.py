"""
main.py  —  FastAPI Application
────────────────────────────────
Purplle Store Intelligence REST API
All endpoints required for the acceptance gate and scoring.
"""

import os
import time
import uuid
import sqlalchemy as sa
from contextlib import asynccontextmanager
from datetime import datetime
from loguru import logger

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from db.database import engine, SessionLocal
from routes import metrics, funnel, zones, anomalies, events, hourly, sales, stream, cameras, insights
from services.seed import seed_sales_data, seed_demo_events


# ── DB Init ───────────────────────────────────────────────────────────────────

def init_db():
    """Create all required tables if they don't exist yet."""
    with engine.connect() as conn:
        # events table — written by detection pipeline, read by API
        # Schema matches official Purplle sample_events JSONL exactly
        conn.execute(sa.text("""
            CREATE TABLE IF NOT EXISTS events (
                id             SERIAL PRIMARY KEY,
                event_id       TEXT UNIQUE,
                event_type     TEXT NOT NULL,
                person_id      TEXT NOT NULL,
                timestamp      TIMESTAMP NOT NULL,
                camera_id      TEXT,
                zone           TEXT,
                dwell_seconds  REAL,
                is_staff       BOOLEAN DEFAULT FALSE,
                purchased      BOOLEAN DEFAULT FALSE,
                confidence     REAL,
                bbox           TEXT,
                -- Official schema fields from sample_events
                gender_pred    TEXT,
                age_pred       INTEGER,
                age_bucket     TEXT,
                id_token       TEXT,
                zone_id        TEXT,
                zone_type      TEXT,
                wait_seconds   INTEGER,
                queue_abandoned BOOLEAN,
                store_id       TEXT,
                created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.execute(sa.text("""
            CREATE INDEX IF NOT EXISTS idx_events_type      ON events(event_type);
            CREATE INDEX IF NOT EXISTS idx_events_zone      ON events(zone);
            CREATE INDEX IF NOT EXISTS idx_events_staff     ON events(is_staff);
            CREATE INDEX IF NOT EXISTS idx_events_ts        ON events(timestamp);
            CREATE INDEX IF NOT EXISTS idx_events_person_id ON events(person_id);
            CREATE INDEX IF NOT EXISTS idx_events_created   ON events(created_at);
            CREATE INDEX IF NOT EXISTS idx_events_store_id  ON events(store_id);
            CREATE INDEX IF NOT EXISTS idx_events_gender    ON events(gender_pred);
            CREATE INDEX IF NOT EXISTS idx_events_age_bucket ON events(age_bucket);
        """))
        conn.commit()
    logger.info("✅ events table ready (9 indexes, official schema)")


# ── Startup / Shutdown ────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Starting Purplle Store Intelligence API...")

    # Wait for DB to be ready
    for attempt in range(30):
        try:
            with engine.connect() as conn:
                conn.execute(sa.text("SELECT 1"))
            logger.info("✅ Database connected")
            break
        except Exception as e:
            logger.warning(f"DB not ready ({attempt+1}/30): {e}")
            time.sleep(2)

    # Ensure tables exist
    try:
        init_db()
    except Exception as e:
        logger.warning(f"init_db warning (non-fatal): {e}")

    # Seed sales CSV data
    try:
        seed_sales_data()
        logger.info("✅ Sales data seeded")
    except Exception as e:
        logger.warning(f"Sales seed failed (non-fatal): {e}")

    # Seed demo CCTV events disabled to ensure 100% pure live data from CCTV
    # User is going to push real data from local pipeline!
    pass

    yield
    logger.info("Shutting down...")


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Purplle Store Intelligence API",
    description=(
        "AI-powered store analytics from CCTV footage. "
        "Provides real-time footfall, conversion, zone dwell time, and anomaly detection."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS — allow Vercel frontend + local dev
_cors_origins = os.getenv("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request Logging + Tracing ─────────────────────────────────────────────────

_start_time = time.time()  # track uptime


@app.middleware("http")
async def log_requests(request: Request, call_next):
    # Generate unique request ID for distributed tracing
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    start = time.time()
    response = await call_next(request)
    duration = (time.time() - start) * 1000
    # Attach trace ID to response for client-side correlation
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Response-Time"] = f"{duration:.1f}ms"
    logger.info(
        f"{request.method} {request.url.path} → {response.status_code} "
        f"({duration:.1f}ms) rid={request_id[:8]}"
    )
    return response


# ── Routes ────────────────────────────────────────────────────────────────────

app.include_router(metrics.router,    prefix="",       tags=["Core Metrics"])
app.include_router(funnel.router,     prefix="",       tags=["Conversion Funnel"])
app.include_router(zones.router,      prefix="",       tags=["Zone Analytics"])
app.include_router(anomalies.router,  prefix="",       tags=["Anomaly Detection"])
app.include_router(events.router,     prefix="",       tags=["Events"])
app.include_router(hourly.router,     prefix="",       tags=["Hourly Footfall"])
app.include_router(sales.router,      prefix="",       tags=["Sales Analytics"])
app.include_router(stream.router,     prefix="",       tags=["Real-Time Stream"])
app.include_router(cameras.router,    prefix="",       tags=["Camera Analytics"])
app.include_router(insights.router,   prefix="",       tags=["Business Insights"])


# ── Health Check ──────────────────────────────────────────────────────────────

@app.get("/health", tags=["System"], summary="System health and observability")
def health_check():
    """
    Comprehensive health check with observability data:
    - Database connectivity
    - Event table row count and schema check
    - Detection pipeline recency (seconds since last event)
    - System uptime
    - Version
    """
    db_ok        = False
    event_count  = 0
    last_event_s = None   # seconds since last detection event
    tables_ok    = False

    try:
        with engine.connect() as conn:
            conn.execute(sa.text("SELECT 1"))
            db_ok = True

            event_count = conn.execute(
                sa.text("SELECT COUNT(*) FROM events")
            ).scalar() or 0

            tables_ok = True

            last_ts = conn.execute(
                sa.text("SELECT MAX(created_at) FROM events")
            ).scalar()
            if last_ts:
                last_event_s = round((datetime.utcnow() - last_ts).total_seconds(), 1)

    except Exception as e:
        logger.warning(f"Health check DB error: {e}")

    uptime_s = round(time.time() - _start_time, 1)

    return {
        "status":           "healthy" if db_ok else "degraded",
        "db_connected":     db_ok,
        "tables_ready":     tables_ok,
        "event_count":      event_count,
        "pipeline_lag_sec": last_event_s,   # None if no events yet
        "uptime_sec":       uptime_s,
        "version":          "1.0.0",
        "timestamp":        datetime.utcnow().isoformat(),
    }


@app.get("/metrics/prometheus", tags=["Observability"])
def prometheus_metrics():
    """
    Prometheus-compatible metrics endpoint for observability.
    Exposes store KPIs in the standard Prometheus text exposition format.
    Scrape with: curl http://localhost:8000/metrics/prometheus
    """
    from fastapi.responses import PlainTextResponse
    event_count = 0
    footfall    = 0
    buyers      = 0
    try:
        with engine.connect() as conn:
            event_count = conn.execute(sa.text("SELECT COUNT(*) FROM events")).scalar() or 0
            footfall    = conn.execute(sa.text(
                "SELECT COUNT(DISTINCT person_id) FROM events WHERE event_type='person_entered' AND is_staff=FALSE"
            )).scalar() or 0
            buyers      = conn.execute(sa.text(
                "SELECT COUNT(DISTINCT order_id) FROM sales_data"
            )).scalar() or 0
    except Exception:
        pass
    conversion = round(buyers / footfall * 100, 2) if footfall > 0 else 0.0
    lines = [
        "# HELP purplle_events_total Total detection events stored",
        "# TYPE purplle_events_total counter",
        f"purplle_events_total {event_count}",
        "# HELP purplle_footfall_total Unique customer entries today",
        "# TYPE purplle_footfall_total gauge",
        f"purplle_footfall_total {footfall}",
        "# HELP purplle_buyers_total Unique purchases today",
        "# TYPE purplle_buyers_total gauge",
        f"purplle_buyers_total {buyers}",
        "# HELP purplle_conversion_rate_pct Store conversion rate percentage",
        "# TYPE purplle_conversion_rate_pct gauge",
        f"purplle_conversion_rate_pct {conversion}",
    ]
    return PlainTextResponse("\n".join(lines) + "\n")


@app.get("/", tags=["System"])
def root():
    return {
        "service": "Purplle Store Intelligence API",
        "version": "1.0.0",
        "endpoints": [
            "/metrics", "/funnel", "/zones", "/anomalies",
            "/events", "/hourly", "/sales", "/cameras",
            "/insights", "/stream", "/health",
            "/metrics/prometheus", "/docs",
        ],
    }
