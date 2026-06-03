# DESIGN.md — Purplle Store Intelligence System

## 1. Problem Statement

Build an end-to-end AI-powered Store Intelligence System from raw CCTV footage that produces meaningful business metrics — conversion rate, zone dwell time, funnel drop-off, and anomaly detection — for a Purplle physical retail store (Brigade Road, Bangalore).

---

## 2. System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     INPUT LAYER                                  │
│   CAM 1 (Skincare)  CAM 2 (Makeup)  CAM 3 (Entrance/Exit)       │
│   CAM 4 (Haircare)  CAM 5 (Checkout)                             │
│                MP4 Files / Live RTSP Streams                     │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                  DETECTION & TRACKING PIPELINE                   │
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌───────────────────┐  │
│  │  YOLOv8n     │───▶│  ByteTrack   │───▶│  Zone Mapper      │  │
│  │  Person Det. │    │  Multi-track │    │  bbox→zone name   │  │
│  └──────────────┘    └──────────────┘    └───────────────────┘  │
│                                                  │               │
│  ┌──────────────┐    ┌──────────────┐            │               │
│  │  Staff Filter│    │ Reentry Guard│◀───────────┘               │
│  │  (temporal)  │    │  (spatial)   │                            │
│  └──────────────┘    └──────────────┘                            │
│                                                                  │
│  OUTPUT: Structured Events → PostgreSQL                          │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      DATA STORE                                  │
│                                                                  │
│   PostgreSQL (events table + sales_data table)                   │
│   - events: person_entered, zone_enter, zone_exit, person_exited │
│   - sales_data: Brigade Road CSV (22 orders, 101 line items)     │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      REST API (FastAPI)                          │
│                                                                  │
│   GET  /metrics           → footfall, conversion rate, revenue   │
│   GET  /funnel            → 4-stage conversion funnel            │
│   GET  /zones             → per-zone dwell time + footfall       │
│   GET  /anomalies         → crowd surge, empty zone, dwell       │
│   GET  /events            → raw event stream with filters        │
│   GET  /hourly            → per-hour visitor counts              │
│   GET  /sales             → department + salesperson breakdown   │
│   GET  /cameras           → per-camera analytics                 │
│   GET  /insights          → 6 actionable business insights       │
│   GET  /stream            → Server-Sent Events (real-time)       │
│   GET  /health            → system status                        │
│   GET  /metrics/prometheus → Prometheus-format metrics           │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│               DASHBOARD (Next.js 14 + Recharts)                  │
│                                                                  │
│   - Live KPI cards (footfall, conversion, revenue, dwell)        │
│   - Conversion funnel (visual progress bars)                     │
│   - Zone visitor bar chart (Recharts)                            │
│   - Hourly footfall area chart (Recharts) with peak marker       │
│   - Zone dwell time progress bars                                │
│   - Anomaly alert feed with severity badges                      │
│   - Salesperson leaderboard with avatars                         │
│   - Department revenue breakdown with progress bars              │
│   - Brand revenue horizontal bar chart (Recharts)                │
│   - Auto-refresh every 30 seconds                                │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Component Details

### 3.1 Detection Pipeline

**Model:** YOLOv8n (nano) — chosen for speed on CPU/GPU with acceptable accuracy.

**Tracker:** ByteTrack via Ultralytics' built-in `model.track()`.

**Camera-Zone Mapping:** Based on direct visual inspection of extracted CCTV frames:

| Camera | Zone | Evidence |
|--------|------|---------|
| CAM 3  | Entrance/Exit | Glass doors, black marble floor visible |
| CAM 2  | Makeup Zone | Faces Canada, Maybelline, Swiss Beauty signage |
| CAM 1  | Skincare Zone | The Face Shop, COSRX, Minimalist, billing counter |
| CAM 4  | Haircare Zone | Alps Goodness branding visible |
| CAM 5  | Checkout Zone | Based on store layout + foot-traffic convergence |

**Entry/Exit Detection:** CAM 3 has a horizontal "entry line" at y=75% of frame height. Persons crossing this line upward = entered; downward = exited.

**Staff Exclusion:** Temporal heuristic — persons present continuously for >10 minutes are classified as staff. This is robust without needing uniform training data.

**Re-entry Handling:** Persons exiting are recorded with their last position. If a new track appears at the same door position within 2 minutes, it's marked as a re-entry, not a new visitor.

**Frame Skipping:** Every 3rd frame is processed (skip=3) to balance throughput vs. latency. At 25fps this means ~8 processed frames/sec per camera — sufficient for slow-moving retail shoppers.

**Parallelism:** Up to 2 camera threads run simultaneously, controlled by a `threading.Semaphore`. This prevents OOM on CPU-only environments while still achieving parallelism.

### 3.2 Event Schema

```json
{
    "event_id":       "uuid-v4",
    "event_type":     "person_entered | zone_enter | zone_exit | person_exited | staff_detected",
    "person_id":      "CAM3_T0042",
    "timestamp":      "2026-04-10T16:55:36.123Z",
    "camera_id":      "CAM 3",
    "zone":           "entrance",
    "dwell_seconds":  null,
    "is_staff":       false,
    "purchased":      null,
    "confidence":     0.92,
    "bbox":           [x1, y1, x2, y2]
}
```

### 3.3 API Business Logic

