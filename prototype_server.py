"""
prototype_server.py
===================
Standalone FastAPI server that the prototype/index.html frontend connects to.

Endpoints expected by the frontend:
  GET  /api/dashboard-data?horizon=T%2B1&route=DEL-BOM
  POST /api/trigger-scrape?route=DEL-BOM

Run with:
  source .venv/bin/activate
  uvicorn prototype_server:app --host 127.0.0.1 --port 8000 --reload
"""

from __future__ import annotations

import os
import random
import sqlite3
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

# pyrefly: ignore [missing-import]
import uvicorn
# pyrefly: ignore [missing-import]
from fastapi import FastAPI, Query
# pyrefly: ignore [missing-import]
from fastapi.middleware.cors import CORSMiddleware
# pyrefly: ignore [missing-import]
from fastapi.responses import JSONResponse

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(title="Faresense Prototype API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # Prototype: allow all origins (file://)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Database helpers ───────────────────────────────────────────────────────────
DB_PATH = Path(__file__).parent / "database" / "airfare_index.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_schema():
    with _get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS live_fares (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scrape_timestamp TEXT,
                origin TEXT,
                destination TEXT,
                airline TEXT,
                flight_number TEXT,
                price REAL,
                departure_time TEXT,
                booking_lead_days INTEGER,
                flight_type TEXT,
                cabin_class TEXT,
                source TEXT
            )
        """)
        conn.commit()


_ensure_schema()

# ── Baseline data ──────────────────────────────────────────────────────────────
BASE_PRICES: dict[str, float] = {
    "DEL-BOM": 4000.0,
    "DEL-BLR": 4800.0,
    "BOM-MAA": 3500.0,
    "BOM-BLR": 3200.0,
    "DEL-CCU": 4200.0,
    "MAA-DEL": 4600.0,
    "BLR-HYD": 2800.0,
}
ROUTE_WEIGHTS: dict[str, float] = {
    "DEL-BOM": 0.35,
    "DEL-BLR": 0.25,
    "BOM-MAA": 0.15,
    "BOM-BLR": 0.10,
    "DEL-CCU": 0.08,
    "MAA-DEL": 0.05,
    "BLR-HYD": 0.02,
}
AIRLINES = ["IndiGo", "Air India", "SpiceJet", "Vistara", "Akasa Air"]
HORIZON_LEAD: dict[str, int] = {"T+1": 1, "T+7": 7, "T+15": 15, "T+30": 30, "T+45": 45}


# ── Scraper integration ────────────────────────────────────────────────────────
def _run_scraper(route: str | None) -> tuple[list[dict], str]:
    """
    Calls flight_scraper.scrape_and_persist_fares() for all monitored routes
    (or just the requested one).  Falls back to realistic synthetic data if
    scraping fails entirely.
    """
    records: list[dict] = []
    source = "fallback"

    try:
        import importlib.util, sys as _sys
        spec = importlib.util.spec_from_file_location(
            "flight_scraper",
            str(Path(__file__).parent / "flight_scraper.py"),
        )
        mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
        _sys.modules["flight_scraper"] = mod
        spec.loader.exec_module(mod)  # type: ignore[union-attr]

        df = mod.scrape_and_persist_fares(lead_days=7)
        if not df.empty:
            records = df.to_dict("records")
            source = "google-flights"
    except Exception:
        traceback.print_exc()
        # Pure synthetic fallback
        records = _synthetic_fares(route)
        source = "fallback"

    return records, source


def _synthetic_fares(route: str | None = None) -> list[dict]:
    """Generate realistic synthetic fares for all/one route."""
    now = datetime.now()
    routes = [route] if route and "-" in (route or "") else list(BASE_PRICES.keys())
    out = []
    for r in routes:
        if r not in BASE_PRICES:
            continue
        base = BASE_PRICES[r]
        origin, dest = r.split("-")
        for horizon, lead in HORIZON_LEAD.items():
            mult = 1.45 if lead <= 2 else (1.2 if lead <= 7 else 1.0)
            for airline in random.sample(AIRLINES, k=min(3, len(AIRLINES))):
                price = round(base * mult * random.uniform(0.90, 1.18), 2)
                out.append({
                    "scrape_timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
                    "origin": origin,
                    "destination": dest,
                    "airline": airline,
                    "flight_number": f"6E-{random.randint(100, 999)}",
                    "price": price,
                    "departure_time": f"{(now + timedelta(days=lead)).strftime('%Y-%m-%d')} 08:00:00",
                    "booking_lead_days": lead,
                    "flight_type": "Direct",
                    "cabin_class": "economy",
                    "source": "synthetic",
                })
    return out


def _load_from_db(route: str | None, horizon: str) -> list[dict]:
    lead = HORIZON_LEAD.get(horizon, 7)
    route_filter = ""
    params: list[Any] = [lead + 4]

    if route and "-" in (route or ""):
        parts = route.split("-")
        if len(parts) == 2:
            route_filter = "AND origin = ? AND destination = ?"
            params = [parts[0], parts[1]] + params

    try:
        with _get_conn() as conn:
            rows = conn.execute(f"""
                SELECT * FROM live_fares
                WHERE booking_lead_days <= ?
                {route_filter}
                ORDER BY scrape_timestamp DESC
                LIMIT 100
            """, params[::-1] if route_filter else params).fetchall()
        return [dict(r) for r in rows]
    except Exception:
        return []


# ── Index calculation ──────────────────────────────────────────────────────────
BASE_INDEX = 100.0


def _compute_index(records: list[dict], horizon: str) -> dict:
    lead = HORIZON_LEAD.get(horizon, 7)
    filtered = [r for r in records if abs(r.get("booking_lead_days", 99) - lead) <= 4]
    if not filtered:
        filtered = records  # loosen filter if nothing

    route_avgs: dict[str, float] = {}
    carrier_counts: dict[str, int] = {}

    for rec in filtered:
        route_key = f"{rec.get('origin', '')}-{rec.get('destination', '')}"
        if route_key not in route_avgs:
            route_avgs[route_key] = 0.0
        route_avgs[route_key] += rec.get("price", 0.0)
        airline = rec.get("airline", "Unknown")
        carrier_counts[airline] = carrier_counts.get(airline, 0) + 1

    # Average per route
    route_counts: dict[str, int] = {}
    for rec in filtered:
        k = f"{rec.get('origin', '')}-{rec.get('destination', '')}"
        route_counts[k] = route_counts.get(k, 0) + 1
    for k in route_avgs:
        route_avgs[k] = route_avgs[k] / route_counts.get(k, 1)

    # Weighted Laspeyres index
    total_weight = 0.0
    index_sum = 0.0
    for route, avg in route_avgs.items():
        w = ROUTE_WEIGHTS.get(route, 0.05)
        base = BASE_PRICES.get(route, 4000.0)
        if base > 0:
            index_sum += w * (avg / base) * BASE_INDEX
            total_weight += w

    overall = (index_sum / total_weight) if total_weight > 0 else BASE_INDEX
    avg_fare = (
        sum(r.get("price", 0.0) for r in filtered) / len(filtered) if filtered else 4500.0
    )
    delta_pct = overall - BASE_INDEX

    # Carrier share
    total_quotes = sum(carrier_counts.values())
    carrier_share = [
        {"airline": k, "count": v, "pct": round(v / total_quotes * 100, 1)}
        for k, v in sorted(carrier_counts.items(), key=lambda x: -x[1])
    ]

    # Historical trend (last 14 mock points with slight noise)
    now = datetime.now()
    hist = []
    for i in range(14, 0, -1):
        noise = random.uniform(-3, 3)
        hist.append({
            "date": (now - timedelta(days=i)).strftime("%d %b"),
            "index_val": round(overall - noise, 2),
        })

    # Relatives (route index vs national)
    relatives = {
        route: round((avg / BASE_PRICES.get(route, 4000.0)) * BASE_INDEX, 2)
        for route, avg in route_avgs.items()
    }

    return {
        "overall_index": round(overall, 2),
        "avg_fare": round(avg_fare, 2),
        "delta_pct": round(delta_pct, 2),
        "route_avgs": {k: round(v, 2) for k, v in route_avgs.items()},
        "relatives": relatives,
        "carrier_share": carrier_share,
        "historical_trend": hist,
        "flight_records": filtered[:20],
    }


# ── Endpoints ──────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "server": "Faresense Prototype API"}


@app.get("/api/dashboard-data")
def dashboard_data(
    horizon: str = Query("T+1"),
    route: str | None = Query(None),
):
    records = _load_from_db(route, horizon)
    if not records:
        records = _synthetic_fares(route)

    payload = _compute_index(records, horizon)
    payload["last_sync_timestamp"] = datetime.now().isoformat()

    source_counts: dict[str, int] = {}
    for r in records:
        s = r.get("source", "unknown")
        source_counts[s] = source_counts.get(s, 0) + 1
    payload["source_counts"] = source_counts

    # Horizon KPIs for all horizons
    horizon_kpis = []
    for h, lead in HORIZON_LEAD.items():
        mult = 1.45 if lead <= 2 else (1.2 if lead <= 7 else 1.0)
        base_fare = 5000.0
        obs = round(base_fare * mult * random.uniform(0.95, 1.08), 0)
        idx = round((obs / base_fare) * BASE_INDEX, 1)
        horizon_kpis.append({
            "horizon": h,
            "index_score": idx,
            "variance_pct": round(idx - BASE_INDEX, 2),
            "avg_observed_fare": obs,
        })
    payload["horizon_kpis"] = horizon_kpis

    return JSONResponse({"data": payload, **payload})


@app.post("/api/trigger-scrape")
def trigger_scrape(route: str | None = Query(None)):
    records, source = _run_scraper(route)

    if records:
        try:
            with _get_conn() as conn:
                conn.executemany("""
                    INSERT INTO live_fares
                    (scrape_timestamp, origin, destination, airline, flight_number,
                     price, departure_time, booking_lead_days, flight_type, cabin_class, source)
                    VALUES
                    (:scrape_timestamp, :origin, :destination, :airline, :flight_number,
                     :price, :departure_time, :booking_lead_days, :flight_type, :cabin_class, :source)
                """, records)
                conn.commit()
        except Exception:
            traceback.print_exc()

    source_counts: dict[str, int] = {}
    for r in records:
        s = r.get("source", "unknown")
        source_counts[s] = source_counts.get(s, 0) + 1

    return {
        "message": f"Live fares refreshed via {source} ({len(records)} records)",
        "records_fetched": len(records),
        "source": source,
        "source_counts": source_counts,
        "last_sync_timestamp": datetime.now().isoformat(),
    }


@app.get("/api/analytics-data")
def analytics_data(route: str | None = Query(None)):
    records = _synthetic_fares(route)
    return {
        "national_composite_api": "123.28",
        "highest_volatility_corridor": route or "DEL-BOM",
        "advance_purchase_discount_pct": "18.4",
        "monitored_trunk_corridors": len(BASE_PRICES),
        "route_fare_comparison": [
            {"route": r, "avg_fare": round(BASE_PRICES.get(r, 4000) * random.uniform(0.95, 1.15), 0), "index_score": round(random.uniform(98, 130), 1)}
            for r in list(BASE_PRICES.keys())[:6]
        ],
        "airline_market_share": [
            {"airline": a, "quote_volume": random.randint(200, 800), "avg_observed_fare": round(random.uniform(3500, 7000), 0)}
            for a in AIRLINES
        ],
        "index_trend_lines": [
            {
                "date": (datetime.now() - timedelta(days=30 - i)).strftime("%d %b"),
                "T+1": round(random.uniform(108, 120), 1),
                "T+7": round(random.uniform(102, 115), 1),
                "T+45": round(random.uniform(95, 105), 1),
            }
            for i in range(30)
        ],
    }


@app.get("/api/surveillance-data")
def surveillance_data():
    return {
        "extractor_status_pct": 92,
        "last_extraction": datetime.now().isoformat(),
        "quotes_collected_today": random.randint(30000, 40000),
        "data_freshness_score_pct": 96,
        "carrier_daemons": [
            {"name": f"{a} Extractor", "status": "Active", "coverage_pct": random.randint(88, 99)}
            for a in AIRLINES
        ],
        "corridors": [
            {"route": r, "weight_factor": round(w, 2), "frequency": "Every 15s", "status": "Ingesting"}
            for r, w in ROUTE_WEIGHTS.items()
        ],
    }


@app.get("/api/reports-data")
def reports_data():
    return {
        "executive_summary": {
            "national_airfare_index": "123.28",
            "avg_fare_national": "₹5,032",
            "highest_fare_corridor": "DEL-BOM",
            "lowest_fare_corridor": "BLR-HYD",
            "data_coverage": "94.2%",
            "report_period": datetime.now().strftime("%b %Y"),
        },
        "route_summary": [
            {
                "route": r,
                "index_score": round((BASE_PRICES[r] * 1.15) / BASE_PRICES[r] * 100, 1),
                "avg_fare": round(BASE_PRICES[r] * random.uniform(1.0, 1.25), 0),
                "quote_count": random.randint(500, 3000),
            }
            for r in BASE_PRICES
        ],
        "airline_compliance": [
            {"airline": a, "coverage": f"{random.randint(88, 99)}%", "status": "Compliant"}
            for a in AIRLINES
        ],
    }


@app.get("/api/export-pdf")
def export_pdf():
    # pyrefly: ignore [missing-import]
    from fastapi.responses import Response
    content = b"%PDF-1.4 mock report"
    return Response(content=content, media_type="application/pdf",
                    headers={"Content-Disposition": "attachment; filename=Airfare_Report.pdf"})


if __name__ == "__main__":
    uvicorn.run("prototype_server:app", host="127.0.0.1", port=8000, reload=True)
