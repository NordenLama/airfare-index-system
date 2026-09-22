import os
import pandas as pd
from typing import List, Dict, Any, Tuple

try:
    from neo4j import GraphDatabase
    NEO4J_INSTALLED = True
except ImportError:
    GraphDatabase = None
    NEO4J_INSTALLED = False


class RouteKnowledgeGraph:
    """Knowledge Graph interface for mapping flight networks, transit hubs, and route connections."""
    def __init__(self, uri: str = "bolt://localhost:7687", auth: tuple = ("neo4j", "password")):
        self.driver = None
        if NEO4J_INSTALLED:
            try:
                # Add connection timeout (2 seconds max) so UI doesn't hang if database is offline
                self.driver = GraphDatabase.driver(
                    uri, 
                    auth=auth, 
                    connection_timeout=2.0,
                    max_connection_lifetime=5.0
                )
                # Verify active connection
                self.driver.verify_connectivity()
            except Exception:
                # Silent fallback to mock data mode if local Neo4j server isn't running
                self.driver = None

    def close(self):
        if self.driver:
            self.driver.close()

    def get_connected_routes_from_hub(self, hub_airport_code: str) -> List[Dict[str, Any]]:
        """Finds all downstream routes connected through a hub airport (e.g., DEL, BOM, BLR)."""
        if not self.driver:
            # Fallback mock graph structure if Neo4j is offline/unreachable
            mock_graph = {
                "DEL": [
                    {"origin": "DEL", "destination": "BOM", "airline": "IndiGo", "type": "DIRECT", "hub_importance": 0.45},
                    {"origin": "DEL", "destination": "BLR", "airline": "Air India", "type": "DIRECT", "hub_importance": 0.35},
                    {"origin": "DEL", "destination": "CCU", "airline": "SpiceJet", "type": "DIRECT", "hub_importance": 0.20}
                ],
                "BOM": [
                    {"origin": "BOM", "destination": "DEL", "airline": "IndiGo", "type": "DIRECT", "hub_importance": 0.40},
                    {"origin": "BOM", "destination": "MAA", "airline": "Vistara", "type": "DIRECT", "hub_importance": 0.35},
                    {"origin": "BOM", "destination": "BLR", "airline": "Akasa", "type": "DIRECT", "hub_importance": 0.25}
                ],
                "BLR": [
                    {"origin": "BLR", "destination": "DEL", "airline": "Air India", "type": "DIRECT", "hub_importance": 0.50},
                    {"origin": "BLR", "destination": "BOM", "airline": "IndiGo", "type": "DIRECT", "hub_importance": 0.30},
                    {"origin": "BLR", "destination": "HYD", "airline": "Alliance Air", "type": "DIRECT", "hub_importance": 0.20}
                ]
            }
            return mock_graph.get(hub_airport_code, mock_graph["DEL"])

        query = """
        MATCH (hub:Airport {code: $hub_code})-[r:HAS_ROUTE]->(dest:Airport)
        RETURN hub.code AS origin, dest.code AS destination, r.airline AS airline, coalesce(r.type, 'DIRECT') AS type
        """
        try:
            with self.driver.session() as session:
                result = session.run(query, hub_code=hub_airport_code)
                return [record.data() for record in result]
        except Exception:
            return []

    def compute_graph_adjusted_index(self, fares_df: pd.DataFrame, hub_code: str = "DEL") -> Tuple[float, Dict[str, float]]:
        """
        Calculates a Knowledge-Graph Adjusted Index based on centrality and hub importance.
        """
        if fares_df.empty:
            return 100.0, {}

        df = fares_df.copy()
        if 'route' not in df.columns and ('origin' in df.columns and 'destination' in df.columns):
            df['route'] = df['origin'] + "-" + df['destination']

        route_avgs = df.groupby('route')['price'].mean().to_dict()
        connections = self.get_connected_routes_from_hub(hub_code)
        
        if not connections:
            return 100.0, route_avgs

        # Base prices mapping fallback
        base_price_map = {"DEL-BOM": 4000.0, "DEL-BLR": 4800.0, "BOM-MAA": 3500.0, "DEL-CCU": 4200.0, "BLR-BOM": 3200.0}

        weighted_relatives = []
        graph_weights = []

        for conn in connections:
            route_str = f"{conn['origin']}-{conn['destination']}"
            current_p = route_avgs.get(route_str, base_price_map.get(route_str, 4000.0))
            base_p = base_price_map.get(route_str, current_p)
            
            # Graph weight calculated from network topology
            weight = conn.get("hub_importance", 0.33)
            
            price_rel = (current_p / base_p) * 100.0
            weighted_relatives.append(price_rel * weight)
            graph_weights.append(weight)

        total_w = sum(graph_weights)
        if total_w > 0:
            graph_index = sum(weighted_relatives) / total_w
        else:
            graph_index = 100.0

        return round(float(graph_index), 2), route_avgs


# Standard Singleton Interface
_kg_engine = RouteKnowledgeGraph()

def get_graph_insights(hub_code: str = "DEL", fares_df: pd.DataFrame = None) -> Dict[str, Any]:
    """Helper function called directly by Streamlit app.py"""
    connections = _kg_engine.get_connected_routes_from_hub(hub_code)
    
    if fares_df is not None and not fares_df.empty:
        graph_index, _ = _kg_engine.compute_graph_adjusted_index(fares_df, hub_code)
    else:
        graph_index = 100.0

    return {
        "hub": hub_code,
        "connections": connections,
        "active_route_count": len(connections),
        "graph_adjusted_index": graph_index,
        "is_neo4j_live": _kg_engine.driver is not None
    }