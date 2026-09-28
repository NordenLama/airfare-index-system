from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from index_engine.index import AirfarePriceIndex, IndexResult, RouteIndexResult


@dataclass
class RouteIndex:
    """Route-level index for a period."""
    route: str
    origin: str
    destination: str
    period: str
    base_period_fare: Optional[float]
    period_fare: Optional[float]
    route_index: Optional[float]
    observations_used: int
    weight_raw: Optional[float]
    weight_normalized: Optional[float]
    status: str


@dataclass
class RouteContribution:
    """Route's contribution to national index MoM change."""
    route: str
    weight_normalized: float
    route_index_current: Optional[float]
    route_index_previous: Optional[float]
    contribution_points: Optional[float]


@dataclass
class CleaningReport:
    """Data cleaning report."""
    total_input: int
    total_valid: int
    total_removed: int
    removed_by_reason: Dict[str, int]


@dataclass
class PriceIndex:
    """Full price index result."""
    base_period: str
    current_period: str
    national_index: Optional[float]
    mom_change_pct: Optional[float]
    yoy_change_pct: Optional[float]
    routes_covered: int
    routes_total: int
    observations_used: int
    coverage_rate: float
    observations_received: int
    observations_rejected: int
    outliers_flagged: int
    routes_expected: int
    routes_with_data: int
    representative_method: str
    aggregation_method: str
    route_indices: List[RouteIndex]
    route_contributions: List[RouteContribution]
    quality_flags: List[str]
    cleaning_report: CleaningReport
    traffic_weight_coverage: Optional[float] = None


@dataclass
class RouteVolatility:
    """Route-level volatility."""
    route: str
    period: str
    volatility: Optional[float]
    classification: str
    observations_used: int
    method: str


@dataclass
class BookingHorizonVolatility:
    """Volatility by booking horizon."""
    bucket: str
    volatility: Optional[float]
    classification: str
    observations_used: int


@dataclass
class VolatilityResult:
    """Volatility analysis result."""
    period: str
    method: str
    national_volatility: Optional[float]
    national_classification: str
    route_volatility: List[RouteVolatility]
    high_volatility_routes: List[str]
    low_volatility_routes: List[str]
    observations_used: int
    booking_horizon_volatility: List[BookingHorizonVolatility]


@dataclass
class RouteInflationRow:
    """Route inflation, importance and stability."""
    route: str
    origin: str
    destination: str
    current_index: Optional[float]
    mom_inflation_pct: Optional[float]
    yoy_inflation_pct: Optional[float]
    weight: Optional[float]
    traffic_weight: Optional[float]
    contribution: Optional[float]
    volatility: Optional[float]
    status: str


@dataclass
class RouteMapObject:
    """Route data for map visualization."""
    origin: str
    destination: str
    origin_lat: float
    origin_lon: float
    destination_lat: float
    destination_lon: float
    inflation_mom: Optional[float]
    inflation_yoy: Optional[float]
    volatility: Optional[float]
    traffic_weight: Optional[float]
    contribution: Optional[float]
    status: str


