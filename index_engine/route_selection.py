from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import pandas as pd


@dataclass
class RecommendedRoute:
    route: str
    origin: str
    destination: str
    passenger_weight: float
    base_price: float
    priority: int


class RouteSelector:
    """Select recommended routes based on DGCA traffic data."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
    
    def get_recommended_routes(self) -> List[RecommendedRoute]:
        """Get recommended routes for the index."""
        return [
            RecommendedRoute(
                route="DEL-BOM",
                origin="DEL",
                destination="BOM",
                passenger_weight=0.45,
                base_price=4000.0,
                priority=1
            ),
            RecommendedRoute(
                route="DEL-BLR",
                origin="DEL",
                destination="BLR",
                passenger_weight=0.35,
                base_price=4800.0,
                priority=2
            ),
            RecommendedRoute(
                route="BOM-MAA",
                origin="BOM",
                destination="MAA",
                passenger_weight=0.20,
                base_price=3500.0,
                priority=3
            ),
        ]