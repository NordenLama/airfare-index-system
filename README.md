# Airfare Price Index (APIx) System ✈️

A comprehensive airfare tracking, index calculation, knowledge graph, and forecasting system. The project features web scrapers, a FastAPI backend service, an ML forecasting engine, an SQLite database engine, and a standalone prototype frontend dashboard.

---

## 🚀 Key Features

*   **Real-time Fare Analytics:** Live data collection and tracking across multiple channels.
*   **APIx Calculation:** Compute Airfare Price Index against a base period (Base 2024 = 100).
*   **Machine Learning Forecasting:**
    *   Trains a RandomForestRegressor (fallback to polynomial regression) on historical fares.
    *   Predicts fares at various horizons (T+1 to T+45).
    *   Provides actionable insights for consumers (savings analysis) and market surveillance (surge risk alerts).
*   **Interactive Prototype Dashboard:**
    *   Professional, modern light-mode executive UI.
    *   Interactive moving forecast charts (7-day history + 30-day prediction).
    *   Route-Horizon Heatmap Matrix.

---

## 📁 Repository Structure

```text
airfare-index-system/
├── database/            # Central database schemas and SQLite files (airfare_index.db)
├── prototype/           # Prototyping scripts and standalone UI experiments
│   ├── index.html       # Prototype UI dashboard with responsive layout and charts
│   ├── backend.py       # Core backend index calculation & data processing
│   └── ml_forecaster.py # ML-based forecasting engine (Random Forest)
├── prototype_server.py  # FastAPI backend endpoints & live data scraping connector
├── requirements.txt     # Python backend dependencies
└── scrapers/            # Web scraping modules (if any)
```

---

## 🏛️ Government Data Export & Consumption

The system exposes dedicated REST API endpoints for government regulatory bodies (like DGCA, Ministry of Civil Aviation) to ingest real-time airfare data and anomaly alerts clearly and securely:

*   **Dedicated JSON Endpoint (`/api/export-apix-data?format=json`)**: A highly structured REST endpoint that outputs the National Airfare Index, route-specific anomalies, and surge alerts.
*   **How the Govt consumes it**: Government systems or enterprise dashboards can poll this endpoint via standard HTTP `GET` requests (e.g., using `curl`, Python `requests`, or automated cron jobs) to feed into their own national dashboards or trigger regulatory alerts. 
*   **Security & Validation**: This endpoint ensures that data is served in a standardized, machine-readable format (JSON) that complies with data interoperability standards, keeping raw scraping logic separate from government data ingestion pipelines.

---

## 🛠️ Tech Stack

*   **Backend:** Python, FastAPI, SQLite
*   **Machine Learning:** scikit-learn (Random Forest), NumPy, Pandas
*   **Frontend (Prototype):** HTML, Tailwind CSS, JavaScript, Chart.js, Leaflet

---

## ⚙️ Running the Prototype

1.  **Install dependencies:** 
    ```bash
    pip install -r requirements.txt
    ```

2.  **Start the Main API Server:**
    ```bash
    uvicorn api.main:app --host 0.0.0.0 --port 8001
    ```
    *The server runs on `http://127.0.0.1:8001`. Requires API key for `/api/v1/*` endpoints.*

3.  **Start the Prototype Dashboard Server:**
    ```bash
    python3 prototype_server.py
    ```
    *Runs on `http://localhost:8000` with full features (OTP auth, forecasting, surveillance, etc.).*

4.  **Start the Frontend Dev Server:**
    ```bash
    cd frontend && npm run dev
    ```
    *Runs on `http://localhost:5173` (Vite dev server for Live Share / component development).*

5.  **Open the Dashboard:**
    Navigate to `http://localhost:8000` to access the prototype dashboard.

---

## 🐳 Docker & Alternative Deployment

- `docker-compose.yml` is available for full-stack deployment (API + dashboard).
- See `start.sh` for the unified startup script that starts all servers (API on 8001, Dashboard on 8000, Frontend Vite on 5173).

---

## 📡 API Endpoints

**Main API (port 8001, auth required via API key):**

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Health check (no auth) |
| `/analytics` | GET | Full analytics (index, volatility, rankings) |
| `/analytics/timeseries` | GET | Index time series |
| `/analytics/routes/recommended` | GET | DGCA recommended routes |
| `/analytics/data-quality` | GET | Data quality report |
| `/dashboard/summary` | GET | Dashboard summary |
| `/routes` | GET | Route analysis |
| `/quality` | GET | Quality assessment |
| `/routes/{route}/context` | GET | News context for route |
| `/index/calculate` | POST | Calculate airfare price index |
| `/forecast/national` | POST | National forecast |
| `/forecast/national/evaluate` | POST | Baseline evaluation |
| `/forecast/route` | POST | Route forecast |
| `/forecast/route/evaluate` | POST | Route baseline evaluation |
| `/forecast/routes` | POST | All-routes forecast |
| `/forecast/routes/evaluate` | POST | All-routes evaluation |
| `/forecast/cpi-benchmark` | POST | CPI benchmark comparison |
| `/forecast/booking-horizon` | POST | Booking-horizon analysis |

See `api/forecasting_routes.py` for full forecasting endpoint definitions.

---

## 🗂️ Repository Structure (Expanded)

