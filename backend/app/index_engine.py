import pandas as pd
import numpy as np
from typing import Dict, List, Any

class AirfareIndexEngine:
    def __init__(self, base_period_data: pd.DataFrame):
        self.base_data = base_period_data.set_index('route')
        self.base_data['normalized_weight'] = (
            self.base_data['passenger_weight'] / self.base_data['passenger_weight'].sum()
        )

    def calculate_laspeyres_index(self, current_period_data: pd.DataFrame) -> float:
        # Laspeyres Price Index Calculation
        curr = current_period_data.set_index('route')
        merged = self.base_data.join(curr[['current_price']], how='inner')
        
        if merged.empty:
            raise ValueError("No matching routes found between base and current period.")

        # Price relative calculation
        merged['price_relative'] = merged['current_price'] / merged['base_price']
        
        # Weighted index calculation
        laspeyres_index = (merged['price_relative'] * merged['normalized_weight']).sum() * 100
        return round(float(laspeyres_index), 2)

    def detect_price_surges(self, historical_route_prices: pd.DataFrame, threshold_std: float = 2.0) -> List[Dict[str, Any]]:
        # Identifies routes where current price > mean + (threshold_std * std_dev)
        surges = []
        grouped = historical_route_prices.groupby('route')

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