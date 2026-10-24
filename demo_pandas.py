"""Optional pandas view over the public synthetic dataset (no private inputs)."""

import json
import math

import pandas as pd

from demo_time_series import make_synthetic_readings


def summarize_with_pandas() -> dict[str, int]:
    readings = make_synthetic_readings()
    frame = pd.DataFrame(
        [{"timestamp": r.timestamp, "value": r.value} for r in readings]
    )
    # Preserve the raw 'value' column; diagnostics are derived, not destructive.
    frame["duplicate_timestamp"] = frame.duplicated("timestamp", keep=False)
    frame["missing_value"] = frame["value"].isna()
    frame["invalid_numeric"] = frame["value"].map(
        lambda v: pd.notna(v) and not (
            isinstance(v, (int, float)) and not isinstance(v, bool)
            and math.isfinite(v)
        )
    )
    frame["negative_value"] = frame["value"].map(
        lambda v: isinstance(v, (int, float)) and not isinstance(v, bool)
        and math.isfinite(v) and v < 0
    )
    return {
        "rows": len(frame),
        "duplicate_marked_rows": int(frame["duplicate_timestamp"].sum()),
        "missing_values": int(frame["missing_value"].sum()),
        "invalid_numeric_values": int(frame["invalid_numeric"].sum()),
        "negative_values": int(frame["negative_value"].sum()),
    }


if __name__ == "__main__":
    print(json.dumps(summarize_with_pandas(), indent=2))
