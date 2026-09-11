import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as bg

# Base API URL where FastAPI is running
API_BASE_URL = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="Airfare Price Index & Route Tracking",
    page_icon="✈️",
    layout="wide"
)

# Header Section
st.title("✈️ Indian Airfare Price Index & Route Analytics System")
st.markdown("""
This prototype monitors domestic aviation pricing trends, calculates the **Laspeyres Airfare Index**, 
detects **surge pricing anomalies**, and traverses **Knowledge Graph route connections**.
""")

st.divider()

# Sidebar for Quick Actions and Configuration
st.sidebar.header("⚙️ System Control")
api_status = "Unknown"

try:
    health_res = requests.get(f"{API_BASE_URL}/")
    if health_res.status_code == 200:
        st.sidebar.success("Backend API: Online 🟢")
    else:
        st.sidebar.error("Backend API: Error 🔴")
except Exception:
    st.sidebar.error("Backend API: Offline 🔴 (Start FastAPI on port 8000)")

st.sidebar.markdown("---")
st.sidebar.subheader("Index Calculation Simulator")

# Interactive Inputs for Index Simulation
p_del_bom = st.sidebar.number_input("DEL-BOM Current Price (₹)", value=5200, step=100)
p_blr_del = st.sidebar.number_input("BLR-DEL Current Price (₹)", value=5100, step=100)
p_bom_maa = st.sidebar.number_input("BOM-MAA Current Price (₹)", value=3900, step=100)
p_del_ccu = st.sidebar.number_input("DEL-CCU Current Price (₹)", value=4800, step=100)

if st.sidebar.button("Calculate Live Price Index", type="primary"):
    payload = {
        "prices": [
            {"route": "DEL-BOM", "current_price": float(p_del_bom)},
            {"route": "BLR-DEL", "current_price": float(p_blr_del)},
            {"route": "BOM-MAA", "current_price": float(p_bom_maa)},
            {"route": "DEL-CCU", "current_price": float(p_del_ccu)}
        ]
    }
    try:
        res = requests.post(f"{API_BASE_URL}/api/v1/calculate-index", json=payload)
        if res.status_code == 200:
            st.session_state["live_index"] = res.json()
        else:
            st.error("Failed to compute index from API.")
    except Exception as e:
        st.error(f"Error connecting to backend: {e}")


# Tabbed Interface Layout
tab1, tab2, tab3 = st.tabs(["📊 Price Index Timeline", "🚨 Surge Price Alerts", "🕸️ Knowledge Graph Topology"])

# ==========================================
# TAB 1: PRICE INDEX & TIMELINE ANALYTICS
# ==========================================
with tab1:
    st.subheader("National Domestic Airfare Price Index")
    
    col1, col2, col3 = st.columns(3)
    
    # Retrieve simulated live index or set default
    live_idx = st.session_state.get("live_index", {"airfare_price_index": 112.40, "status": "Moderate Inflation"})
    
    idx_val = live_idx.get("airfare_price_index", 112.40)
    idx_status = live_idx.get("status", "Normal")
    delta_val = round(idx_val - 100.0, 2)
    
    col1.metric(label="Current Airfare Index", value=f"{idx_val}", delta=f"{delta_val}% vs Base (100)")
    col2.metric(label="Market Condition", value=idx_status)
    col3.metric(label="Base Period Benchmark", value="100.00")
    
    st.markdown("### Historical Index Trend")
    
    # Mock historical timeline data
    historical_df = pd.DataFrame([
        {"Date": "2026-08-01", "Index": 98.2},
        {"Date": "2026-08-08", "Index": 101.5},
        {"Date": "2026-08-15", "Index": 104.0},
        {"Date": "2026-08-22", "Index": 102.8},
        {"Date": "2026-08-29", "Index": 108.6},
        {"Date": "2026-09-05", "Index": idx_val},
    ])
    
    fig_line = px.line(
        historical_df, 
        x="Date", 
        y="Index", 
        title="Weekly National Airfare Price Index Trend",
        markers=True,
        line_shape="spline"
    )
    fig_line.add_hline(y=100.0, line_dash="dash", line_color="gray", annotation_text="Baseline Reference (100.0)")
    fig_line.update_layout(yaxis_range=[80, 130])
    
    st.plotly_chart(fig_line, use_container_width=True)

# ==========================================
# TAB 2: SURGE ANOMALY DETECTION
# ==========================================
with tab2:
    st.subheader("Route Price Surge Detection")
    st.write("Identifies flight routes where current prices breach statistical upper bounds (+1.5 Standard Deviations).")
    
    std_threshold = st.slider("Select Surge Sensitivity Threshold (Std Dev)", min_value=1.0, max_value=3.0, value=1.5, step=0.1)
    
    try:
        surge_res = requests.get(f"{API_BASE_URL}/api/v1/surge-alerts?std_threshold={std_threshold}")
        if surge_res.status_code == 200:
            surge_data = surge_res.json()
            surges = surge_data.get("details", [])
            
            st.info(f"Total Surge Anomalies Detected: **{surge_data.get('surges_detected_count', 0)}**")
            
            if surges:
                surge_df = pd.DataFrame(surges)
                
                # Format Columns for Display
                surge_df = surge_df.rename(columns={
                    "route": "Route",
                    "latest_price": "Current Fare (₹)",
                    "mean_price": "Historical Mean (₹)",
                    "upper_bound": "Upper Bound Limit (₹)",
                    "surge_pct": "Surge Spike (%)"
                })
                
                st.dataframe(
                    surge_df[["Route", "Current Fare (₹)", "Historical Mean (₹)", "Upper Bound Limit (₹)", "Surge Spike (%)"]],
                    use_container_width=True
                )
                
                # Visualization Bar Chart for Surges
                fig_surge = px.bar(
                    surge_df, 
                    x="Route", 
                    y=["Historical Mean (₹)", "Current Fare (₹)"], 
                    barmode="group",
                    title="Price Surge Comparison vs Historical Route Average"
                )
                st.plotly_chart(fig_surge, use_container_width=True)
            else:
                st.success("No route price surges detected under current threshold settings.")
        else:
            st.error("Could not retrieve surge metrics from API.")
    except Exception as e:
        st.error(f"Error connecting to backend API: {e}")

# ==========================================
# TAB 3: KNOWLEDGE GRAPH TOPOLOGY
# ==========================================
with tab3:
    st.subheader("Route Knowledge Graph Connections")
    st.write("Explores downstream route dependencies and airline connectivity from major transit hub airports.")
    
    selected_hub = st.selectbox("Select Aviation Hub Airport", options=["DEL", "BOM", "BLR"])
    
    try:
        graph_res = requests.get(f"{API_BASE_URL}/api/v1/graph/hub-impact/{selected_hub}")
        if graph_res.status_code == 200:
            graph_data = graph_res.json()
            nodes = graph_data.get("network_nodes", [])
            
            st.write(f"Showing **{len(nodes)}** connected routes originating from transit hub **{selected_hub}**:")
            
            if nodes:
                nodes_df = pd.DataFrame(nodes)
                nodes_df = nodes_df.rename(columns={
                    "origin": "Origin Hub",
                    "destination": "Destination",
                    "airline": "Operating Airline",
                    "type": "Flight Type"
                })
                
                st.table(nodes_df[["Origin Hub", "Destination", "Operating Airline", "Flight Type"]])
            else:
                st.warning("No connected routes found for this hub.")
        else:
            st.error("Failed to query Knowledge Graph endpoint.")
    except Exception as e:
        st.error(f"Error connecting to graph backend: {e}")