import os
import sys
import sqlite3
import datetime
import pandas as pd
import numpy as np
from typing import Optional
from fastapi import FastAPI, Query, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel

# -------------------------------------------------------------------
# Path Configurations & Imports
# -------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROTOTYPE_DIR = os.path.dirname(os.path.abspath(__file__))
for path in [BASE_DIR, PROTOTYPE_DIR]:
    if path not in sys.path:
        sys.path.append(path)

from database.db_manager import DB_PATH, init_db

# Import Index Calculation Engine
try:
    from calculate_index import calculate_prototype_index
except ImportError:
    from prototype.calculate_index import calculate_prototype_index

# Import Knowledge Graph Engine
try:
    from kg_calculate_index import get_graph_insights
    kg_available = True
except ImportError:
    try:
        from prototype.kg_calculate_index import get_graph_insights
        kg_available = True
    except ImportError:
        kg_available = False

# Import Flight Scraper Engine
try:
    from scrapers.flight_scraper import scrape_and_persist_fares
except ImportError:
    scrape_and_persist_fares = None

# Optional PDF export library
try:
    from fpdf import FPDF
    fpdf_available = True
except ImportError:
    fpdf_available = False


# -------------------------------------------------------------------
# FastAPI App Initialization
# -------------------------------------------------------------------
app = FastAPI(title="Faresense - National Airfare Intelligence API")

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -------------------------------------------------------------------
# Helper Data Loaders
# -------------------------------------------------------------------
def get_filtered_df(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    booking_lead: Optional[str] = None,
    airline: Optional[str] = None
) -> pd.DataFrame:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    fares_df = pd.read_sql_query("SELECT * FROM live_fares ORDER BY id DESC", conn)
    conn.close()

    if fares_df.empty:
        return fares_df

    # Standardize route_id & origin/destination
    if 'route_id' not in fares_df.columns:
        if 'origin_airport' in fares_df.columns and 'destination_airport' in fares_df.columns:
            fares_df['route_id'] = fares_df['origin_airport'] + "-" + fares_df['destination_airport']
        elif 'route' in fares_df.columns:
            fares_df['route_id'] = fares_df['route']

    if ('origin_airport' not in fares_df.columns or fares_df['origin_airport'].isnull().all()) and 'route_id' in fares_df.columns:
        split_routes = fares_df['route_id'].str.split('-', expand=True)
        if split_routes.shape[1] == 2:
            fares_df['origin_airport'] = split_routes[0]
            fares_df['destination_airport'] = split_routes[1]

    # Date filtering
    if 'scrape_timestamp' in fares_df.columns:
        fares_df['date_dt'] = pd.to_datetime(fares_df['scrape_timestamp']).dt.date
        if start_date:
            fares_df = fares_df[fares_df['date_dt'] >= pd.to_datetime(start_date).date()]
        if end_date:
            fares_df = fares_df[fares_df['date_dt'] <= pd.to_datetime(end_date).date()]

    # Booking Lead filtering
    if booking_lead and booking_lead != "All Windows" and 'booking_lead_days' in fares_df.columns:
        lead_val = int(booking_lead.replace("T-", "").replace(" days", ""))
        fares_df = fares_df[fares_df['booking_lead_days'] == lead_val]

    # Airline filtering
    if airline and airline != "All Airlines" and 'airline' in fares_df.columns:
        fares_df = fares_df[fares_df['airline'] == airline]

    return fares_df


# -------------------------------------------------------------------
# REST API Endpoints
# -------------------------------------------------------------------

@app.get("/")
def serve_frontend():
    """Serves the main HTML page directly from root"""
    if os.path.exists("index.html"):
        return FileResponse("index.html")
    return HTMLResponse("<h2>index.html not found in root directory</h2>")


@app.get("/api/filters")
def get_filters():
    """Returns dynamic filter options available in database"""
    fares_df = get_filtered_df()
    if fares_df.empty:
        return {"airlines": ["All Airlines"], "leads": ["All Windows"], "dates": {"min": "", "max": ""}}

    airlines = ["All Airlines"]
    if 'airline' in fares_df.columns:
        airlines += sorted(fares_df['airline'].dropna().unique().tolist())

    leads = ["All Windows"]
    if 'booking_lead_days' in fares_df.columns:
        leads += [f"T-{d} days" for d in sorted(fares_df['booking_lead_days'].unique().tolist())]

    dates = {"min": "", "max": ""}
    if 'date_dt' in fares_df.columns:
        dates["min"] = str(fares_df['date_dt'].min())
        dates["max"] = str(fares_df['date_dt'].max())

    return {"airlines": airlines, "leads": leads, "dates": dates}


