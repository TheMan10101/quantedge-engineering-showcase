"""Standard-library regression tests: python -m unittest discover -v"""

from datetime import datetime, timedelta, timezone
import unittest

from demo_time_series import (
    Reading, make_large_synthetic_readings, make_synthetic_readings,
    validate_readings,
)

START = datetime(2026, 1, 1, tzinfo=timezone.utc)


class TestTimeSeriesValidation(unittest.TestCase):
    def test_synthetic_report(self):
        report = validate_readings(make_synthetic_readings(), START, 12)
        self.assertEqual(report, {
            "received_records": 12, "valid_records": 9,
            "duplicate_records": 1, "exact_duplicate_records": 1,
            "conflicting_duplicate_records": 0, "conflicting_timestamps": 0,
            "missing_intervals": 1, "missing_values": 1, "invalid_values": 1,
            "outside_window": 0, "mean_valid_value": 104.78,
        })

    def test_clean_series(self):
        records = [Reading(START + timedelta(minutes=i*5), float(i)) for i in range(3)]
        report = validate_readings(records, START, 3)
        self.assertEqual(report["valid_records"], 3)
        self.assertEqual(report["missing_intervals"], 0)
        self.assertEqual(report["mean_valid_value"], 1.0)

    def test_exact_duplicate(self):
        report = validate_readings([Reading(START, 10.), Reading(START, 10.)], START, 1)
        self.assertEqual(report["exact_duplicate_records"], 1)
        self.assertEqual(report["valid_records"], 1)

    def test_conflicting_duplicate_is_quarantined(self):
        samples = [Reading(START, 10.), Reading(START, 20.)]
        report = validate_readings(samples, START, 1)
        self.assertEqual(report["conflicting_duplicate_records"], 1)
        self.assertEqual(report["conflicting_timestamps"], 1)
        self.assertEqual(report["valid_records"], 0)
        self.assertIsNone(report["mean_valid_value"])
        self.assertEqual(samples[0].value, 10.)  # Source data untouched.

    def test_conflict_counter_scopes(self):
        outside = START + timedelta(hours=1)
        report = validate_readings([
            Reading(START, 10.0),
            Reading(START, 11.0),
            Reading(outside, 20.0),
            Reading(outside, 21.0),
        ], START, intervals=1)
        self.assertEqual(report["conflicting_duplicate_records"], 2)
        self.assertEqual(report["conflicting_timestamps"], 1)
        self.assertEqual(report["outside_window"], 1)

    def test_conflict_with_none(self):
        report = validate_readings([Reading(START, None), Reading(START, 5.)], START, 1)
        self.assertEqual(report["conflicting_timestamps"], 1)
        self.assertEqual(report["missing_values"], 0)

    def test_missing_interval(self):
        records = [Reading(START, 1.), Reading(START + timedelta(minutes=10), 3.)]
        self.assertEqual(validate_readings(records, START, 3)["missing_intervals"], 1)

    def test_missing_value(self):
        report = validate_readings([Reading(START, None)], START, 1)
        self.assertEqual(report["missing_values"], 1)
        self.assertIsNone(report["mean_valid_value"])

    def test_invalid_values(self):
        bad = [-1., float("nan"), float("inf"), True, "5"]
        records = [Reading(START + timedelta(minutes=5*i), value) for i, value in enumerate(bad)]
        report = validate_readings(records, START, len(records))
        self.assertEqual(report["invalid_values"], 5)
        self.assertEqual(report["valid_records"], 0)

    def test_configurable_minimum_for_signed_sensors(self):
        samples = [Reading(START, -1.), Reading(START + timedelta(minutes=5), 2.)]
        report = validate_readings(samples, START, 2, min_valid=None)
        self.assertEqual(report["valid_records"], 2)
        self.assertEqual(report["mean_valid_value"], 0.5)
        report = validate_readings(samples, START, 2, min_valid=-1.)
        self.assertEqual(report["valid_records"], 2)

    def test_outside_window(self):
        records = [Reading(START, 10.), Reading(START + timedelta(hours=1), 900.)]
        report = validate_readings(records, START, 1)
        self.assertEqual(report["outside_window"], 1)
        self.assertEqual(report["mean_valid_value"], 10.)

    def test_empty_input(self):
        report = validate_readings([], START, 3)
        self.assertEqual(report["missing_intervals"], 3)
        self.assertIsNone(report["mean_valid_value"])

    def test_requires_timezone_aware_start(self):
        with self.assertRaises(ValueError):
            validate_readings([], datetime(2026, 1, 1), 1)

    def test_rejects_naive_reading(self):
        with self.assertRaises(ValueError):
            validate_readings([Reading(datetime(2026, 1, 1), 1.)], START, 1)

    def test_rejects_bad_configuration(self):
        for intervals, minutes in [(0, 5), (1, 0), (-1, 5), (1, -5), (True, 5)]:
            with self.subTest(intervals=intervals, minutes=minutes):
                with self.assertRaises(ValueError):
                    validate_readings([], START, intervals, minutes)
        for low in [float("nan"), True, "0"]:
            with self.subTest(low=low):
                with self.assertRaises(ValueError):
                    validate_readings([], START, 1, min_valid=low)

    def test_equivalent_timezone_offsets(self):
        other = START.astimezone(timezone(timedelta(hours=-6)))
        report = validate_readings([Reading(other, 7.)], START, 1)
        self.assertEqual(report["valid_records"], 1)

    def test_larger_synthetic_smoke(self):
        records = make_large_synthetic_readings(2000)
        report = validate_readings(records, START, 2000)
        self.assertEqual(report["valid_records"], 2000)
        self.assertEqual(report["missing_intervals"], 0)


if __name__ == "__main__":
    unittest.main()
