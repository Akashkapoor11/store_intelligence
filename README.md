# Purplle Store Intelligence System

> **UpGrad Placements · April 2026 — Round 2 Submission**

An end-to-end AI-powered store intelligence system built from raw CCTV footage. Detects and tracks customers, maps them to store zones, computes business metrics, and surfaces insights via REST API and live dashboard.

---

##  Quick Start

```bash
# 1. Clone the repo
git clone <your-repo-url>
cd store_intelligence

# 2. Create local configuration files
cp .env.example .env
cp backend/.env.example backend/.env
cp detection/.env.example detection/.env
cp frontend/.env.example frontend/.env

# 3a. Run immediately — no CCTV footage needed
#     Starts DB + API + Dashboard. API auto-seeds 85 demo customers on first boot.
docker compose up --build

# 3b. Run WITH CCTV detection (optional, after placing footage):
#     CCTV_DATA_PATH=/absolute/path/to/footage docker compose --profile detection up --build

# 4. Access the services
#    Dashboard: http://localhost:3000
#    API:       http://localhost:8000/docs
#    Health:    http://localhost:8000/health
#    Stream:    http://localhost:8000/stream  (SSE)
#    Prometheus: http://localhost:8000/metrics/prometheus
```

---

##  Project Structure

```
store_intelligence/
├── docker-compose.yml      ← One command deployment
├── DESIGN.md               ← System architecture
├── CHOICES.md              ← Engineering decisions
├── detection/              ← AI pipeline (YOLOv8 + ByteTrack)
├── backend/                ← FastAPI REST API (12 endpoints)
├── frontend/               ← Next.js 14 production dashboard
└── tests/                  ← pytest test suite (40+ tests)
```

---

##  API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /metrics` | Footfall, conversion rate, revenue, dwell time |
| `GET /funnel` | 4-stage conversion funnel with drop-off |
| `GET /zones` | Per-zone analytics and dwell time |
| `GET /anomalies` | Crowd surge, unusual dwell, empty store |
| `GET /events` | Raw event stream with filters |
| `GET /hourly` | Per-hour visitor counts |
| `GET /sales` | Revenue by department, salesperson, brand |
| `GET /cameras` | Per-camera analytics and diagnostics |
| `GET /insights` | Actionable business recommendations from data |
| `GET /stream` | Real-time SSE event stream |
| `GET /health` | System health check with uptime + pipeline lag |
| `GET /metrics/prometheus` | Prometheus-format observability metrics |
| `GET /docs` | Interactive Swagger API documentation |

---

##  Architecture

**Detection:** YOLOv8n → ByteTrack → Zone Mapper → Staff Filter → Re-entry Guard → Event Emitter  
**Storage:** PostgreSQL 15 (events + sales_data tables, indexed)  
**API:** FastAPI + Pydantic + uvicorn (async, **12 endpoints**)  
**Insights:** `/insights` endpoint — 6 actionable store manager recommendations  
**Real-time:** Server-Sent Events `/stream` (poll interval 2s)  
**Tracing:** `X-Request-ID` + `X-Response-Time` headers on every response  
**Dashboard:** Next.js 14 + Recharts (auto-refresh 30s)  
**Observability:** `/metrics/prometheus` + `/health` with uptime + pipeline lag  
**Deploy:** Docker Compose (local) · Render + Vercel (cloud)  

See [DESIGN.md](DESIGN.md) for full architecture and [CHOICES.md](CHOICES.md) for engineering decisions.

---

##  Store Data

- **Store:** Brigade Road, Bangalore (ST1008)
- **Date:** 10 April 2026
- **Cameras:** 5 (Entrance/CAM3, Makeup/CAM2, Skincare/CAM1, Haircare/CAM4, Checkout/CAM5)
- **Sales:** 22 orders, 101 items, ₹14,823 NMV
- **Salespersons:** 5 (Zufishan, Kasthuri, Shashikala, Naziya, Priya)
- **Top Salesperson:** Shashikala (₹3,671 / 6 orders)