**Conversion Rate:**
```
conversion_rate = (unique_buyers / total_footfall) × 100
```
- `total_footfall` = unique `person_entered` events (excluding staff, re-entries)
- `unique_buyers` = unique order_ids from CSV (22 orders on 10 April 2026)

**Funnel:**
1. Entered (crossed entry line)
2. Browsed (visited ≥1 zone)
3. Engaged (dwelled >60s in a zone)
4. Purchased (matched to sales CSV)

**Anomaly Detection:**
- Crowd Surge: ≥5 entries in any 1-minute window
- Unusual Dwell: >30 minutes in a single zone
- Empty Store: No zone activity for >15 minutes

### 3.4 Sales Data Integration

The `Brigade_Bangalore_10_April_26.csv` (22 unique orders, 101 line items) is loaded into PostgreSQL at startup and used to:
- Provide the "purchased" count for conversion calculation
- Power revenue metrics (total NMV ≈ ₹14,823)
- Enable department-level and salesperson-level attribution

### 3.5 Real-Time Streaming (SSE)

`GET /stream` provides a Server-Sent Events endpoint. The API polls the `events` table every 2 seconds for rows newer than the last-seen ID and pushes them to connected clients as typed events (`person-entered`, `zone-enter`, `zone-exit`, `person-exited`). Keepalive comments prevent connection drops through proxies.

This enables:
- Live browser EventSource connections
- Real-time alerting integration (e.g., PagerDuty webhook)
- Future WebSocket upgrade path

### 3.6 Per-Camera Analytics

`GET /cameras` returns event counts, unique persons, and dwell statistics broken down per camera feed. This is essential for:
- Detecting camera outages (zero events)
- Diagnosing zone miscalibration
- Identifying high-traffic cameras needing model confidence tuning

### 3.7 Observability

`GET /metrics/prometheus` exposes four Prometheus-format gauges:
- `purplle_events_total` — total detection events (counter)
- `purplle_footfall_total` — unique customers today
- `purplle_buyers_total` — unique purchases today
- `purplle_conversion_rate_pct` — conversion rate

These can be scraped by a Prometheus server and visualised in Grafana for production monitoring without any additional instrumentation library.

### 3.8 Database Schema & Indexes

**`events` table** (written by detection, read by API):

| Column | Type | Purpose |
|--------|------|---------|
| `id` | SERIAL PK | Auto-increment row ID |
| `event_id` | TEXT UNIQUE | UUID per event (idempotent writes) |
| `event_type` | TEXT | person_entered / zone_enter / zone_exit / person_exited |
| `person_id` | TEXT | Camera-specific track identifier |
| `timestamp` | TIMESTAMP | Frame timestamp when event occurred |
| `camera_id` | TEXT | Source camera (CAM 1 – CAM 5) |
| `zone` | TEXT | Store zone name |
| `dwell_seconds` | REAL | For zone_exit events |
| `is_staff` | BOOLEAN | True if track classified as staff |
| `purchased` | BOOLEAN | True if matched to sales CSV |
| `confidence` | REAL | YOLO detection confidence |
| `bbox` | TEXT | JSON [x1, y1, x2, y2] in pixels |
| `created_at` | TIMESTAMP | DB write time |

**Indexes (6):**

| Index | Column | Powers query |
|-------|--------|-------------|
| `idx_events_type` | `event_type` | Footfall (person_entered count) |
| `idx_events_zone` | `zone` | Zone dwell + funnel queries |
| `idx_events_staff` | `is_staff` | Staff exclusion filter |
| `idx_events_ts` | `timestamp` | Hourly bucketing, time-range queries |
| `idx_events_person_id` | `person_id` | Conversion + unique visitor queries |
| `idx_events_created` | `created_at` | SSE cursor (`WHERE created_at > :last_ts`) |

**`sales_data` table** (seeded from Brigade Road CSV at startup):

Stores denormalised CSV rows: `order_id`, `salesperson_name`, `department`, `brand`, `product_name`, `qty`, `price`, `nmv`, `date`.

---

## 4. Deployment

All services run via a single `docker compose up` command:

| Service | Port | Technology |
|---------|------|-----------|
| PostgreSQL | 5432 | postgres:15-alpine |
| Detection | — | Python + YOLOv8 |
| API | 8000 | FastAPI + uvicorn |
| Dashboard | 3000 | Next.js 14 |

**Cloud (optional):**
| Component | Platform | File |
|-----------|----------|------|
| API + DB | Render | `render.yaml` |
| Dashboard | Vercel | `frontend/vercel.json` |

**Minimum requirements:** Docker, Docker Compose, CCTV footage mounted at `CCTV_DATA_PATH`.

---

## 5. Known Limitations & Assumptions

1. **Person Re-ID across cameras** uses positional heuristics (not deep appearance features). Cross-camera deduplication is approximate.
2. **Purchase attribution** cannot directly link a CCTV track_id to a CSV order_id (no PII bridge). We use aggregate counts.
3. **Staff uniform detection** is temporal-only. A customer who stays very long (unlikely) could be mis-classified.
4. **Video timestamp** is estimated from file creation time + frame offset. Actual store hours assumed 12:00–22:00.
5. **SSE polling** adds 2-second latency. For <2s latency, a WebSocket approach with DB LISTEN/NOTIFY would be preferred but adds operational complexity not warranted here.
