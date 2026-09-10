import streamlit as st
import pandas as pd
from calculate_index import calculate_prototype_index

# Set page configuration
st.set_page_config(page_title="Airfare Index Prototype", layout="wide")

st.title("✈️ Airfare Price Index System — Rapid Prototype")
st.markdown("---")

# Calculate statistical metrics using Member 3's function
overall_index, route_avgs, relatives = calculate_prototype_index("prototype/sample_fares.csv")

# 1. Top Metrics Display Cards
col1, col2, col3 = st.columns(3)
col1.metric("Current Airfare Index", f"{overall_index}", f"{round(overall_index - 100, 2)}%")
col2.metric("Monitored Routes", f"{len(route_avgs)} Routes")
col3.metric("System Status", "Live Prototype", "Active")

st.markdown("---")

# 2. Charts and Raw Data Tables
left_col, right_col = st.columns([1, 1])

with left_col:
    st.subheader("Route Price Relatives")
    rel_df = pd.DataFrame(list(relatives.items()), columns=["Route", "Price Relative Index"])
    st.bar_chart(rel_df.set_index("Route"))

with right_col:
    st.subheader("Raw Sample Observations")
    raw_df = pd.read_csv("prototype/sample_fares.csv")
    st.dataframe(raw_df, use_container_width=True)
