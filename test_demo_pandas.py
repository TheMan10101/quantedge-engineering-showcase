"""pytest tests for the pandas-specific synthetic demonstration."""

from demo_pandas import summarize_with_pandas


def test_pandas_row_and_duplicate_counts():
    report = summarize_with_pandas()
    assert report["rows"] == 12
    assert report["duplicate_marked_rows"] == 2


def test_pandas_missing_and_negative_counts():
    report = summarize_with_pandas()
    assert report["missing_values"] == 1
    assert report["negative_values"] == 1
    assert report["invalid_numeric_values"] == 0
