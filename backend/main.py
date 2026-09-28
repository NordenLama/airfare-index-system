from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import pandas as pd
from typing import List, Optional

from app.index_engine import AirfareIndexEngine
from app.knowledge_graph import RouteKnowledgeGraph

app = FastAPI(
    title="Airfare Price Index & Tracking API",
    description="Backend engine for calculating domestic airfare indices, surge monitoring, and route network graph traversal.",
    version="1.0.0"
)

# Initialize engines with baseline sample data (e.g., Top Indian Domestic Routes)
base_data = pd.DataFrame([
    {"route": "DEL-BOM", "base_price": 4500, "passenger_weight": 0.35},
    {"route": "BLR-DEL", "base_price": 5000, "passenger_weight": 0.25},
    {"route": "BOM-MAA", "base_price": 3800, "passenger_weight": 0.20},
    {"route": "DEL-CCU", "base_price": 4200, "passenger_weight": 0.20},
])

index_engine = AirfareIndexEngine(base_period_data=base_data)
kg_engine = RouteKnowledgeGraph()


# Pydantic Request Models
class PricePoint(BaseModel):
    route: str
    current_price: float

class IndexRequest(BaseModel):
    prices: List[PricePoint]


@app.get("/")
def read_root():
    return {"status": "active", "service": "Airfare Price Index Engine"}


@app.post("/api/v1/calculate-index")
def calculate_index(payload: IndexRequest):
    """
    Accepts current prices across routes and returns the calculated Laspeyres Price Index.
    """
    try:
        data = pd.DataFrame([p.model_dump() for p in payload.prices])
        index_val = index_engine.calculate_laspeyres_index(data)
        
        status = "Baseline Normal"
        if index_val > 110:
            status = "High Fare Inflation"
        elif index_val < 90:
            status = "Discounted Fares"

        return {
            "airfare_price_index": index_val,
            "status": status,
            "base_index_reference": 100.0
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/v1/surge-alerts")
def get_surge_alerts():
    """
    Analyzes historical mock trend data to detect routes experiencing price surges.
    """
    historical_mock = pd.DataFrame([
        {"route": "DEL-BOM", "price": 4500},
        {"route": "DEL-BOM", "price": 4600},
        {"route": "DEL-BOM", "price": 4550},
        {"route": "DEL-BOM", "price": 8200},  # Price spike
        {"route": "BLR-DEL", "price": 5000},
        {"route": "BLR-DEL", "price": 5100},
        {"route": "BLR-DEL", "price": 5050},
    ])
    surges = index_engine.detect_price_surges(historical_mock, threshold_std=1.5)
    return {"surges_detected_count": len(surges), "details": surges}


@app.get("/api/v1/graph/hub-impact/{hub_code}")
def get_hub_network_impact(hub_code: str):
    """
    Queries Knowledge Graph to fetch routes affected by a central hub disruption/surge.
    """
    routes = kg_engine.get_connected_routes_from_hub(hub_code.upper())
    return {
        "hub": hub_code.upper(),
        "connected_routes_count": len(routes),
        "network_nodes": routes
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)