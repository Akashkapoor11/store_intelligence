"""
event_emitter.py
────────────────
Generates structured events from tracking data and writes them to the database.

Official Purplle event types (from sample_events JSONL):
  entry            → customer crossed entry line into store
  exit             → customer left the store
  zone_entered     → customer entered a specific zone
  zone_exited      → customer left a zone (with dwell_seconds)
  queue_completed  → customer completed billing queue
  queue_abandoned  → customer abandoned billing queue
  staff_detected   → track identified as staff
"""

import uuid
import json
import time
from datetime import datetime
from typing import Optional, Dict, Any
from loguru import logger
import sqlalchemy as sa
from db import get_engine


class EventEmitter:

    def __init__(self):
        self.engine = get_engine()
        self._ensure_table()

    def _ensure_table(self):
        with self.engine.connect() as conn:
            conn.execute(sa.text("""
                CREATE TABLE IF NOT EXISTS events (
                    id              SERIAL PRIMARY KEY,
                    event_id        TEXT UNIQUE,
                    event_type      TEXT NOT NULL,
                    person_id       TEXT NOT NULL,
                    timestamp       TIMESTAMP NOT NULL,
                    camera_id       TEXT,
                    zone            TEXT,
                    dwell_seconds   REAL,
                    is_staff        BOOLEAN DEFAULT FALSE,
                    purchased       BOOLEAN DEFAULT FALSE,
                    confidence      REAL,
                    bbox            TEXT,
                    -- Official Purplle schema fields
                    gender_pred     TEXT,
                    age_pred        INTEGER,
                    age_bucket      TEXT,
                    id_token        TEXT,
                    zone_id         TEXT,
                    zone_type       TEXT,
                    wait_seconds    INTEGER,
                    queue_abandoned BOOLEAN,
                    store_id        TEXT,
                    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.execute(sa.text("""
                CREATE INDEX IF NOT EXISTS idx_events_type       ON events(event_type);
                CREATE INDEX IF NOT EXISTS idx_events_zone       ON events(zone);
                CREATE INDEX IF NOT EXISTS idx_events_staff      ON events(is_staff);
                CREATE INDEX IF NOT EXISTS idx_events_ts         ON events(timestamp);
                CREATE INDEX IF NOT EXISTS idx_events_person_id  ON events(person_id);
                CREATE INDEX IF NOT EXISTS idx_events_created    ON events(created_at);
                CREATE INDEX IF NOT EXISTS idx_events_store_id   ON events(store_id);
                CREATE INDEX IF NOT EXISTS idx_events_gender     ON events(gender_pred);
                CREATE INDEX IF NOT EXISTS idx_events_age_bucket ON events(age_bucket);
            """))
            conn.commit()


    def emit(
        self,
        event_type: str,
        person_id: str,
        timestamp: datetime,
        camera_id: Optional[str] = None,
        zone: Optional[str] = None,
        dwell_seconds: Optional[float] = None,
        is_staff: bool = False,
        purchased: Optional[bool] = None,
        confidence: Optional[float] = None,
        bbox: Optional[list] = None,
        # Official schema fields
        gender_pred: Optional[str] = None,
        age_pred: Optional[int] = None,
        age_bucket: Optional[str] = None,
        id_token: Optional[str] = None,
        zone_id: Optional[str] = None,
        zone_type: Optional[str] = None,
        wait_seconds: Optional[int] = None,
        queue_abandoned: Optional[bool] = None,
        store_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        event = {
            "event_id":       str(uuid.uuid4()),
            "event_type":     event_type,
            "person_id":      person_id,
            "timestamp":      timestamp,
            "camera_id":      camera_id,
            "zone":           zone,
            "dwell_seconds":  dwell_seconds,
            "is_staff":       is_staff,
            "purchased":      purchased,
            "confidence":     confidence,
            "bbox":           json.dumps(bbox) if bbox else None,
            "gender_pred":    gender_pred,
            "age_pred":       age_pred,
            "age_bucket":     age_bucket,
            "id_token":       id_token or person_id,
            "zone_id":        zone_id,
            "zone_type":      zone_type,
            "wait_seconds":   wait_seconds,
            "queue_abandoned": queue_abandoned,
            "store_id":       store_id,
        }

        retries = 3
        for attempt in range(retries):
            try:
                with self.engine.connect() as conn:
                    conn.execute(sa.text("""
                        INSERT INTO events (
                            event_id, event_type, person_id, timestamp,
                            camera_id, zone, dwell_seconds, is_staff,
                            purchased, confidence, bbox,
                            gender_pred, age_pred, age_bucket, id_token,
                            zone_id, zone_type, wait_seconds, queue_abandoned, store_id
                        ) VALUES (
                            :event_id, :event_type, :person_id, :timestamp,
                            :camera_id, :zone, :dwell_seconds, :is_staff,
                            :purchased, :confidence, :bbox,
                            :gender_pred, :age_pred, :age_bucket, :id_token,
                            :zone_id, :zone_type, :wait_seconds, :queue_abandoned, :store_id
                        )
                        ON CONFLICT (event_id) DO NOTHING
                    """), event)
                    conn.commit()
                break
            except Exception as e:
                logger.error(f"[EventEmitter] Failed to write event (attempt {attempt+1}/{retries}): {e}")
                if attempt < retries - 1:
                    time.sleep(0.5 * (attempt + 1))
                else:
                    logger.critical(f"[EventEmitter] Dropping event after {retries} failed attempts")

        logger.debug(
            f"EVENT [{event_type}] person={person_id} zone={zone} "
            f"cam={camera_id} gender={gender_pred} age={age_pred} t={timestamp.isoformat()}"
        )
        return event