@dataclass
class AnalyticsResult:
    """Complete analytics result."""
    price_index: PriceIndex
    volatility: VolatilityResult
    route_inflation: List[RouteInflationRow]
    rankings: Dict[str, List[RouteInflationRow]]
    route_map_objects: List[RouteMapObject]
    traffic_weight_coverage: Optional[float]
    affordability: Optional[Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class AirfareAnalytics:
    """
    Full analytics engine for airfare price index.
    Computes national index, volatility, route inflation, rankings, and map data.
    """
    
    # Airport coordinates for map
    AIRPORT_COORDS = {
        "DEL": (28.5562, 77.1000),
        "BOM": (19.0896, 72.8656),
        "BLR": (13.1986, 77.7066),
        "MAA": (12.9941, 80.1809),
        "CCU": (22.6547, 88.4467),
        "HYD": (17.2403, 78.4294),
        "PNQ": (18.5821, 73.9197),
        "GOI": (15.4834, 73.8274),
        "COK": (10.1556, 76.4000),
        "AMD": (23.0772, 72.6347),
    }
    
    def __init__(
        self,
        base_period: str,
        weights: Optional[pd.DataFrame] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """Initialize analytics engine."""
        self.base_period = base_period
        self.config = config or {}
        self.index_engine = AirfarePriceIndex(base_period=base_period, weights=weights, config=config)
        self.traffic_weight_coverage: Optional[float] = None
    
    def _determine_route_status(
        self,
        route: str,
        base_fare: Optional[float],
        current_fare: Optional[float],
        observations: int
    ) -> str:
        """Determine route status."""
        if observations == 0:
            return "NO_BASE_DATA"
        if base_fare is None:
            return "NEW_ROUTE"
        if current_fare is None:
            return "DISCONTINUED"
        if observations < 3:
            return "INSUFFICIENT_DATA"
        return "OK"
    
    def _classify_volatility(self, vol: Optional[float]) -> str:
        """Classify volatility level."""
        if vol is None:
            return "INSUFFICIENT_DATA"
        if vol < 0.05:
            return "LOW"
        elif vol < 0.15:
            return "MODERATE"
        else:
            return "HIGH"
    
    def calculate(
        self,
        observations: pd.DataFrame,
        current_period: str
    ) -> AnalyticsResult:
        """Calculate full analytics result."""
        # Calculate price index
        obs_list = observations.to_dict(orient="records")
        index_result = self.index_engine.calculate_index(
            observations=obs_list,
            base_period=self.base_period,
            current_period=current_period
        )
        
        # Build route indices
        route_indices = []
        for ri in index_result.route_indices:
            # Find base fare
            base_fares = observations[
                (observations["route"] == ri.route) & 
                (pd.to_datetime(observations["date"]).dt.strftime("%Y-%m") == self.base_period)
            ]["fare"]
            current_fares = observations[
                (observations["route"] == ri.route) & 
                (pd.to_datetime(observations["date"]).dt.strftime("%Y-%m") == current_period)
            ]["fare"]
            
            base_fare = float(base_fares.median()) if not base_fares.empty else None
            current_fare = float(current_fares.median()) if not current_fares.empty else None
            obs_used = len(current_fares)
            
            # Get weight info
            weight_row = self.index_engine.weights_df[
                self.index_engine.weights_df["route"] == ri.route
            ]
            weight_raw = float(weight_row["weight"].iloc[0]) if not weight_row.empty else None
            weight_norm = float(weight_row["normalized_weight"].iloc[0]) if not weight_row.empty else None
            
            origin, dest = ri.route.split("-")
            status = self._determine_route_status(ri.route, base_fare, current_fare, obs_used)
            
            route_indices.append(RouteIndex(
                route=ri.route,
                origin=origin,
                destination=dest,
                period=current_period,
                base_period_fare=base_fare,
                period_fare=current_fare,
                route_index=ri.index,
                observations_used=obs_used,
                weight_raw=weight_raw,
                weight_normalized=weight_norm,
                status=status
            ))
        
        # Route contributions (simplified - would need previous period)
        route_contributions = []
        for ri in index_result.route_indices:
            route_contributions.append(RouteContribution(
                route=ri.route,
                weight_normalized=ri.weight,
                route_index_current=ri.index,
                route_index_previous=None,
                contribution_points=ri.contribution
            ))
        
        # Cleaning report (simplified)
        cleaning_report = CleaningReport(
            total_input=len(observations),
            total_valid=len(observations),
            total_removed=0,
            removed_by_reason={}
        )
        
        # Price index result
        price_index = PriceIndex(
            base_period=self.base_period,
            current_period=current_period,
            national_index=index_result.national_index,
            mom_change_pct=index_result.mom,
            yoy_change_pct=index_result.yoy,
            routes_covered=index_result.metadata.get("routes_covered", 0),
            routes_total=index_result.metadata.get("routes_expected", 0),
            observations_used=index_result.metadata.get("observations_used", 0),
            coverage_rate=index_result.quality_score or 0,
            observations_received=len(observations),
            observations_rejected=0,
            outliers_flagged=0,
            routes_expected=index_result.metadata.get("routes_expected", 0),
            routes_with_data=index_result.metadata.get("routes_covered", 0),
            representative_method=index_result.metadata.get("representative_method", "median"),
            aggregation_method=index_result.metadata.get("aggregation_method", "arithmetic"),
            route_indices=route_indices,
            route_contributions=route_contributions,
            quality_flags=index_result.flags,
            cleaning_report=cleaning_report,
            traffic_weight_coverage=self.traffic_weight_coverage
        )
        
        # Volatility analysis (simplified)
        volatility = self._calculate_volatility(observations, current_period)
        
        # Route inflation
        route_inflation = self._calculate_route_inflation(observations, current_period, route_indices)
        
        # Rankings
        rankings = self._calculate_rankings(route_inflation)
        
        # Route map objects
        route_map_objects = self._build_route_map_objects(route_inflation)
        
        return AnalyticsResult(
            price_index=price_index,
            volatility=volatility,
            route_inflation=route_inflation,
            rankings=rankings,
            route_map_objects=route_map_objects,
            traffic_weight_coverage=self.traffic_weight_coverage,
            affordability=None
        )
    
    def _calculate_volatility(
        self,
        observations: pd.DataFrame,
        current_period: str
    ) -> VolatilityResult:
        """Calculate volatility metrics."""
        # Simplified volatility calculation
        route_volatility = []
        high_vol_routes = []
        low_vol_routes = []
        
        for route in self.index_engine.weights_df["route"].unique():
            route_obs = observations[observations["route"] == route]
            if len(route_obs) < 3:
                route_volatility.append(RouteVolatility(
                    route=route,
                    period=current_period,
                    volatility=None,
                    classification="INSUFFICIENT_DATA",
                    observations_used=len(route_obs),
                    method="std_dev"
                ))
                continue
            
            fares = route_obs["fare"]
            cv = float(fares.std() / fares.mean()) if fares.mean() > 0 else None
            classification = self._classify_volatility(cv)
            
            route_volatility.append(RouteVolatility(
                route=route,
                period=current_period,
                volatility=cv,
                classification=classification,
                observations_used=len(route_obs),
                method="std_dev"
            ))
            
            if classification == "HIGH":
                high_vol_routes.append(route)
            elif classification == "LOW":
                low_vol_routes.append(route)
        
        # National volatility (weighted average)
        national_vol = None
        if route_volatility:
            weights = self.index_engine.weights_df.set_index("route")["normalized_weight"]
            vol_series = pd.Series({rv.route: rv.volatility for rv in route_volatility if rv.volatility is not None})
            if not vol_series.empty:
                national_vol = float((vol_series * weights).sum())
        
        # Booking horizon volatility
        horizon_volatility = []
        if "booking_lead_days" in observations.columns:
            for bucket_name, (min_d, max_d) in [
                ("0-3", (0, 3)),
                ("4-7", (4, 7)),
                ("8-14", (8, 14)),
                ("15-30", (15, 30)),
                ("31-60", (31, 60)),
                ("61+", (61, 999)),
            ]:
                bucket_obs = observations[
                    (observations["booking_lead_days"] >= min_d) & 
                    (observations["booking_lead_days"] <= max_d)
                ]
                if len(bucket_obs) >= 3:
                    cv = float(bucket_obs["fare"].std() / bucket_obs["fare"].mean())
                    horizon_volatility.append(BookingHorizonVolatility(
                        bucket=bucket_name,
                        volatility=cv,
                        classification=self._classify_volatility(cv),
                        observations_used=len(bucket_obs)
                    ))
                else:
                    horizon_volatility.append(BookingHorizonVolatility(
                        bucket=bucket_name,
                        volatility=None,
                        classification="INSUFFICIENT_DATA",
                        observations_used=len(bucket_obs)
                    ))
        
        return VolatilityResult(
            period=current_period,
            method="std_dev",
            national_volatility=national_vol,
            national_classification=self._classify_volatility(national_vol),
            route_volatility=route_volatility,
            high_volatility_routes=high_vol_routes,
            low_volatility_routes=low_vol_routes,
            observations_used=len(observations),
            booking_horizon_volatility=horizon_volatility
        )
    
    def _calculate_route_inflation(
        self,
        observations: pd.DataFrame,
        current_period: str,
        route_indices: List[RouteIndex]
    ) -> List[RouteInflationRow]:
        """Calculate route inflation metrics."""
        # Get previous period
        year, month = map(int, current_period.split("-"))
        month -= 1
        if month == 0:
            month = 12
            year -= 1
        prev_period = f"{year:04d}-{month:02d}"
        
        # Calculate previous period index (handle missing data gracefully)
        prev_indices = {}
        try:
            prev_result = self.index_engine.calculate_index(
                observations=observations.to_dict(orient="records"),
                base_period=self.base_period,
                current_period=prev_period
            )
            prev_indices = {ri.route: ri.index for ri in prev_result.route_indices}
        except ValueError:
            # No data for previous period - MoM will be None
            pass
        
        # Traffic weights (from DGCA)
        traffic_weights = {
            "DEL-BOM": 0.45, "DEL-BLR": 0.35, "BOM-MAA": 0.20,
        }
        
        route_inflation = []
        for ri in route_indices:
            current_idx = ri.route_index
            prev_idx = prev_indices.get(ri.route)
            
            mom_inflation = None
            if current_idx is not None and prev_idx is not None and prev_idx > 0:
                mom_inflation = round(((current_idx - prev_idx) / prev_idx) * 100, 2)
            
            yoy_inflation = None
            # YoY would need 12 months ago data
            
            route_inflation.append(RouteInflationRow(
                route=ri.route,
                origin=ri.origin,
                destination=ri.destination,
                current_index=current_idx,
                mom_inflation_pct=mom_inflation,
                yoy_inflation_pct=yoy_inflation,
                weight=ri.weight_normalized,
                traffic_weight=traffic_weights.get(ri.route),
                contribution=ri.route_index * ri.weight_normalized if ri.route_index and ri.weight_normalized else None,
                volatility=None,  # Would come from volatility analysis
                status=ri.status
            ))
        
        return route_inflation
    
    def _calculate_rankings(
        self,
        route_inflation: List[RouteInflationRow]
    ) -> Dict[str, List[RouteInflationRow]]:
        """Calculate route rankings."""
        rankings = {}
        
        # Filter valid entries
        valid = [r for r in route_inflation if r.mom_inflation_pct is not None]
        
        rankings["highest_mom_inflation"] = sorted(valid, key=lambda r: r.mom_inflation_pct or -999, reverse=True)[:5]
        rankings["lowest_mom_inflation"] = sorted(valid, key=lambda r: r.mom_inflation_pct or 999)[:5]
        rankings["highest_yoy_inflation"] = sorted(valid, key=lambda r: r.yoy_inflation_pct or -999, reverse=True)[:5]
        rankings["lowest_yoy_inflation"] = sorted(valid, key=lambda r: r.yoy_inflation_pct or 999)[:5]
        
        # Contribution rankings
        valid_contrib = [r for r in route_inflation if r.contribution is not None]
        rankings["largest_positive_contributors"] = sorted(valid_contrib, key=lambda r: r.contribution or -999, reverse=True)[:5]
        rankings["largest_negative_contributors"] = sorted(valid_contrib, key=lambda r: r.contribution or 999)[:5]
        
        # Traffic weight
        valid_traffic = [r for r in route_inflation if r.traffic_weight is not None]
        rankings["highest_traffic_weight"] = sorted(valid_traffic, key=lambda r: r.traffic_weight or -999, reverse=True)[:5]
        
        # Volatility
        valid_vol = [r for r in route_inflation if r.volatility is not None]
        rankings["highest_volatility"] = sorted(valid_vol, key=lambda r: r.volatility or -999, reverse=True)[:5]
        
        return rankings
    
    def _build_route_map_objects(
        self,
        route_inflation: List[RouteInflationRow]
    ) -> List[RouteMapObject]:
        """Build route objects for map visualization."""
        map_objects = []
        
        for ri in route_inflation:
            origin_coords = self.AIRPORT_COORDS.get(ri.origin, (0, 0))
            dest_coords = self.AIRPORT_COORDS.get(ri.destination, (0, 0))
            
            map_objects.append(RouteMapObject(
                origin=ri.origin,
                destination=ri.destination,
                origin_lat=origin_coords[0],
                origin_lon=origin_coords[1],
                destination_lat=dest_coords[0],
                destination_lon=dest_coords[1],
                inflation_mom=ri.mom_inflation_pct,
                inflation_yoy=ri.yoy_inflation_pct,
                volatility=ri.volatility,
                traffic_weight=ri.traffic_weight,
                contribution=ri.contribution,
                status=ri.status
            ))
        
        return map_objects
    
    def inflation_matrix(self, metric: str = "mom") -> pd.DataFrame:
        """Build origin-destination inflation matrix."""
        origins = sorted(self.AIRPORT_COORDS.keys())
        dests = sorted(self.AIRPORT_COORDS.keys())
        
        matrix = pd.DataFrame(index=origins, columns=dests, dtype=float)
        
        # This would be filled from actual route inflation data
        # For now, return empty matrix with NaN
        return matrix