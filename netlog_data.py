"""Shared CSV validation and cleaning for Network Analyzer."""
from pathlib import Path
import pandas as pd

NUMERIC_COLS = ["speedtest_ping", "latency_min", "latency_avg", "latency_max", "jitter", "download", "upload"]


def load_clean(log_file: Path) -> pd.DataFrame:
    if not log_file.exists():
        raise FileNotFoundError(f"Log file does not exist: {log_file}")
    try:
        df = pd.read_csv(log_file)
    except pd.errors.EmptyDataError as error:
        raise ValueError("CSV is empty; collect at least one measurement first.") from error
    missing = set(["time", *NUMERIC_COLS]) - set(df.columns)
    if missing:
        raise ValueError("Missing CSV columns: " + ", ".join(sorted(missing)))
    total = len(df)
    df["time"] = pd.to_datetime(df["time"], errors="coerce")
    for col in NUMERIC_COLS:
        df[col] = pd.to_numeric(df[col], errors="coerce")
        df.loc[(df[col] < 0) | (df[col] == float("inf")), col] = float("nan")
    invalid_time = int(df["time"].isna().sum())
    failed = int((~((df["download"] > 0) & (df["upload"] > 0))).sum())
    # Earlier collectors used all-zero ping fields for failures. Keep genuine zero
    # jitter on successful pings, but do not average failed ping windows as 0 ms.
    ping_cols = ["latency_min", "latency_avg", "latency_max", "jitter"]
    df.loc[(df[ping_cols] == 0).all(axis=1), ping_cols] = float("nan")
    df = df.dropna(subset=["time"])
    df = df[(df["download"] > 0) & (df["upload"] > 0)].sort_values("time")
    df.attrs.update(total_rows=total, invalid_timestamps=invalid_time, failed_speedtests=failed)
    return df
