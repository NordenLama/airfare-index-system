import os
import sys
import sqlite3
import pandas as pd
import streamlit as st

# Add base paths to sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROTOTYPE_DIR = os.path.dirname(os.path.abspath(__file__))
for path in [BASE_DIR, PROTOTYPE_DIR]:
    if path not in sys.path:
        sys.path.append(path)

from database.db_manager import DB_PATH, init_db

# Import Index Engine
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

# Import Flight Scraper
try:
    from scrapers.flight_scraper import scrape_and_persist_fares
except ImportError:
    scrape_and_persist_fares = None

# -------------------------------------------------------------------
# Page Configuration
# -------------------------------------------------------------------
st.set_page_config(
    page_title="Indian Airfare Price Index System",
    page_icon="✈️",
    layout="wide"
)

# -------------------------------------------------------------------
# Database Data Retrieval Helper
# -------------------------------------------------------------------
def load_data_from_db():
    init_db()
    conn = sqlite3.connect(DB_PATH)
    live_fares_df = pd.read_sql_query("SELECT * FROM live_fares ORDER BY id DESC", conn)
    weights_df = pd.read_sql_query("SELECT * FROM route_weights", conn)
    base_prices_df = pd.read_sql_query("SELECT * FROM base_prices", conn)
    conn.close()
    return live_fares_df, weights_df, base_prices_df

# Load central database records
fares_df, weights_df, base_prices_df = load_data_from_db()

# -------------------------------------------------------------------
# Sidebar Navigation & Controls
# -------------------------------------------------------------------
st.sidebar.title("✈️ Navigation")
page_selection = st.sidebar.radio(
    "Select View Dashboard:",
    ["📊 MoSPI Airfare Index", "🕸️ Knowledge Graph Analytics", "📂 Scraped Data Logs"]
)

st.sidebar.divider()
st.sidebar.header("🕹️ Scraper Controls")

if st.sidebar.button("🚀 Fetch Latest Live Fares", type="primary"):
    if scrape_and_persist_fares is not None:
        with st.spinner("Scraping live fares from Google Flights..."):
            scrape_and_persist_fares(lead_days=7)
            st.sidebar.success("Updated live fares successfully!")
            st.rerun()
    else:
        st.sidebar.error("Scraper module missing!")

# Booking lead time selector filter
if not fares_df.empty and 'booking_lead_days' in fares_df.columns:
    available_leads = sorted(fares_df['booking_lead_days'].unique().tolist())
    lead_options = ["All Windows"] + [f"T-{d} days" for d in available_leads]
else:
    lead_options = ["All Windows"]

selected_lead = st.sidebar.selectbox("Filter Booking Window", lead_options)

# Filter dataset globally based on selection
filtered_df = fares_df.copy()
if selected_lead != "All Windows" and not filtered_df.empty:
    lead_val = int(selected_lead.replace("T-", "").replace(" days", ""))
    filtered_df = filtered_df[filtered_df['booking_lead_days'] == lead_val]

# Compute MoSPI Index
overall_index, route_avgs, relatives, _ = calculate_prototype_index(filtered_df)


# ===================================================================
# TAB 1: Main MoSPI Index Dashboard (Front Page)
# ===================================================================
if page_selection == "📊 MoSPI Airfare Index":
    st.title("📊 Indian Airfare Price Index (MoSPI Methodology)")
    st.caption("Statistical Laspeyres Index based on real-time scraped domestic airfares")

    if not filtered_df.empty and 'scrape_timestamp' in filtered_df.columns:
        st.info(f"🕒 **Last Data Update:** `{filtered_df['scrape_timestamp'].iloc[0]}`")

    # High-level Metrics Cards
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Overall MoSPI Index", f"{overall_index}", delta=f"{round(overall_index - 100.0, 2)}% vs Base")
    with m2:
        st.metric("Scraped Fare Records", len(filtered_df))
    with m3:
        st.metric("Monitored Routes", len(route_avgs))
    with m4:
        st.metric("Data Source Engine", "SQLite (`live_fares`)")

    st.divider()

    # Route Breakdown & Baseline Tables
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("📌 Route Price Relatives (P_t / P_0 * 100)")
        if relatives:
            st.dataframe(
                [{"Route": k, "Price Relative": v, "Avg Live Fare (P_t)": f"₹{route_avgs[k]:,.2f}"} for k, v in relatives.items()],
                use_container_width=True, hide_index=True
            )
        else:
            st.info("No fare data available for selected filter.")

    with c2:
        st.subheader("⚖️ MoSPI Base Weights (W_0) & Reference Prices (P_0)")
        weights_summary = pd.merge(weights_df, base_prices_df, on="route_id")
        st.dataframe(weights_summary, use_container_width=True, hide_index=True)


# ===================================================================
# TAB 2: Knowledge Graph Network View (Separate Side Tab)
# ===================================================================
elif page_selection == "🕸️ Knowledge Graph Analytics":
    st.title("🕸️ Knowledge Graph Network Analytics")
    st.caption("Network centrality, transit hub connectivity, and graph-weighted airfare index")

    if kg_available:
        col_ctrl, col_view = st.columns([1, 2])

        with col_ctrl:
            st.markdown("### Hub Airport Selector")
            selected_hub = st.selectbox("Select Central Airport Node", ["DEL", "BOM", "BLR"])
            graph_data = get_graph_insights(selected_hub, filtered_df)

            st.metric(
                "Graph-Adjusted Index", 
                f"{graph_data['graph_adjusted_index']}",
                delta=f"{round(graph_data['graph_adjusted_index'] - 100.0, 2)}% vs Base"
            )
            
            st.metric("Hub Direct Routes Count", graph_data["active_route_count"])

            if graph_data["is_neo4j_live"]:
                st.success("🟢 Connected to Live Neo4j Graph Database")
            else:
                st.info("🟡 Running via Local Graph Engine (Neo4j Offline)")

        with col_view:
            st.markdown(f"### Outbound Route Connections for `{selected_hub}`")
            if graph_data["connections"]:
                routes_table = pd.DataFrame(graph_data["connections"])
                st.dataframe(routes_table, use_container_width=True, hide_index=True)
            else:
                st.warning("No connections mapped for this hub airport.")
    else:
        st.error("Knowledge Graph module (`kg_calculate_index.py`) not found in workspace.")


# ===================================================================
# TAB 3: Raw Scraped Data Logs
# ===================================================================
elif page_selection == "📂 Scraped Data Logs":
    st.title("📂 Scraped Raw Data Inspector")
    st.caption("View raw records stored in SQLite `live_fares` table and export CSVs")

    if not filtered_df.empty:
        st.dataframe(filtered_df, use_container_width=True, hide_index=True)

        csv_bytes = filtered_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Cleaned CSV",
            data=csv_bytes,
            file_name="scraped_live_fares.csv",
            mime="text/csv"
        )
    else:
        st.warning("No records found in database. Click 'Fetch Latest Live Fares' in the sidebar to scrape.")
