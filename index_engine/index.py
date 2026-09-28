from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd


@dataclass
class IndexConfig:
    """Configuration for index calculation."""
    base_period: str
    representative_method: str = "median"
    trimmed_mean_proportion: float = 0.1
    outlier_method: str = "iqr"
    outlier_iqr_multiplier: float = 1.5
    fare_field: str = "total_fare"
    booking_horizon_filter: Optional[str] = None
    min_observations_per_route_period: int = 3
    aggregation_method: str = "arithmetic"


class InsufficientDataError(ValueError):
    """Raised when there is insufficient data for index calculation."""
    pass


@dataclass
class RouteIndexResult:
    """Result for a single route's index calculation."""
    route: str
    index: float
    mom: Optional[float] = None
    weight: float = 0.0
    contribution: float = 0.0
    data_source: str = "synthetic"


@dataclass
class IndexResult:
    """Complete index calculation result."""
    national_index: float
    mom: Optional[float]
    yoy: Optional[float]
    base_period: str
    current_period: str
    route_indices: List[RouteIndexResult]
    quality_score: Optional[float]
    flags: List[str]
    data_source: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TimeseriesPoint:
    """A single point in the index time series."""
    period: str
    index: float
    mom: Optional[float]
    yoy: Optional[float]
    data_source: str


