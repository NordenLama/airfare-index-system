from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import pandas as pd


@dataclass
class RouteAnalysisResult:
    """Result of route analysis."""
    route: str
    route_index: float
    mom: Optional[float]
    weight: float
    contribution: float
    traffic_coverage: float
    status: str
    data_source: str


class RouteAnalyzer:
    """Analyze individual route performance."""
    
    def __init__(
        self,
        base_period: str,
        weights: Optional[pd.DataFrame] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        self.base_period = base_period
        self.config = config or {}
        
        if weights is not None and not weights.empty:
            self.weights_df = weights.copy()
        else:
            self.weights_df = pd.DataFrame([
                {"route": "DEL-BOM", "origin": "DEL", "destination": "BOM", "weight": 0.45, "base_price": 4000.0, "normalized_weight": 0.45},
                {"route": "DEL-BLR", "origin": "DEL", "destination": "BLR", "weight": 0.35, "base_price": 4800.0, "normalized_weight": 0.35},
                {"route": "BOM-MAA", "origin": "BOM", "destination": "MAA", "weight": 0.20, "base_price": 3500.0, "normalized_weight": 0.20},
            ])
    
    def get_route_analysis(self) -> List[RouteAnalysisResult]:
        """Get analysis for all routes."""
        results = []
        
        for _, row in self.weights_df.iterrows():
            route = row["route"]
            
            # Simulate index calculation
            import random
            route_index = round(100 + random.uniform(-15, 25), 1)
            mom = round(random.uniform(-5, 8), 1)
            weight = float(row["normalized_weight"])
            contribution = round(route_index * weight / 100, 2)
            traffic_coverage = round(random.uniform(0.7, 0.95), 2)
            
            results.append(RouteAnalysisResult(
                route=route,
                route_index=route_index,
                mom=mom,
                weight=weight,
                contribution=contribution,
                traffic_coverage=traffic_coverage,
                status="active",
                data_source="synthetic"
            ))
        
        return results