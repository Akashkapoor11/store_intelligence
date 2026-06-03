"""
routes/stream.py — GET /stream  (Server-Sent Events)
──────────────────────────────────────────────────────
Real-time event stream from the detection pipeline.
Clients connect via EventSource and receive new events as they are written.

Usage:
  curl -N http://localhost:8000/stream
  new EventSource("http://localhost:8000/stream")
"""

import json
import asyncio
import sqlalchemy as sa
from datetime import datetime
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from db.database import engine

router = APIRouter()

_POLL_INTERVAL_SEC = 2   # check DB every 2 seconds for new events


async def _event_generator():
    """
    Yields Server-Sent Events containing new detection events.
    Uses created_at timestamp cursor — works regardless of which service
    created the events table first (API or detection pipeline).
    """
    last_seen_ts = None

    # Seed cursor to the current latest event's created_at
    try:
        with engine.connect() as conn:
            row = conn.execute(sa.text(
                "SELECT MAX(created_at) FROM events"
            )).scalar()
            last_seen_ts = row  # May be None if table is empty
    except Exception:
        pass

    # Opening handshake
    yield (
        "event: connected\n"
        f"data: {json.dumps({'message': 'Purplle Store Intelligence stream connected', 'ts': datetime.utcnow().isoformat()})}\n\n"
    )

    while True:
        await asyncio.sleep(_POLL_INTERVAL_SEC)

        try:
            with engine.connect() as conn:
                if last_seen_ts is None:
                    rows = conn.execute(sa.text("""
                        SELECT event_id, event_type, person_id,
                               timestamp, camera_id, zone,
                               dwell_seconds, is_staff, confidence,
                               created_at
                        FROM events
                        WHERE is_staff = FALSE
                        ORDER BY created_at ASC
                        LIMIT 20
                    """)).fetchall()
                else:
                    rows = conn.execute(sa.text("""
                        SELECT event_id, event_type, person_id,
                               timestamp, camera_id, zone,
                               dwell_seconds, is_staff, confidence,
                               created_at
                        FROM events
                        WHERE created_at > :last_ts
                          AND is_staff = FALSE
                        ORDER BY created_at ASC
                        LIMIT 20
                    """), {"last_ts": last_seen_ts}).fetchall()

            for row in rows:
                payload = {
                    "event_id":      row.event_id,
                    "event_type":    row.event_type,
                    "person_id":     row.person_id,
                    "timestamp":     row.timestamp.isoformat() if row.timestamp else None,
                    "camera_id":     row.camera_id,
                    "zone":          row.zone,
                    "dwell_seconds": row.dwell_seconds,
                    "confidence":    row.confidence,
                }
                event_type = row.event_type.replace("_", "-")
                yield f"event: {event_type}\ndata: {json.dumps(payload)}\n\n"
                last_seen_ts = row.created_at

        except Exception as e:
            yield f": error polling DB: {e}\n\n"

        # Keepalive ping
        yield f": ping {datetime.utcnow().isoformat()}\n\n"


@router.get("/stream", summary="Real-time event stream (SSE)")
async def stream_events():
    """
    Server-Sent Events endpoint for real-time detection events.

    Connect via EventSource in the browser or `curl -N /stream`.
    Emits events: **person-entered**, **zone-enter**, **zone-exit**, **person-exited**.
    Polls the database every 2 seconds for new events from the detection pipeline.
    """
    return StreamingResponse(
        _event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control":     "no-cache",
            "X-Accel-Buffering": "no",     # disable nginx buffering
            "Connection":        "keep-alive",
        },
    )