@app.get("/api/dashboard")
def get_dashboard_metrics(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    booking_lead: Optional[str] = None,
    airline: Optional[str] = None
):
    """Calculates MoSPI Index, Route Averages, Trends, and Anomaly Alerts"""
    filtered_df = get_filtered_df(start_date, end_date, booking_lead, airline)
    
    if filtered_df.empty:
        return {
            "overall_index": 100.0,
            "avg_fare": 0.0,
            "delta_pct": 0.0,
            "relatives": {},
            "route_avgs": {},
            "historical_trend": [],
            "anomalies": [],
            "heatmap": {"x": [], "y": [], "z": []},
            "carrier_share": []
        }

    # Compute Index
    overall_index, route_avgs, relatives, _ = calculate_prototype_index(filtered_df)
    avg_fare = float(np.mean(list(route_avgs.values()))) if route_avgs else 0.0
    delta_val = round(overall_index - 100.0, 2)

    # Historical Trend Data
    historical_trend = []
    if 'scrape_timestamp' in filtered_df.columns:
        trend_df = filtered_df.copy()
        trend_df['date'] = pd.to_datetime(trend_df['scrape_timestamp']).dt.date.astype(str)
        daily = trend_df.groupby('date')['price'].mean().reset_index()
        base_ref = 4500.0
        daily['index_val'] = (daily['price'] / base_ref) * 100.0
        historical_trend = daily.to_dict(orient='records')

    # Anomaly Detection (> 2 std)
    anomalies = []
    if 'price' in filtered_df.columns and 'route_id' in filtered_df.columns:
        stats = filtered_df.groupby('route_id')['price'].agg(['mean', 'std']).reset_index()
        merged = pd.merge(filtered_df, stats, on='route_id')
        merged['z_score'] = (merged['price'] - merged['mean']) / merged['std'].replace(0, 1)
        anomalies_df = merged[merged['z_score'] > 2.0]
        if not anomalies_df.empty:
            anomalies = anomalies_df[['route_id', 'price', 'z_score']].head(5).to_dict(orient='records')

    # Heatmap Matrix Data
    heatmap = {"x": [], "y": [], "z": []}
    if 'origin_airport' in filtered_df.columns and 'destination_airport' in filtered_df.columns:
        pivot_df = filtered_df.pivot_table(index='origin_airport', columns='destination_airport', values='price', aggfunc='mean')
        heatmap = {
            "x": [str(c) for c in pivot_df.columns],
            "y": [str(i) for i in pivot_df.index],
            "z": pivot_df.fillna(0).values.tolist()
        }

    # Carrier Inventory Share
    carrier_share = []
    if 'airline' in filtered_df.columns:
        shares = filtered_df['airline'].value_counts().reset_index()
        shares.columns = ['airline', 'count']
        carrier_share = shares.to_dict(orient='records')

    return {
        "overall_index": round(overall_index, 2),
        "avg_fare": round(avg_fare, 2),
        "delta_pct": delta_val,
        "relatives": relatives,
        "route_avgs": route_avgs,
        "historical_trend": historical_trend,
        "anomalies": anomalies,
        "heatmap": heatmap,
        "carrier_share": carrier_share
    }


@app.get("/api/knowledge-graph")
def get_knowledge_graph(hub: str = "DEL"):
    """Fetches knowledge graph insights for transit hub connectivity"""
    if not kg_available:
        raise HTTPException(status_code=500, detail="kg_calculate_index module not available")
    
    filtered_df = get_filtered_df()
    graph_data = get_graph_insights(hub, filtered_df)
    return graph_data


@app.get("/api/logs")
def get_logs():
    """Returns raw database records for the inspector tab"""
    filtered_df = get_filtered_df()
    return filtered_df.head(100).to_dict(orient='records')


@app.post("/api/scrape")
def trigger_scrape():
    """Triggers the flight scraper module"""
    if scrape_and_persist_fares is None:
        raise HTTPException(status_code=500, detail="Flight scraper module missing")
    
    scrape_and_persist_fares(lead_days=7)
    return {"status": "success", "message": "Scraped live fares successfully!"}


@app.get("/api/export-pdf")
def export_pdf():
    """Generates executive summary PDF report"""
    if not fpdf_available:
        raise HTTPException(status_code=500, detail="fpdf library is not installed")

    filtered_df = get_filtered_df()
    overall_index, route_avgs, _, _ = calculate_prototype_index(filtered_df)

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "National Airfare Intelligence Executive Summary", ln=True, align='C')
    pdf.set_font("Arial", '', 10)
    pdf.cell(0, 8, f"Generated on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True, align='C')
    pdf.ln(10)
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, f"Overall MoSPI Airfare Index: {overall_index:.2f} pts", ln=True)
    pdf.cell(0, 10, f"Total Monitored Corridors: {len(route_avgs)}", ln=True)
    pdf.ln(5)

    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 8, "Corridor Averages:", ln=True)
    pdf.set_font("Arial", '', 10)
    for r, avg in route_avgs.items():
        pdf.cell(0, 6, f" - {r}: INR {avg:,.2f}", ln=True)

    pdf_output = pdf.output(dest='S').encode('latin1')
    return Response(content=pdf_output, media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=Airfare_Report.pdf"})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)