from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

# Repo root is the directory containing this file's parent's parent's parent
REPO_ROOT = Path(__file__).resolve().parents[3]
# But the file is at airfare-index-system/src/engine/data_access.py
# So parents[3] = airfare-index-system
# Let's verify
if not (REPO_ROOT / "database" / "airfare_index.db").exists():
    # Try parents[2]
    REPO_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = REPO_ROOT / "database" / "airfare_index.db"


def get_db_connection() -> sqlite3.Connection:
    """Get a connection to the SQLite database."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db_if_needed() -> None:
    """Initialize the database if it doesn't exist."""
    from database.db_manager import init_db
    init_db()


def load_raw_observations() -> Tuple[List[Dict[str, Any]], bool]:
    """
    Load raw fare observations from the database.
    
    Returns:
        Tuple of (observations_list, is_real_data_flag)
    """
    init_db_if_needed()
    
    with get_db_connection() as conn:
        # Check if we have any real scraped data
        cursor = conn.execute("SELECT COUNT(*) as cnt FROM live_fares")
        row = cursor.fetchone()
        count = row["cnt"] if row else 0
        
        if count == 0:
            # Return synthetic data if no real data
            return _get_synthetic_observations(), False
        
        # Load real data from database
        df = pd.read_sql_query("""
            SELECT 
                scrape_timestamp as date,
                origin || '-' || destination as route,
                origin,
                destination,
                airline,
                flight_number,
                price as fare,
                booking_lead_days,
                flight_type,
                cabin_class,
                source
            FROM live_fares
            ORDER BY scrape_timestamp DESC
        """, conn)
        
        observations = df.to_dict(orient="records")
        return observations, True


def load_validated_observations() -> Tuple[List[Dict[str, Any]], bool]:
    """
    Load validated fare observations (after cleaning).
    For now, this is the same as raw observations.
    """
    return load_raw_observations()


def available_periods(observations: List[Dict[str, Any]]) -> List[str]:
    """Extract available YYYY-MM periods from observations."""
    periods = set()
    for obs in observations:
        date_str = obs.get("date", "")
        if date_str and len(date_str) >= 7:
            periods.add(date_str[:7])  # YYYY-MM
    return sorted(periods)


def build_weights(observations: List[Dict[str, Any]]) -> Tuple[pd.DataFrame, bool]:
    """
    Build route weights from database or use defaults.
    
    Returns:
        Tuple of (weights_dataframe, is_real_weights_flag)
    """
    init_db_if_needed()
    
    with get_db_connection() as conn:
        cursor = conn.execute("SELECT COUNT(*) as cnt FROM route_weights")
        row = cursor.fetchone()
        count = row["cnt"] if row else 0
        
        if count == 0:
            # Use default weights
            return _get_default_weights(), False
        
        df = pd.read_sql_query("""
            SELECT route_id as route, origin, destination, weight
            FROM route_weights
        """, conn)
        
        return df, True


def get_base_prices() -> Tuple[pd.DataFrame, bool]:
    """
    Get base period prices from database or use defaults.
    
    Returns:
        Tuple of (base_prices_dataframe, is_real_flag)
    """
    init_db_if_needed()
    
    with get_db_connection() as conn:
        cursor = conn.execute("SELECT COUNT(*) as cnt FROM base_prices")
        row = cursor.fetchone()
        count = row["cnt"] if row else 0
        
        if count == 0:
            return _get_default_base_prices(), False
        
        df = pd.read_sql_query("""
            SELECT route_id as route, base_price
            FROM base_prices
        """, conn)
        
        return df, True


def _get_synthetic_observations() -> List[Dict[str, Any]]:
    """Generate synthetic observations for demo purposes."""
    import random
    from datetime import datetime, timedelta
    
    routes = [
        ("DEL", "BOM"), ("DEL", "BLR"), ("BOM", "MAA"),
        ("DEL", "CCU"), ("BLR", "HYD"), ("MAA", "DEL")
    ]
    airlines = ["IndiGo", "Air India", "Air India Express", "Akasa Air", "SpiceJet"]
    
    observations = []
    base_prices = {
        "DEL-BOM": 4000, "DEL-BLR": 4800, "BOM-MAA": 3500,
        "DEL-CCU": 4200, "BLR-HYD": 2800, "MAA-DEL": 4600
    }
    
    # Generate data for the last 8 months
    for month_offset in range(8):
        period_date = datetime.now() - timedelta(days=30 * month_offset)
        date_str = period_date.strftime("%Y-%m-%d")
        
        for origin, dest in routes:
            route = f"{origin}-{dest}"
            base = base_prices.get(route, 4000)
            
            # Generate 3-5 observations per route per period
            route_key = f"{origin}-{dest}"
            for _ in range(random.randint(3, 5)):
                multiplier = random.uniform(0.85, 1.25)
                fare = round(base * multiplier, 2)
                
                observations.append({
                    "date": date_str,
                    "route": route_key,
                    "origin": origin,
                    "destination": dest,
                    "airline": random.choice(airlines),
                    "flight_number": f"6E-{random.randint(100, 999)}",
                    "fare": fare,
                    "booking_lead_days": random.randint(1, 45),
                    "flight_type": "Direct",
                    "cabin_class": "economy",
                    "source": "synthetic"
                })
    
    return observations


def _get_default_weights() -> pd.DataFrame:
    """Get default route weights based on DGCA passenger traffic."""
    data = [
        {"route": "DEL-BOM", "origin": "DEL", "destination": "BOM", "weight": 0.45},
        {"route": "DEL-BLR", "origin": "DEL", "destination": "BLR", "weight": 0.35},
        {"route": "BOM-MAA", "origin": "BOM", "destination": "MAA", "weight": 0.20},
    ]
    return pd.DataFrame(data)


def _get_default_base_prices() -> pd.DataFrame:
    """Get default base period prices."""
    data = [
        {"route": "DEL-BOM", "base_price": 4000.0},
        {"route": "DEL-BLR", "base_price": 4800.0},
        {"route": "BOM-MAA", "base_price": 3500.0},
    ]
    return pd.DataFrame(data)


# --- Forecasting data access ---

def load_forecasting_observations() -> Tuple[pd.DataFrame, bool]:
    """Load observations formatted for forecasting."""
    observations, is_real = load_validated_observations()
    df = pd.DataFrame(observations)
    return df, is_real


def load_mospi_cpi_series(path: Path) -> pd.DataFrame:
    """Load MoSPI CPI reference series from Excel file."""
    if not path.exists():
        return pd.DataFrame()
    
    try:
        df = pd.read_excel(path)
        return df
    except Exception:
        return pd.DataFrame()