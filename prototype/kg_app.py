import os
import streamlit as st
import pandas as pd

# Import Standard Engine from calculate_index.py
try:
    from calculate_index import calculate_prototype_index
except ImportError:
    from prototype.calculate_index import calculate_prototype_index

# Import Knowledge Graph Engine from kg_calculate_index.py
try:
    from kg_calculate_index import calculate_kg_fare, KNOWLEDGE_GRAPH
except ImportError:
    from prototype.kg_calculate_index import calculate_kg_fare, KNOWLEDGE_GRAPH

st.set_page_config(page_title="Airfare Price Index System", layout="wide")

st.title("✈️ Airfare Price Index System — Unified Prototype")
st.markdown("---")

# Navigation Selector
engine_mode = st.sidebar.radio(
    "Select Calculation Engine",
    ["📊 Standard Laspeyres Index Engine", "🧠 Knowledge Graph Enriched Engine"]
)

if engine_mode == "📊 Standard Laspeyres Index Engine":
    st.header("Standard Airfare Price Index")
    st.caption("Calculates baseline price relatives using traditional economic index formulas.")
    
    # Run Standard Engine
    index_score, route_avgs, relatives, raw_df = calculate_prototype_index()
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Overall Index Score", f"{index_score}")
    col2.metric("Index Variation", f"{round(index_score - 100, 2)}%")
    col3.metric("Routes Tracked", f"{len(route_avgs)} Routes")
    
    st.markdown("---")
    
    col_left, col_right = st.columns([1, 1])
    with col_left:
        st.subheader("Route Price Relatives (Base = 100)")
        rel_df = pd.DataFrame(list(relatives.items()), columns=["Route", "Price Relative Index"])
        st.bar_chart(rel_df.set_index("Route"))
        
    with col_right:
        st.subheader("Underlying Fare Dataset")
        st.dataframe(raw_df, use_container_width=True)

else:
    st.header("Knowledge Graph Contextual Airfare Engine")
    st.caption("Dynamically adjusts price and buying intent based on urgency, stock health, quality, and risk protection.")
    
    # Sidebar Controls for Knowledge Graph Inputs
    st.sidebar.subheader("🕹️ KG Context Modifiers")
    selected_route = st.sidebar.selectbox("Flight Route", ["DEL-BOM", "DEL-BLR", "BOM-MAA"])
    base_prices = {"DEL-BOM": 4000, "DEL-BLR": 4800, "BOM-MAA": 3500}
    
    airline = st.sidebar.selectbox("Airline (Financial/Stock Context)", list(KNOWLEDGE_GRAPH["airline_financials"].keys()))
    lead_days = st.sidebar.slider("Booking Lead Time (Days to Departure)", 0, 30, 2)
    occasion = st.sidebar.selectbox("Occasion / Event Context", list(KNOWLEDGE_GRAPH["occasions"].keys()))
    quality = st.sidebar.selectbox("Service Quality Tier", list(KNOWLEDGE_GRAPH["quality_metrics"].keys()))
    insurance = st.sidebar.selectbox("Insurance & Flexibility Plan", list(KNOWLEDGE_GRAPH["protection_plans"].keys()))
    
    # Run KG Engine Calculation
    base_fare = base_prices[selected_route]
    kg_fare, buy_prob = calculate_kg_fare(base_fare, airline, lead_days, quality, insurance, occasion)
    
    # Display KG Metrics
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Baseline Fare", f"₹{base_fare}")
    c2.metric("KG Contextual Fare", f"₹{kg_fare}", f"{round(((kg_fare - base_fare)/base_fare)*100, 1)}%")
    c3.metric("Buying Intent Probability", f"{buy_prob}%")
    c4.metric("Urgency Level", "Critical / Emergency" if lead_days <= 2 else "Standard Booking")
    
    st.markdown("---")
    
    # Show Multiplier Breakdown
    st.subheader("📊 Knowledge Graph Influencer Multipliers")
    influencers = {
        "Occasion Surge": KNOWLEDGE_GRAPH["occasions"][occasion]["surge"],
        "Airline Financial Margin Pressure": KNOWLEDGE_GRAPH["airline_financials"][airline]["margin_pressure"],
        "Insurance Protection Markup": KNOWLEDGE_GRAPH["protection_plans"][insurance]["insurance_markup"],
        "Urgency Multiplier": 1.6 if lead_days <= 2 else (1.2 if lead_days <= 7 else 1.0)
    }
    st.bar_chart(pd.DataFrame(list(influencers.items()), columns=["Factor", "Multiplier"]).set_index("Factor"))