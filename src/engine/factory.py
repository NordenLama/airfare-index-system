from __future__ import annotations

from typing import Any, Dict, List, Optional

import pandas as pd

# Import the actual engine implementations
from index_engine import AirfarePriceIndex, AirfareAnalytics
from index_engine.volatility import VolatilityAnalyzer
from index_engine.route_analysis import RouteAnalyzer
from index_engine.route_selection import RouteSelector
from index_engine.data_quality import DataQualityEngine
from index_engine.news_context import NewsContextEngine


# Singleton instances
_index_engine: Optional[AirfarePriceIndex] = None
_analytics_engine: Optional[AirfareAnalytics] = None
_route_analytics_engine: Optional[RouteAnalyzer] = None
_quality_engine: Optional[DataQualityEngine] = None
_news_context_engine: Optional[NewsContextEngine] = None


def get_index_engine() -> AirfarePriceIndex:
    """Get or create the AirfarePriceIndex engine instance."""
    global _index_engine
    if _index_engine is None:
        from src.engine import data_access
        
        # Load base period data and weights
        weights_df, _ = data_access.build_weights([])
        base_prices_df, _ = data_access.get_base_prices()
        
        # Merge weights and base prices for the engine
        if not weights_df.empty and not base_prices_df.empty:
            engine_data = weights_df.merge(base_prices_df, on="route")
        else:
            engine_data = data_access._get_default_weights().merge(
                data_access._get_default_base_prices(), on="route"
            )
        
        _index_engine = AirfarePriceIndex(
            base_period="2024-01",
            weights=engine_data
        )
    return _index_engine


def get_analytics_engine() -> AirfareAnalytics:
    """Get or create the AirfareAnalytics engine instance."""
    global _analytics_engine
    if _analytics_engine is None:
        from src.engine import data_access
        
        weights_df, _ = data_access.build_weights([])
        base_prices_df, _ = data_access.get_base_prices()
        
        if not weights_df.empty and not base_prices_df.empty:
            engine_data = weights_df.merge(base_prices_df, on="route")
        else:
            engine_data = data_access._get_default_weights().merge(
                data_access._get_default_base_prices(), on="route"
            )
        
        _analytics_engine = AirfareAnalytics(
            base_period="2024-01",
            weights=engine_data
        )
    return _analytics_engine


def get_route_analytics_engine() -> RouteAnalyzer:
    """Get or create the RouteAnalyzer engine instance."""
    global _route_analytics_engine
    if _route_analytics_engine is None:
        from src.engine import data_access
        
        weights_df, _ = data_access.build_weights([])
        base_prices_df, _ = data_access.get_base_prices()
        
        if not weights_df.empty and not base_prices_df.empty:
            engine_data = weights_df.merge(base_prices_df, on="route")
        else:
            engine_data = data_access._get_default_weights().merge(
                data_access._get_default_base_prices(), on="route"
            )
        
        # Ensure normalized_weight column exists
        if "normalized_weight" not in engine_data.columns:
            total_weight = engine_data["weight"].sum()
            if total_weight > 0:
                engine_data["normalized_weight"] = engine_data["weight"] / total_weight
            else:
                engine_data["normalized_weight"] = 0.0
        
        _route_analytics_engine = RouteAnalyzer(
            base_period="2024-01",
            weights=engine_data
        )
    return _route_analytics_engine


def get_quality_engine() -> DataQualityEngine:
    """Get or create the DataQualityEngine instance."""
    global _quality_engine
    if _quality_engine is None:
        _quality_engine = DataQualityEngine()
    return _quality_engine


def get_news_context_engine() -> NewsContextEngine:
    """Get or create the NewsContextEngine instance."""
    global _news_context_engine
    if _news_context_engine is None:
        _news_context_engine = NewsContextEngine()
    return _news_context_engine


# For backwards compatibility
def reset_engines() -> None:
    """Reset all engine instances (useful for testing)."""
    global _index_engine, _analytics_engine, _route_analytics_engine, _quality_engine, _news_context_engine
    _index_engine = None
    _analytics_engine = None
    _route_analytics_engine = None
    _quality_engine = None
    _news_context_engine = None