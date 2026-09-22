import os
import sys
import random
import pandas as pd
from datetime import datetime, timedelta

# Fast-flights parser imports (v3.x compliant)
try:
    from fast_flights import FlightQuery, Passengers, create_query, get_flights
except ImportError:
    print("⚠️ 'fast-flights' package not found. Installing via pip...")
    os.system(f"{sys.executable} -m pip install fast-flights")
    from fast_flights import FlightQuery, Passengers, create_query, get_flights

# Add parent directory to path so database module can be imported
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from database.db_manager import save_scraped_fares, init_db
except ImportError:
    # Inline fallback if db_manager path resolution fails
    def init_db(): pass
    def save_scraped_fares(df):
        db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "database", "airfare_index.db")
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        import sqlite3
        conn = sqlite3.connect(db_path)
        df.to_sql("live_fares", conn, if_exists="append", index=False)
        conn.close()

# Monitored Core Routes for MoSPI Price Index
MONITORED_ROUTES = [
    ("DEL", "BOM"),
    ("DEL", "BLR"),
    ("BOM", "MAA")
]

# Baseline prices fallback reference table (INR)
BASE_PRICES = {
    "DEL-BOM": 4000.0,
    "DEL-BLR": 4800.0,
    "BOM-MAA": 3500.0
}

AIRLINES = ["IndiGo", "Air India", "SpiceJet", "Vistara", "Akasa Air"]


def generate_fallback_flight(origin: str, dest: str, lead_days: int) -> dict:
    """Generates realistic fallback fare if scraping fails or gets rate-limited."""
    route_key = f"{origin}-{dest}"
    base_price = BASE_PRICES.get(route_key, 4000.0)
    
    # Lead-time urgency multiplier
    urgency_mult = 1.45 if lead_days <= 2 else (1.2 if lead_days <= 7 else 1.0)
    price = round(base_price * urgency_mult * random.uniform(0.92, 1.15), 2)
    target_date = (datetime.now() + timedelta(days=lead_days)).strftime("%Y-%m-%d")
    
    return {
        "scrape_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "origin": origin,
        "destination": dest,
        "airline": random.choice(AIRLINES),
        "flight_number": f"6E-{random.randint(1000, 9999)}",
        "price": price,
        "departure_time": f"{target_date} 08:30:00",
        "booking_lead_days": lead_days,
        "flight_type": "Direct",
        "cabin_class": "economy",
        "source": "fallback_generator"
    }


def parse_price_value(raw_price) -> float:
    """Safely extracts numeric float from price strings or objects."""
    if raw_price is None:
        return 0.0
    if isinstance(raw_price, (int, float)):
        return float(raw_price)
    
    # Clean currency symbols, commas, and whitespace
    cleaned = str(raw_price).replace('₹', '').replace('Rs.', '').replace(',', '').strip()
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def scrape_and_persist_fares(lead_days: int = 14) -> pd.DataFrame:
    """
    Scrapes live flight prices for monitored routes and automatically 
    persists them into the SQLite database.
    """
    # 1. Initialize SQLite Database if missing
    init_db()
    
    target_date = (datetime.now() + timedelta(days=lead_days)).strftime("%Y-%m-%d")
    scraped_records = []
    
    print(f"🛫 Initiating fare collection for target date: {target_date} (T-{lead_days} days)...")

    for origin, dest in MONITORED_ROUTES:
        route_str = f"{origin}-{dest}"
        print(f"   --> Querying Google Flights for route: {route_str}...")
        
        try:
            # Construct fast-flights search query (v3.x API)
            query = create_query(
                flights=[
                    FlightQuery(
                        date=target_date,
                        from_airport=origin,
                        to_airport=dest
                    )
                ],
                trip="one-way",
                seat="economy",
                passengers=Passengers(adults=1)
            )
            
            # Fetch flights from Google Flights RPC endpoint
            result = get_flights(query)
            
            # Parse results
            flights_found = getattr(result, 'flights', []) or []
            if len(flights_found) > 0:
                for f in flights_found[:5]:
                    raw_price = getattr(f, 'price', None) or getattr(f, 'current_price', None)
                    price_val = parse_price_value(raw_price)
                    
                    if price_val <= 0:
                        continue
                        
                    airline_name = getattr(f, 'name', None) or getattr(f, 'airline', 'IndiGo')
                    
                    scraped_records.append({
                        "scrape_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "origin": origin,
                        "destination": dest,
                        "airline": str(airline_name),
                        "flight_number": getattr(f, 'flight_number', f"6E-{random.randint(100, 999)}"),
                        "price": float(price_val),
                        "departure_time": f"{target_date} {getattr(f, 'departure', '08:00')}",
                        "booking_lead_days": lead_days,
                        "flight_type": "Direct" if getattr(f, 'is_direct', True) else "Layover",
                        "cabin_class": "economy",
                        "source": "fast-flights"
                    })
                print(f"       ✅ Successfully extracted live fares for {route_str}")
            else:
                raise ValueError("Empty flight results returned by scraper")

        except Exception as e:
            print(f"       ⚠️ Scraper exception for {route_str} ({e}). Inserting fallback fare.")
            scraped_records.append(generate_fallback_flight(origin, dest, lead_days))

    df = pd.DataFrame(scraped_records)
    
    # 2. Automatically save DataFrame to SQLite database
    save_scraped_fares(df)
    
    return df


if __name__ == "__main__":
    # Test execution for T-7 days booking window
    df_results = scrape_and_persist_fares(lead_days=7)
    
    print("\n📊 Scraped Data Preview:")
    print("=" * 70)
    print(df_results[["origin", "destination", "airline", "price", "booking_lead_days", "source"]].to_string())
    print("=" * 70)