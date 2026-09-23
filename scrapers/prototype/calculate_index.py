import pandas as pd
import numpy as np
from typing import Dict, List, Any, Tuple

class AirfareIndexEngine:
    def __init__(self, base_period_data: pd.DataFrame):
        """
        Initializes engine with baseline reference prices and route weights.
        Expects columns: 'route', 'base_price', 'passenger_weight'
        """
        self.base_data = base_period_data.copy().set_index('route')
        # Normalize weights so they sum to 1.0
        self.base_data['normalized_weight'] = (
            self.base_data['passenger_weight'] / self.base_data['passenger_weight'].sum()
        )

    def calculate_laspeyres_index(self, current_period_data: pd.DataFrame) -> Tuple[float, Dict[str, float], Dict[str, float], pd.DataFrame]:
        """
        Calculates official Laspeyres Price Index and returns route-level metrics.
        """
        df = current_period_data.copy()

        # Build route column if missing
        if 'route' not in df.columns and ('origin' in df.columns and 'destination' in df.columns):
            df['route'] = df['origin'] + "-" + df['destination']

        if df.empty:
            return 100.0, {}, {}, df

        # Aggregate scraped fares to calculate average P_t per route
        route_avgs = df.groupby('route')['price'].mean().to_dict()
        
        curr = pd.DataFrame(list(route_avgs.items()), columns=['route', 'current_price']).set_index('route')
        
        # Merge baseline reference data with current live period
        merged = self.base_data.join(curr, how='inner')

        if merged.empty:
            return 100.0, route_avgs, {}, df

        # Price relative calculation: (P_t / P_0) * 100
        merged['price_relative'] = (merged['current_price'] / merged['base_price']) * 100.0
        
        # Laspeyres index calculation: sum( (P_t / P_0) * W_0 ) / sum(W_0)
        laspeyres_index = (merged['price_relative'] * merged['normalized_weight']).sum()
        
        relatives = merged['price_relative'].round(2).to_dict()
        
        return round(float(laspeyres_index), 2), route_avgs, relatives, df

    def detect_price_surges(self, historical_route_prices: pd.DataFrame, threshold_std: float = 2.0) -> List[Dict[str, Any]]:
        """Identifies routes where latest fare > mean + (threshold_std * std_dev)"""
        surges = []
        if historical_route_prices.empty:
            return surges

        df = historical_route_prices.copy()
        if 'route' not in df.columns and ('origin' in df.columns and 'destination' in df.columns):
            df['route'] = df['origin'] + "-" + df['destination']

        grouped = df.groupby('route')

        for route, group in grouped:
            prices = group['price']
            mean_price = prices.mean()
            std_price = prices.std() if len(prices) > 1 else 0.0
            latest_price = prices.iloc[-1]

            upper_bound = mean_price + (threshold_std * std_price)

            if latest_price > upper_bound and std_price > 0:
                surge_magnitude_pct = round(((latest_price - mean_price) / mean_price) * 100, 2)
                surges.append({
                    "route": route,
                    "latest_price": float(latest_price),
                    "mean_price": round(float(mean_price), 2),
                    "upper_bound": round(float(upper_bound), 2),
                    "surge_pct": surge_magnitude_pct,
                    "is_surge": True
                })

        return surges


# -------------------------------------------------------------------
# Streamlit Interface Wrapper
# -------------------------------------------------------------------
# Default MoSPI Reference Table for initial execution
DEFAULT_BASE_PERIOD = pd.DataFrame([
    {"route": "DEL-BOM", "base_price": 4000.0, "passenger_weight": 0.45},
    {"route": "DEL-BLR", "base_price": 4800.0, "passenger_weight": 0.35},
    {"route": "BOM-MAA", "base_price": 3500.0, "passenger_weight": 0.20}
])

_engine = AirfareIndexEngine(DEFAULT_BASE_PERIOD)

def calculate_prototype_index(data_input) -> Tuple[float, Dict[str, float], Dict[str, float], pd.DataFrame]:
    """Compatibility function called by Streamlit prototype/app.py"""
    if isinstance(data_input, pd.DataFrame):
        df = data_input.copy()
    else:
        df = pd.read_csv(data_input)
        
    return _engine.calculate_laspeyres_index(df)
