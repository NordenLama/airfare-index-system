from __future__ import annotations


def shift_period(period: str, months: int) -> str:
    """
    Shift a YYYY-MM period by the given number of months.
    
    Args:
        period: Period string in YYYY-MM format
        months: Number of months to shift (positive or negative)
    
    Returns:
        Shifted period in YYYY-MM format
    """
    year, month = map(int, period.split("-"))
    month += months
    
    while month > 12:
        month -= 12
        year += 1
    while month < 1:
        month += 12
        year -= 1
    
    return f"{year:04d}-{month:02d}"


def period_range(start: str, end: str) -> list[str]:
    """Generate list of periods from start to end inclusive."""
    periods = []
    current = start
    while current <= end:
        periods.append(current)
        current = shift_period(current, 1)
    return periods