import os
import sqlite3
import pandas as pd

DB_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(DB_DIR, "airfare_index.db")
SCHEMA_PATH = os.path.join(DB_DIR, "init.sql")  # Changed from schema.sql to init.sql

def init_db():
    """Initializes SQLite database using database/init.sql."""
    os.makedirs(DB_DIR, exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Read and execute schema.sql
    if os.path.exists(SCHEMA_PATH):
        with open(SCHEMA_PATH, 'r') as f:
            schema_sql = f.read()
        cursor.executescript(schema_sql)
        conn.commit()
        print(f"✅ Database initialized and schema applied at: {DB_PATH}")
    else:
        print(f"⚠️ Warning: Schema file not found at {SCHEMA_PATH}")
        
    conn.close()

def save_scraped_fares(df: pd.DataFrame):
    """Appends scraped fare records into SQLite live_fares table."""
    if df.empty:
        print("⚠️ No scraped data to save.")
        return

    init_db()  # Ensure database exists
    conn = sqlite3.connect(DB_PATH)
    
    # Insert scraped DataFrame directly into live_fares table
    df.to_sql("live_fares", conn, if_exists="append", index=False)
    conn.close()
    
    print(f"💾 Successfully stored {len(df)} scraped fare records into SQLite.")

def fetch_latest_fares(limit: int = 10) -> pd.DataFrame:
    """Helper query function to inspect recent fares stored in SQLite."""
    conn = sqlite3.connect(DB_PATH)
    query = "SELECT * FROM live_fares ORDER BY id DESC LIMIT ?"
    df = pd.read_sql_query(query, conn, params=(limit,))
    conn.close()
    return df

if __name__ == "__main__":
    init_db()
    
    # Preview reference database tables
    conn = sqlite3.connect(DB_PATH)
    routes_df = pd.read_sql_query("SELECT * FROM route_weights", conn)
    print("\n📊 Pre-loaded MoSPI Route Weights (W_0):")
    print(routes_df.to_string(index=False))
    conn.close()