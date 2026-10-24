"""Synthetic time-series data-quality demonstration (not QuantEdge production code).

Run: python demo_time_series.py
     python demo_time_series.py --benchmark 250000
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
import math
import time
import tracemalloc
from statistics import mean


@dataclass(frozen=True)
class Reading:
    timestamp: datetime
    value: float | None


def _utc(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Every timestamp must be timezone-aware")
    return value.astimezone(timezone.utc)


def _same_value(a: object, b: object) -> bool:
    """Treat two NaNs as equivalent duplicate payloads, not as new conflicts."""
    if isinstance(a, float) and isinstance(b, float):
        if math.isnan(a) and math.isnan(b):
            return True
    return type(a) is type(b) and a == b


def _is_valid_value(value: object, min_valid: float | None) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    if not math.isfinite(value):
        return False
    return min_valid is None or value >= min_valid


def make_synthetic_readings() -> list[Reading]:
    """Twelve records with one gap, one exact duplicate and two bad values."""
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    readings: list[Reading] = []
    for index in range(12):
        if index == 5:
            continue
        value = None if index == 8 else (-2.0 if index == 10 else 100.0 + index)
        reading = Reading(start + timedelta(minutes=index * 5), value)
        readings.append(reading)
        if index == 3:
            readings.append(reading)
    return readings


def make_large_synthetic_readings(count: int) -> list[Reading]:
    """Create deterministic, strategy-free artificial observations."""
    if isinstance(count, bool) or not isinstance(count, int) or count <= 0:
        raise ValueError("count must be a positive integer")
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return [
        Reading(start + timedelta(minutes=i * 5), float(100 + (i % 50)))
        for i in range(count)
    ]


def validate_readings(
    readings: list[Reading],
    start: datetime,
    intervals: int,
    minutes: int = 5,
    min_valid: float | None = 0.0,
) -> dict[str, int | float | None]:
    """Report quality without mutating input; quarantine conflicting duplicates.

    A missing interval has no timestamp at all. A conflicting timestamp exists,
    but is excluded from valid statistics rather than arbitrarily choosing one.
    """
    start_utc = _utc(start)
    if (
        isinstance(intervals, bool) or not isinstance(intervals, int)
        or isinstance(minutes, bool) or not isinstance(minutes, int)
        or intervals <= 0 or minutes <= 0
    ):
        raise ValueError("intervals and minutes must be positive integers")
    if min_valid is not None and not _is_valid_value(min_valid, None):
        raise ValueError("min_valid must be finite and numeric, or None")

    expected = {start_utc + timedelta(minutes=minutes * i) for i in range(intervals)}
    first: dict[datetime, object] = {}
    conflicts: set[datetime] = set()
    duplicates = exact_duplicates = conflicting_duplicate_records = 0

    for reading in readings:
        stamp = _utc(reading.timestamp)
        if stamp in first:
            duplicates += 1
            if _same_value(first[stamp], reading.value):
                exact_duplicates += 1
            else:
                conflicting_duplicate_records += 1
                conflicts.add(stamp)
        else:
            first[stamp] = reading.value

    values: list[float] = []
    missing_values = invalid_values = outside_window = 0
    for stamp, value in first.items():
        if stamp not in expected:
            outside_window += 1
        elif stamp in conflicts:
            continue  # Deliberately quarantine all values at this timestamp.
        elif value is None:
            missing_values += 1
        elif not _is_valid_value(value, min_valid):
            invalid_values += 1
        else:
            values.append(float(value))

    return {
        "received_records": len(readings),
        "valid_records": len(values),
        "duplicate_records": duplicates,
        "exact_duplicate_records": exact_duplicates,
        "conflicting_duplicate_records": conflicting_duplicate_records,
        "conflicting_timestamps": len(conflicts & expected),
        "missing_intervals": len(expected - first.keys()),
        "missing_values": missing_values,
        "invalid_values": invalid_values,
        "outside_window": outside_window,
        "mean_valid_value": round(mean(values), 2) if values else None,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark", type=int, metavar="N", default=None,
                        help="Generate N deterministic synthetic records and measure validation")
    args = parser.parse_args()
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    if args.benchmark is None:
        print(json.dumps(validate_readings(make_synthetic_readings(), start, 12), indent=2))
    else:
        tracemalloc.start()
        readings = make_large_synthetic_readings(args.benchmark)
        start_time = time.perf_counter()
        report = validate_readings(readings, start, args.benchmark)
        seconds = time.perf_counter() - start_time
        _, peak_bytes = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        print(json.dumps({"synthetic": True, "validation_seconds": round(seconds, 3),
                          "peak_traced_mebibytes": round(peak_bytes / (1024 ** 2), 1),
                          "report": report}, indent=2))


if __name__ == "__main__":
    main()