---

##  Running Tests

```bash
# Start the system first
docker compose up -d

# Run all tests (40+ tests across 12 test classes)
pip install pytest requests
pytest tests/ -v

# Tests cover:
#   - Health endpoint (db, uptime, pipeline lag)
#   - Metrics correctness (conversion rate range, footfall)
#   - Funnel monotonicity and percentages
#   - Zone analytics
#   - Anomaly detection
#   - Event schema validation (including bbox field)
#   - Camera analytics (5 feeds)
#   - SSE stream headers
#   - Prometheus text format
#   - Business insights (6 tests: non-empty, fields, priorities, categories)
#   - Tracing headers (X-Request-ID, X-Response-Time)
#   - Root endpoint (endpoints list)
#   - Business logic unit tests (conversion, funnel, zones, staff, re-entry)
```

---

##  Key Metrics (10 April 2026)

| Metric | Value |
|--------|-------|
| Total Footfall | Computed from CCTV |
| Conversion Rate | ~18-22% (estimated) |
| Total Revenue (NMV) | ₹14,823 |
| Avg Order Value | ₹673 |
| Peak Hours | 18:00–20:00 |
| Top Zone | Makeup (Faces Canada, Maybelline) |
| Top Salesperson | Shashikala (₹3,671) |
| Top Brand | Faces Canada |

---

## ⚙️ Environment Variables

This project uses dedicated env files for each service:

- `backend/.env` - backend service configuration
- `detection/.env` - detection pipeline configuration
- `frontend/.env` - frontend dashboard configuration

Use the example files to bootstrap each service:

```bash
cp backend/.env.example backend/.env
cp detection/.env.example detection/.env
cp frontend/.env.example frontend/.env
```

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql://purplle:purplle_secret@db:5432/store_intel` | Postgres connection string |
| `SALES_CSV_PATH` | `../Brigade_Bangalore_10_April_26.csv` | Sales CSV file path for backend |
| `CORS_ORIGINS` | `http://localhost:3000,http://localhost:8000` | Allowed origins for backend |
| `PORT` | `8000` | Backend service port |
| `CCTV_PATH` | `/data/cctv` | Mounted CCTV folder inside detection container |
| `MODEL_NAME` | `yolov8n.pt` | YOLO model to use |
| `PROCESS_MODE` | `file` | `file` or `stream` |
| `LOG_LEVEL` | `INFO` | Application log level |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Backend URL for frontend builds |
| `API_INTERNAL_URL` | `http://api:8000` | Internal API host used in Docker Compose |

---

##  Notes

- CCTV video files are NOT included in the repository (per challenge rules)
- Challenge resource folders like `_extracted/` are ignored by `.gitignore` and not part of the submission.
- Sales CSV is embedded as fallback data — system works without the CSV file.
- The system degrades gracefully if detection hasn't run yet (API returns sensible defaults, not crashes).
- All 12 API endpoints return valid JSON immediately after `docker compose up`
- Set `CCTV_DATA_PATH` in `.env` to the absolute path of your CCTV footage folder before running detection.

##  Deployment Checklist

Follow these steps to deploy the production stack:

1. **Push this repository to GitHub** (without CCTV files per challenge rules).

2. **Render (backend):**
   - Create a new Web Service (Docker) from this repo.
   - Render uses `render.yaml` to provision the API + PostgreSQL automatically.
   - Verify `/health` returns `db_connected: true`.

3. **Vercel (frontend):**
   - Import `frontend/` as the project root.
   - Set `NEXT_PUBLIC_API_URL` to the Render backend URL (e.g., `https://purplle-api.onrender.com`).
   - Deploy and verify the dashboard loads all KPI cards.

4. **Post-deploy checks:**
   - `GET /health` → `db_connected: true`
   - `GET /metrics` → conversion_rate_pct between 0-100
   - `GET /metrics/prometheus` → Prometheus text format
   - `GET /stream` → SSE connection with `event: connected` header
   - `pytest tests/ -v` → all tests pass
