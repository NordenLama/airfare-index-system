"""Demo-stable hybrid airfare surveillance scraper.

The default mock mode keeps the SIH prototype deterministic while preserving a
Playwright integration point for a real browser-backed extractor.
"""
from __future__ import annotations

import math
import random
from datetime import date, timedelta, datetime, timezone
from typing import Any

USE_MOCK_DATA = True

ROUTES: dict[str, dict[str, Any]] = {
    "DEL-BOM": {"distance_km": 1150, "daily_flights": 62, "base_fare": 6200},
    "DEL-BLR": {"distance_km": 1740, "daily_flights": 48, "base_fare": 5700},
    "BOM-BLR": {"distance_km": 840, "daily_flights": 56, "base_fare": 5100},
    "DEL-CCU": {"distance_km": 1305, "daily_flights": 44, "base_fare": 5300},
    "MAA-DEL": {"distance_km": 1760, "daily_flights": 42, "base_fare": 5000},
    "BLR-HYD": {"distance_km": 500, "daily_flights": 38, "base_fare": 3600},
}

CARRIERS = ("IndiGo", "Air India", "Akasa Air", "Vistara", "SpiceJet")


def _route_parts(route: str) -> tuple[str, str]:
    origin, destination = route.upper().split("-", 1)
    return origin, destination


def generate_mock_quotes(route: str) -> list[dict[str, Any]]:
    """Return deterministic, realistic demo quotes for a monitored route."""
    route = route.upper()
    config = ROUTES.get(route, ROUTES["DEL-BOM"])
    origin, destination = _route_parts(route if route in ROUTES else "DEL-BOM")
    seed = sum(ord(char) for char in route)
    rng = random.Random(seed)
    travel_date = date.today() + timedelta(days=7)
    quotes: list[dict[str, Any]] = []

    for index, airline in enumerate(CARRIERS):
        base_fare = round(config["base_fare"] * (0.92 + rng.random() * 0.2) + index * 85)
        fees = round(base_fare * (0.105 + rng.random() * 0.035))
        quotes.append({
            "airline": airline,
            "route": route,
            "travel_date": travel_date.isoformat(),
            "base_fare": base_fare,
            "total_fare": base_fare + fees,
            "surveillance_mode": "MockFareSource",
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "origin": origin,
            "destination": destination,
            "booking_lead_days": 7,
        })
    return quotes


def _extract_with_playwright(route: str) -> list[dict[str, Any]]:
    """Optional browser extraction hook.

    A production extractor can replace this method with selectors/API parsing.
    Returning an empty list deliberately activates the stable fallback path.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return []

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page()
            origin, destination = _route_parts(route)
            page.goto(
                f"https://www.google.com/travel/flights?q=Flights%20from%20{origin}%20to%20{destination}",
                wait_until="domcontentloaded",
                timeout=15000,
            )
            browser.close()
    except Exception:
        return []
    return []


def extract_live_fares(route: str) -> list[dict[str, Any]]:
    """Attempt Playwright extraction, falling back to stable mock quotes."""
    route = route.upper()
    if route not in ROUTES:
        raise ValueError(f"Unsupported route: {route}")
    if not USE_MOCK_DATA:
        live_quotes = _extract_with_playwright(route)
        if live_quotes:
            return live_quotes
    return generate_mock_quotes(route)