```text
airfare-index-system/
├── database/                   # SQLite schemas & initialization
├── docs/                     # Methodology & design documents
│   ├── methodology.md        # Core index calculation methodology
│   ├── forecasting_methodology.md  # Forecasting pipeline (Stages 1-3.1)
│   ├── data_quality.md       # Scraper validation layer
│   ├── sih_pitch.md          # Judge Q&A & differentiation
│   ├── scraper.md            # Scraper module docs
│   ├── data_contract.md      # Data contract specification
│   ├── test_cases.md         # Test case definitions
│   └── methodology/          # Sub-methodology docs
├── api/                      # FastAPI backend
│   ├── main.py               # App entrypoint with routing
│   ├── routes/               # Route definitions (index, forecast, quality, etc.)
│   ├── services/             # Business logic services
│   ├── dependencies.py       # API key verification
│   ├── schemas.py            # Pydantic request/response schemas
│   └── forecasting_routes.py # Forecasting API endpoints
├── prototype/                # Standalone prototype scripts
│   ├── backend.py            # Core index calculation
│   ├── ml_forecaster.py      # ML forecasting engine
│   ├── kg_app.py             # Knowledge graph prototype
│   ├── sample_fares.csv      # Sample data
│   └── index.html            # Prototype UI dashboard
├── prototype_server.py       # Standalone FastAPI server (MoSPI/RBI APIx)
├── start.sh                  # Unified startup script (API 8001 + Dashboard 8000 + Vite 5173)
├── requirements.txt          # Python dependencies
├── frontend/                 # React + Vite frontend dashboard
│   ├── src/                  # React source code
│   ├── package.json          # Frontend dependencies
│   ├── vite.config.ts        # Vite config (fixed: uses import.meta.dirname)
│   ├── tailwind.config.js    # Tailwind CSS config
│   ├── postcss.config.js     # PostCSS config
│   ├── index.html            # HTML entry point
│   ├── tsconfig.json         # TypeScript config
│   ├── tsconfig.node.json    # Node.js TypeScript config
│   └── dist/                 # Production build output
├── data/                     # Data assets
│   ├── routes/               # Recommended routes & priority CSV
│   ├── benchmarks/           # MoSPI CPI benchmark data (cpi_1337.xlsx)
│   └── traffic/              # DGCA passenger-traffic weights
├── prototype_server.log      # Prototype server logs
├── api_server.log            # Main API server logs
└── requirements.txt          # Root-level Python dependencies
```

---

## 🧭 Key Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Python, FastAPI, SQLite, SQLAlchemy |
| **ML / Data Science** | scikit-learn, NumPy, Pandas, statsmodels |
| **Frontend** | React 18, Vite, Tailwind CSS, Recharts |
| **Data Validation** | Custom data_quality layer (schema + field validation) |
| **Index Calculation** | Laspeyres price index, median representative fares, DGCA traffic weights |
| **Forecasting** | Baseline models (naive, historical mean, moving average), rolling-origin backtesting |
| **CPI Comparison** | Structural comparison against MoSPI official CPI Airfare sub-index (series 1337) |
| **Booking Horizon** | T+1 to T+45 partitioning, 5 buckets (T1_7, T8_14, T15_21, T22_30, T31_45) |
| **Deployment** | uvicorn, gunicorn, Docker (docker-compose) |

---

## 📊 Methodology Highlights (Summarized)

- **Airfare Price Index**: Laspeyres-style index with fixed base-period weights from DGCA passenger traffic (not synthetic).
- **Representative Fare**: Median per route/period — resistant to right-skewed fare distributions.
- **Route Weighting**: Real DGCA-derived passenger-traffic weights, explicitly distinguished from CPI expenditure weights.
- **Traffic Coverage**: Current 10 routes = 8.8% of India's domestic passenger traffic; 50 routes = 30.7%.
- **Outlier Handling**: Data Quality layer flags suspicious fares; Index engine performs statistical outlier detection (IQR/MAD/percentile).
- **Quality Flags**: Each route/period gets a status (`OK`, `NEW_ROUTE`, `DISCONTINUED`, `INSUFFICIENT_DATA`, etc.).
- **Volatility**: Coefficient of variation (CV) per route, with booking-horizon breakdown (T+1 to T+45).
- **Affordability**: Relative Airfare Affordability Index = (Airfare Index / Income Index) × 100 — explicitly not a household affordability measure.
- **CPI Benchmark**: Structural comparison against MoSPI CPI, with rebasing to common base period; MoM/YoY differences reported with honesty about synthetic data limitations.

---

## 🛠️ Development Notes

- **vite.config.ts**: Fixed ES module compatibility issue — replaced `__dirname` with `import.meta.dirname` via `fileURLToPath`.
- **Data Pipeline**: Scraper output → data_quality validation → AirfarePriceIndex calculation → API → Frontend dashboard.
- **Forecasting Stages**: Stage 1 (data access/prep) → Stage 2 (exploration) → Stage 3 (national baseline forecasting) → Stage 3.1 (calendar-gap fixes) → Stage 4 (YoY comparison) → Stage 20 (booking-horizon analytics).
- **API Design**: Thin wrapper pattern — `api/main.py` delegates to `index_engine` and `forecasting.*` modules with zero duplicated logic.
- **Honesty Convention**: Every result carries `is_synthetic_data` flag; no fabricated numbers; gaps reported as `NaN`/`None` with explicit quality flags.
- **Testing**: 88/88 tests pass in `index_engine`; extensive test suites for forecasting, CPI benchmark, data quality, and API endpoints.

---

## 📝 Report Generation

This project generates comprehensive reports across these documentation pillars:
- `docs/methodology.md` — Statistical methodology for the Airfare Price Index
- `docs/forecasting_methodology.md` — Forecasting pipeline (Stages 1–3.1) + CPI benchmark
- `docs/data_quality.md` — Scraper validation & quality grading
- `docs/sih_pitch.md` — SIH differentiation & 20 likely judge questions
- `docs/data_contract.md` — Input/output data contract specification
- `docs/test_cases.md` — Test case definitions

These are the primary sources for any project report or judge Q&A.
