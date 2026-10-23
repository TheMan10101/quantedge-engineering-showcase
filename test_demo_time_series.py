
"""Unit tests for the synthetic time-series demonstration.

Run: python -m unittest discover -v
"""

from datetime import datetime, timedelta, timezone
import unittest

from demo_time_series import (
    Reading,
    make_synthetic_readings,
    validate_readings,
)

START = datetime(2026, 1, 1, tzinfo=timezone.utc)


class TestTimeSeriesValidation(unittest.TestCase):

    def test_full_synthetic_report(self):
        result = validate_readings(
            make_synthetic_readings(), START, intervals=12
        )
        self.assertEqual(result, {
            "received_records": 12,
            "valid_records": 9,
            "duplicate_records": 1,
            "missing_intervals": 1,
            "missing_values": 1,
            "invalid_values": 1,
            "outside_window": 0,
            "mean_valid_value": 104.78,
        })

    def test_clean_regular_series(self):
        readings = [
            Reading(START + timedelta(minutes=5 * i), float(i))
            for i in range(3)
        ]
        result = validate_readings(readings, START, intervals=3)
        self.assertEqual(result["valid_records"], 3)
        self.assertEqual(result["missing_intervals"], 0)
        self.assertEqual(result["duplicate_records"], 0)
        self.assertEqual(result["mean_valid_value"], 1.0)

    def test_duplicate_timestamp_is_counted_once(self):
        readings = [
            Reading(START, 10.0),
            Reading(START, 20.0),
        ]
        result = validate_readings(readings, START, intervals=1)
        self.assertEqual(result["duplicate_records"], 1)
        self.assertEqual(result["valid_records"], 1)
        self.assertEqual(result["mean_valid_value"], 10.0)

    def test_missing_interval(self):
        readings = [
            Reading(START, 1.0),
            Reading(START + timedelta(minutes=10), 3.0),
        ]
        result = validate_readings(readings, START, intervals=3)
        self.assertEqual(result["missing_intervals"], 1)

    def test_missing_value(self):
        result = validate_readings(
            [Reading(START, None)], START, intervals=1
        )
        self.assertEqual(result["missing_values"], 1)
        self.assertEqual(result["valid_records"], 0)
        self.assertIsNone(result["mean_valid_value"])

    def test_invalid_values(self):
        bad_values = (
            -1.0, float("nan"), float("inf"), True, "5"
        )
        readings = [
            Reading(START + timedelta(minutes=5 * i), value)
            for i, value in enumerate(bad_values)
        ]
        result = validate_readings(
            readings, START, intervals=len(readings)
        )
        self.assertEqual(
            result["invalid_values"], len(bad_values)
        )
        self.assertEqual(result["valid_records"], 0)

    def test_outside_window_is_not_included_in_mean(self):
        readings = [
            Reading(START, 10.0),
            Reading(START + timedelta(hours=1), 500.0),
        ]
        result = validate_readings(readings, START, intervals=1)
        self.assertEqual(result["outside_window"], 1)
        self.assertEqual(result["valid_records"], 1)
        self.assertEqual(result["mean_valid_value"], 10.0)

    def test_empty_input(self):
        result = validate_readings([], START, intervals=3)
        self.assertEqual(result["received_records"], 0)
        self.assertEqual(result["missing_intervals"], 3)
        self.assertIsNone(result["mean_valid_value"])

    def test_requires_timezone_aware_start(self):
        with self.assertRaises(ValueError):
            validate_readings(
                [], datetime(2026, 1, 1), intervals=1
            )

    def test_rejects_nonpositive_intervals_and_minutes(self):
        for intervals, minutes in (
            (0, 5), (1, 0), (-1, 5), (1, -5)
        ):
            with self.subTest(
                intervals=intervals, minutes=minutes
            ):
                with self.assertRaises(ValueError):
                    validate_readings(
                        [], START,
                        intervals=intervals,
                        minutes=minutes,
                    )


if __name__ == "__main__":
    unittest.main()
