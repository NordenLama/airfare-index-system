from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class NewsEvent:
    headline: str
    source: str
    publication_date: str
    url: Optional[str]
    relevance_score: float
    data_source: str


@dataclass
class RouteContextResult:
    route: str
    significant_movement: bool
    movement_direction: Optional[str]
    movement_pct: Optional[float]
    events: List[NewsEvent]
    data_source: str


class NewsContextEngine:
    """Fetch news context for routes."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
    
    async def get_route_context(self, route_code: str) -> RouteContextResult:
        """Get news context for a route."""
        # Return mock data for now
        return RouteContextResult(
            route=route_code,
            significant_movement=False,
            movement_direction=None,
            movement_pct=None,
            events=[],
            data_source="synthetic"
        )