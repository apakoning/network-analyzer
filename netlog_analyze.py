#!/usr/bin/env python3
# =========================================================
# netlog_analyze.py
# =========================================================
#
# PURPOSE
# -------
# Read the CSV log and print a useful summary.
#
# DEFAULT INPUT
# -------------
# ~/.local/share/netlog/netlog.csv
#
# DESIGN GOAL
# -----------
# This file ONLY analyzes data.
# It does not collect data and does not plot graphs.
# =========================================================

import argparse
from pathlib import Path

import pandas as pd


DEFAULT_LOG_FILE = Path.home() / ".local" / "share" / "netlog" / "netlog.csv"


from netlog_data import load_clean


def print_summary(df: pd.DataFrame) -> None:
    """
    Print high-level summary stats.
    """
    if df.empty:
        print("No usable data.")
        return

    print("\n=== SUMMARY ===")
    print(f"Samples          : {len(df)}")
    print(f"First sample     : {df['time'].min()}")
    print(f"Last sample      : {df['time'].max()}")
    print(f"Avg download     : {df['download'].mean():.2f} Mbps")
    print(f"Avg upload       : {df['upload'].mean():.2f} Mbps")
    print(f"Best download    : {df['download'].max():.2f} Mbps")
    print(f"Best upload      : {df['upload'].max():.2f} Mbps")
    print(f"Worst download   : {df['download'].min():.2f} Mbps")
    print(f"Worst upload     : {df['upload'].min():.2f} Mbps")
    print(f"Avg latency      : {df['latency_avg'].mean():.2f} ms")
    print(f"Max latency      : {df['latency_max'].max():.2f} ms")
    print(f"Avg jitter       : {df['jitter'].mean():.2f} ms")
    print(f"Max jitter       : {df['jitter'].max():.2f} ms")

    print("\n=== PERCENTILES ===")
    print(f"95th latency avg : {df['latency_avg'].quantile(0.95):.2f} ms")
    print(f"95th latency max : {df['latency_max'].quantile(0.95):.2f} ms")
    print(f"95th jitter      : {df['jitter'].quantile(0.95):.2f} ms")
    print(f"5th download     : {df['download'].quantile(0.05):.2f} Mbps")
    print(f"5th upload       : {df['upload'].quantile(0.05):.2f} Mbps")


def print_problem_windows(df: pd.DataFrame) -> None:
    """
    Flag likely bad periods using simple percentile rules.

    This is not advanced anomaly detection.
    It is a practical first pass.
    """
    if df.empty:
        return

    print("\n=== POSSIBLE PROBLEM WINDOWS ===")

    high_latency_threshold = df["latency_max"].quantile(0.95)
    high_jitter_threshold = df["jitter"].quantile(0.95)
    low_download_threshold = df["download"].quantile(0.05)
    low_upload_threshold = df["upload"].quantile(0.05)

    bad = df[
        (df["latency_max"] > high_latency_threshold)
        | (df["jitter"] > high_jitter_threshold)
        | (df["download"] < low_download_threshold)
        | (df["upload"] < low_upload_threshold)
    ]

    if bad.empty:
        print("No major problem windows detected.")
        return

    for _, row in bad.tail(20).iterrows():
        print(
            f"{row['time']} | "
            f"down={row['download']:.2f} Mbps | "
            f"up={row['upload']:.2f} Mbps | "
            f"lat_avg={row['latency_avg']:.2f} ms | "
            f"lat_max={row['latency_max']:.2f} ms | "
            f"jitter={row['jitter']:.2f} ms"
        )


def print_hourly_summary(df: pd.DataFrame) -> None:
    """
    Show average network behavior by hour of day.
    """
    if df.empty:
        return

    print("\n=== HOURLY AVERAGES ===")

    hourly = df.copy()
    hourly["hour"] = hourly["time"].dt.hour

    grouped = hourly.groupby("hour").agg({
        "download": "mean",
        "upload": "mean",
        "latency_avg": "mean",
        "jitter": "mean",
    }).round(2)

    print(grouped.to_string())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze a netlog CSV file."
    )

    parser.add_argument(
        "--log-file",
        type=Path,
        default=DEFAULT_LOG_FILE,
        help=f"CSV log file path. Default: {DEFAULT_LOG_FILE}",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    log_file = args.log_file.expanduser()

    df = load_clean(log_file)

    print(f"Analyzing: {log_file}")
    print(f"CSV rows: {df.attrs['total_rows']} | failed speedtests: {df.attrs['failed_speedtests']} | invalid timestamps: {df.attrs['invalid_timestamps']}")
    print("Throughput summaries exclude failed speedtests; missing ping measurements are not zero latency.")
    print_summary(df)
    print_problem_windows(df)
    print_hourly_summary(df)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, pd.errors.ParserError) as error:
        raise SystemExit(str(error)) from error

