
"""Safe, synthetic time-series data-quality demonstration.

This file contains no market feeds, trading models, or private configuration.
Run with: python demo_time_series.py
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
import math
from statistics import mean


@dataclass(frozen=True)
class Reading:
    timestamp: datetime
    value: float | None


def make_synthetic_readings() -> list[Reading]:
    """Generate data with one gap, duplicate, missing value, and invalid value."""
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    readings = []
    for index in range(12):
        if index == 5:
            continue  # Simulate one missing five-minute interval.
        value = None if index == 8 else (-2.0 if index == 10 else 100.0 + index)
        reading = Reading(start + timedelta(minutes=5 * index), value)
        readings.append(reading)
        if index == 3:
            readings.append(reading)  # Simulate a duplicate record.
    return readings


def validate_readings(
    readings: list[Reading], start: datetime, intervals: int, minutes: int = 5
) -> dict[str, int | float | None]:
    """Summarize data quality without modifying source observations."""
    if start.tzinfo is None or intervals <= 0 or minutes <= 0:
        raise ValueError("Use a timezone-aware start and positive intervals/minutes")

    expected = {start + timedelta(minutes=minutes * i) for i in range(intervals)}
    seen = set()
    values = []
    duplicates = missing_values = invalid_values = outside_window = 0

    for reading in readings:
        if reading.timestamp in seen:
            duplicates += 1
            continue
        seen.add(reading.timestamp)
        if reading.timestamp not in expected:
            outside_window += 1
        elif reading.value is None:
            missing_values += 1
        elif (
            isinstance(reading.value, bool)
            or not isinstance(reading.value, (int, float))
            or not math.isfinite(reading.value)
            or reading.value < 0
        ):
            invalid_values += 1
        else:
            values.append(reading.value)

    return {
        "received_records": len(readings),
        "valid_records": len(values),
        "duplicate_records": duplicates,
        "missing_intervals": len(expected - seen),
        "missing_values": missing_values,
        "invalid_values": invalid_values,
        "outside_window": outside_window,
        "mean_valid_value": round(mean(values), 2) if values else None,
    }


def main() -> None:
    readings = make_synthetic_readings()
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    report = validate_readings(readings, start=start, intervals=12)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
