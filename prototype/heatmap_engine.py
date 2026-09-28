import folium
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from folium.plugins import HeatMap

# Airport Geo-Coordinates (India Major Hubs)
AIRPORTS = {
    "DEL": {"name": "Delhi", "lat": 28.5562, "lon": 77.1000},
    "BOM": {"name": "Mumbai", "lat": 19.0896, "lon": 72.8656},
    "BLR": {"name": "Bengaluru", "lat": 12.9716, "lon": 77.5946},
    "CCU": {"name": "Kolkata", "lat": 22.6520, "lon": 88.4463},
    "HYD": {"name": "Hyderabad", "lat": 17.2403, "lon": 78.4294},
    "MAA": {"name": "Chennai", "lat": 12.9941, "lon": 80.1709},
    "PNQ": {"name": "Pune", "lat": 18.5822, "lon": 73.9197},
    "GOI": {"name": "Goa", "lat": 15.3808, "lon": 73.8314},
}


def create_curved_route(
    start_lat, start_lon, end_lat, end_lon, n_points=30, curvature=0.15
):
    """Calculates quadratic Bezier curve points between two coordinates for aesthetic arc lines."""
    mid_lat = (start_lat + end_lat) / 2 + (
        end_lon - start_lon
    ) * curvature  # Offset perpendicular
    mid_lon = (start_lon + end_lon) / 2 - (end_lat - start_lat) * curvature

    t = np.linspace(0, 1, n_points)
    lat_pts = (1 - t) ** 2 * start_lat + 2 * (1 - t) * t * mid_lat + t**2 * end_lat
    lon_pts = (1 - t) ** 2 * start_lon + 2 * (1 - t) * t * mid_lon + t**2 * end_lon

    return list(zip(lat_pts, lon_pts))


def generate_interactive_map(routes_df=None):
    """Render observed route fares as heat and corridor layers on a map."""
    m = folium.Map(
        location=[20.5937, 78.9629],
        zoom_start=5,
        tiles="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        attr='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    )

    if routes_df is None or routes_df.empty:
        return m._repr_html_()

    routes = routes_df.copy()
    if not {"origin", "destination"}.issubset(routes.columns):
        if {"origin_airport", "destination_airport"}.issubset(routes.columns):
            routes = routes.rename(columns={
                "origin_airport": "origin",
                "destination_airport": "destination",
            })
        elif "route_id" in routes.columns:
            parts = routes["route_id"].astype(str).str.split("-", n=1, expand=True)
            if parts.shape[1] == 2:
                routes["origin"] = parts[0]
                routes["destination"] = parts[1]
        elif "route" in routes.columns:
            parts = routes["route"].astype(str).str.split("-", n=1, expand=True)
            if parts.shape[1] == 2:
                routes["origin"] = parts[0]
                routes["destination"] = parts[1]

    fare_column = next(
        (column for column in ("price", "total_fare", "avg_fare") if column in routes.columns),
        None,
    )
    if fare_column is None or not {"origin", "destination"}.issubset(routes.columns):
        return m._repr_html_()

    routes["avg_fare"] = pd.to_numeric(routes[fare_column], errors="coerce")
    routes = routes.dropna(subset=["origin", "destination", "avg_fare"])
    routes = routes.groupby(["origin", "destination"], as_index=False)["avg_fare"].mean()
    routes_data = routes.to_dict(orient="records")
    if not routes_data:
        return m._repr_html_()

    fares = [route["avg_fare"] for route in routes_data]
    minimum_fare = min(fares)
    maximum_fare = max(fares)
    heat_data = []

    # 1. Draw Flight Arcs & Accumulate Heat Data
    for route in routes_data:
        src = AIRPORTS.get(str(route["origin"]).upper())
        dst = AIRPORTS.get(str(route["destination"]).upper())
        if not src or not dst:
            continue

        fare = route["avg_fare"]
        intensity = 0.5 if maximum_fare == minimum_fare else (
            fare - minimum_fare
        ) / (maximum_fare - minimum_fare)

        if intensity >= 0.75:
            color = "#e11d48"
        elif intensity >= 0.4:
            color = "#f97316"
        elif intensity >= 0.2:
            color = "#facc15"
        else:
            color = "#22c55e"

        # Generate curved flight arc
        curve_pts = create_curved_route(
            src["lat"], src["lon"], dst["lat"], dst["lon"]
        )

        # Add line arc to map
        folium.PolyLine(
            curve_pts,
            color=color,
            weight=2.5,
            opacity=0.75,
            tooltip=f"{route['origin']} ➔ {route['destination']} | Avg Fare: ₹{fare:,.0f}",
        ).add_to(m)

        # Populate points for background heat overlay
        for lat, lon in curve_pts:
            heat_data.append([lat, lon, 0.3 + 0.7 * intensity])

    # 2. Add Route Density Heatmap Layer
    HeatMap(
        heat_data,
        radius=18,
        blur=15,
        min_opacity=0.2,
        gradient={0.2: "#22c55e", 0.5: "#facc15", 0.8: "#f97316", 1: "#e11d48"},
    ).add_to(m)

    # 3. Add Custom Pulsing Airport Markers
    for code, info in AIRPORTS.items():
        html_marker = f"""
        <div style="
            background: rgba(244, 63, 94, 0.9);
            border: 2px solid #ffffff;
            border-radius: 50%;
            color: white;
            font-weight: bold;
            font-size: 10px;
            font-family: sans-serif;
            width: 28px;
            height: 28px;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 0 12px rgba(244, 63, 94, 0.8);
        ">
            {code}
        </div>
        """
        folium.Marker(
            location=[info["lat"], info["lon"]],
            icon=folium.DivIcon(
                icon_size=(28, 28),
                icon_anchor=(14, 14),
                html=html_marker,
            ),
            tooltip=f"{info['name']} ({code})",
        ).add_to(m)

    return m._repr_html_()


def generate_booking_horizon_matrix(matrix_data):
    """Generates a 2D Route x Booking Horizon Fare Heatmap using Plotly."""
    routes = list(matrix_data.keys())
    horizons = ["0-3 Days", "4-7 Days", "8-14 Days", "15-30 Days", "30+ Days"]

    z_values = [list(matrix_data[r].values()) for r in routes]

    fig = px.imshow(
        z_values,
        x=horizons,
        y=routes,
        labels=dict(
            x="Booking Horizon (Days ahead)", y="Route", color="Fare (₹)"
        ),
        color_continuous_scale="Reds",
        aspect="auto",
    )

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#e2e8f0", family="Times New Roman, serif"),
        margin=dict(l=40, r=40, t=30, b=40),
        xaxis=dict(gridcolor="#334155"),
        yaxis=dict(gridcolor="#334155"),
    )

    return fig.to_html(full_html=False, include_plotlyjs="cdn")