class AirfarePriceIndex:
    """
    Laspeyres Price Index calculator for domestic airfares.
    
    The index uses DGCA passenger traffic weights (W_0) as base period weights
    and computes: I_t = sum((P_t / P_0) * W_0) / sum(W_0) * 100
    """
    
    def __init__(
        self,
        base_period: str,
        weights: Optional[pd.DataFrame] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the index engine.
        
        Args:
            base_period: Base period in YYYY-MM format
            weights: DataFrame with columns [route, origin, destination, weight, base_price]
            config: Optional configuration overrides
        """
        self.base_period = base_period
        self.config = config or {}
        
        # Default configuration
        self.representative_method = self.config.get("representative_method", "median")
        self.trimmed_mean_proportion = self.config.get("trimmed_mean_proportion", 0.1)
        self.outlier_method = self.config.get("outlier_method", "iqr")
        self.outlier_iqr_multiplier = self.config.get("outlier_iqr_multiplier", 1.5)
        self.min_observations_per_route_period = self.config.get("min_observations_per_route_period", 3)
        self.aggregation_method = self.config.get("aggregation_method", "arithmetic")
        
        # Initialize weights and base prices
        if weights is not None and not weights.empty:
            self.weights_df = weights.copy()
            # Ensure required columns
            if "normalized_weight" not in self.weights_df.columns:
                total_weight = self.weights_df["weight"].sum()
                if total_weight > 0:
                    self.weights_df["normalized_weight"] = self.weights_df["weight"] / total_weight
                else:
                    self.weights_df["normalized_weight"] = 0.0
        else:
            # Default weights based on DGCA passenger traffic
            self.weights_df = pd.DataFrame([
                {"route": "DEL-BOM", "origin": "DEL", "destination": "BOM", "weight": 0.45, "base_price": 4000.0, "normalized_weight": 0.45},
                {"route": "DEL-BLR", "origin": "DEL", "destination": "BLR", "weight": 0.35, "base_price": 4800.0, "normalized_weight": 0.35},
                {"route": "BOM-MAA", "origin": "BOM", "destination": "MAA", "weight": 0.20, "base_price": 3500.0, "normalized_weight": 0.20},
            ])
        
        # Cache for time series
        self._timeseries_cache: Dict[str, List[TimeseriesPoint]] = {}
    
    def _compute_representative_fare(self, fares: pd.Series) -> float:
        """Compute representative fare for a route-period using configured method."""
        if self.representative_method == "median":
            return float(fares.median())
        elif self.representative_method == "trimmed_mean":
            prop = self.trimmed_mean_proportion
            if prop > 0 and len(fares) > 2:
                n_trim = int(len(fares) * prop)
                sorted_fares = fares.sort_values()
                trimmed = sorted_fares.iloc[n_trim:-n_trim] if n_trim > 0 else sorted_fares
                return float(trimmed.mean())
            return float(fares.mean())
        else:
            return float(fares.mean())
    
    def _detect_outliers(self, fares: pd.Series) -> pd.Series:
        """Detect outliers using configured method."""
        if self.outlier_method == "iqr":
            Q1 = fares.quantile(0.25)
            Q3 = fares.quantile(0.75)
            IQR = Q3 - Q1
            multiplier = self.outlier_iqr_multiplier
            lower = Q1 - multiplier * IQR
            upper = Q3 + multiplier * IQR
            return (fares >= lower) & (fares <= upper)
        elif self.outlier_method == "zscore":
            z_scores = np.abs((fares - fares.mean()) / fares.std())
            return z_scores < 3
        else:
            return pd.Series(True, index=fares.index)
    
    def _aggregate_route_fares(self, df: pd.DataFrame) -> pd.DataFrame:
        """Aggregate fares by route and period."""
        # Group by route and period (YYYY-MM)
        df = df.copy()
        df["period"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m")
        
        # Filter outliers within each route-period group
        mask = df.groupby(["route", "period"])["fare"].transform(self._detect_outliers)
        df_clean = df[mask].copy()
        
        # Compute representative fare per route-period
        if self.aggregation_method == "arithmetic":
            agg_func = "mean"
        else:
            agg_func = "median"
        
        grouped = df_clean.groupby(["route", "period"]).agg(
            fare=("fare", self._compute_representative_fare),
            observations=("fare", "count")
        ).reset_index()
        
        return grouped
    
    def calculate_index(
        self,
        observations: List[Dict[str, Any]],
        base_period: str,
        current_period: str,
        config: Optional[Dict[str, Any]] = None
    ) -> IndexResult:
        """
        Calculate the composite airfare price index.
        
        Args:
            observations: List of fare observations with route, fare, date
            base_period: Base period in YYYY-MM format
            current_period: Current period in YYYY-MM format
            config: Optional config overrides
            
        Returns:
            IndexResult with national index, route breakdowns, etc.
        """
        if config:
            # Apply config overrides
            old_config = self.config
            self.config = {**self.config, **config}
        
        try:
            df = pd.DataFrame(observations)
            
            if df.empty:
                raise ValueError("No observations provided")
            
            # Ensure required columns
            if "route" not in df.columns:
                if "origin" in df.columns and "destination" in df.columns:
                    df["route"] = df["origin"] + "-" + df["destination"]
                else:
                    raise ValueError("Observations must have 'route' or 'origin'/'destination' columns")
            
            # Aggregate fares by route-period
            route_period_fares = self._aggregate_route_fares(df)
            
            # Get base and current period fares
            base_fares = route_period_fares[route_period_fares["period"] == base_period]
            current_fares = route_period_fares[route_period_fares["period"] == current_period]
            
            # Merge with weights
            merged = self.weights_df.merge(
                current_fares[["route", "fare"]].rename(columns={"fare": "current_fare"}),
                on="route",
                how="inner"
            )
            merged = merged.merge(
                base_fares[["route", "fare"]].rename(columns={"fare": "base_fare"}),
                on="route",
                how="inner"
            )
            
            if merged.empty:
                raise ValueError(f"No matching routes found between base ({base_period}) and current ({current_period}) periods")
            
            # Filter routes with sufficient observations
            min_obs = self.min_observations_per_route_period
            base_obs = route_period_fares[route_period_fares["period"] == base_period].set_index("route")["observations"]
            current_obs = route_period_fares[route_period_fares["period"] == current_period].set_index("route")["observations"]
            
            merged["base_obs"] = merged["route"].map(base_obs)
            merged["current_obs"] = merged["route"].map(current_obs)
            
            sufficient_data = (merged["base_obs"] >= min_obs) & (merged["current_obs"] >= min_obs)
            merged = merged[sufficient_data].copy()
            
            if merged.empty:
                raise ValueError(f"Insufficient observations (minimum {min_obs} per route-period)")
            
            # Calculate price relatives
            merged["price_relative"] = merged["current_fare"] / merged["base_fare"]
            
            # Laspeyres index: sum(price_relative * normalized_weight) * 100
            national_index = float((merged["price_relative"] * merged["normalized_weight"]).sum() * 100)
            
            # Route-level indices
            merged["route_index"] = merged["price_relative"] * 100
            merged["contribution"] = merged["price_relative"] * merged["normalized_weight"] * 100
            
            route_indices = []
            for _, row in merged.iterrows():
                route_indices.append(RouteIndexResult(
                    route=row["route"],
                    index=round(float(row["route_index"]), 2),
                    weight=round(float(row["normalized_weight"]), 6),
                    contribution=round(float(row["contribution"]), 4),
                    data_source="synthetic"  # Will be overridden by caller
                ))
            
            # MoM calculation (simplified - would need previous period)
            mom = None
            yoy = None
            
            # Quality score based on coverage
            routes_expected = len(self.weights_df)
            routes_covered = len(merged)
            coverage_rate = routes_covered / routes_expected if routes_expected > 0 else 0
            quality_score = coverage_rate
            
            flags = []
            if coverage_rate < 0.5:
                flags.append("low_coverage")
            if routes_covered < 3:
                flags.append("few_routes")
            
            # Determine data source
            data_sources = set()
            for obs in observations:
                data_sources.add(obs.get("source", "synthetic"))
            data_source = "real" if data_sources == {"real"} else "synthetic"
            
            return IndexResult(
                national_index=round(national_index, 2),
                mom=mom,
                yoy=yoy,
                base_period=base_period,
                current_period=current_period,
                route_indices=route_indices,
                quality_score=round(quality_score, 4),
                flags=flags,
                data_source=data_source,
                metadata={
                    "routes_expected": routes_expected,
                    "routes_covered": routes_covered,
                    "observations_used": int(merged["current_obs"].sum()),
                    "representative_method": self.representative_method,
                    "aggregation_method": self.aggregation_method,
                }
            )
        finally:
            if config:
                self.config = old_config
    
    def get_timeseries(
        self,
        start_date: str,
        end_date: str,
        observations: Optional[List[Dict[str, Any]]] = None
    ) -> List[TimeseriesPoint]:
        """Get index time series for a date range."""
        # If no observations provided, load from data access
        if observations is None:
            from src.engine import data_access
            observations, is_real = data_access.load_validated_observations()
        
        df = pd.DataFrame(observations)
        if df.empty:
            return []
        
        if "route" not in df.columns:
            if "origin" in df.columns and "destination" in df.columns:
                df["route"] = df["origin"] + "-" + df["destination"]
        
        # Generate periods
        periods = []
        current = start_date
        while current <= end_date:
            periods.append(current)
            # Increment month
            year, month = map(int, current.split("-"))
            month += 1
            if month > 12:
                month = 1
                year += 1
            current = f"{year:04d}-{month:02d}"
        
        points = []
        for period in periods:
            try:
                result = self.calculate_index(
                    observations=observations,
                    base_period=self.base_period,
                    current_period=period
                )
                points.append(TimeseriesPoint(
                    period=period,
                    index=result.national_index,
                    mom=result.mom,
                    yoy=result.yoy,
                    data_source=result.data_source
                ))
            except Exception:
                points.append(TimeseriesPoint(
                    period=period,
                    index=100.0,
                    mom=None,
                    yoy=None,
                    data_source="synthetic"
                ))
        
        return points
    
    def calculate_laspeyres_index(self, current_fares: pd.DataFrame, base_fares: pd.DataFrame) -> float:
        """Direct Laspeyres calculation for backward compatibility."""
        merged = base_fares.merge(current_fares, on="route", how="inner")
        if merged.empty:
            return 100.0
        
        merged["price_relative"] = merged["current_price"] / merged["base_price"]
        index = (merged["price_relative"] * merged["normalized_weight"]).sum() * 100
        return round(float(index), 2)