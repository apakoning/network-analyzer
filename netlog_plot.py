#!/usr/bin/env python3
# =========================================================
# netlog_plot.py
# =========================================================
#
# PURPOSE
# -------
# Read the CSV log and generate graph PNG files.
#
# DEFAULT INPUT
# -------------
# ~/.local/share/netlog/netlog.csv
#
# DEFAULT OUTPUT
# --------------
# ~/.local/share/netlog/netlog_speed.png
# ~/.local/share/netlog/netlog_latency.png
#
# DESIGN GOAL
# -----------
# This file ONLY plots data.
# It does not collect or analyze.
# =========================================================

import argparse
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt


DEFAULT_DATA_DIR = Path.home() / ".local" / "share" / "netlog"
DEFAULT_LOG_FILE = DEFAULT_DATA_DIR / "netlog.csv"
DEFAULT_SPEED_GRAPH = DEFAULT_DATA_DIR / "netlog_speed.png"
DEFAULT_LATENCY_GRAPH = DEFAULT_DATA_DIR / "netlog_latency.png"


from netlog_data import load_clean


def plot_speed(df: pd.DataFrame, output_file: Path) -> None:
    """
    Plot download/upload speed.
    """
    output_file.parent.mkdir(parents=True, exist_ok=True)

    plt.figure(figsize=(15, 6))
    plt.plot(df["time"], df["download"], label="Download (Mbps)")
    plt.plot(df["time"], df["upload"], label="Upload (Mbps)")
    plt.legend()
    plt.xlabel("Time")
    plt.ylabel("Speed (Mbps)")
    plt.title("Internet Throughput Over Time")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(output_file)

    print(f"Speed graph written to: {output_file}")


def plot_latency(df: pd.DataFrame, output_file: Path) -> None:
    """
    Plot latency and jitter separately from throughput.

    This avoids hiding low millisecond values under large Mbps values.
    """
    output_file.parent.mkdir(parents=True, exist_ok=True)

    plt.figure(figsize=(15, 6))
    plt.plot(df["time"], df["latency_avg"], label="Latency Avg (ms)")
    plt.plot(df["time"], df["latency_max"], label="Latency Max (ms)")
    plt.plot(df["time"], df["jitter"], label="Jitter (ms)")
    plt.legend()
    plt.xlabel("Time")
    plt.ylabel("Milliseconds")
    plt.title("Latency and Jitter Over Time")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(output_file)

    print(f"Latency graph written to: {output_file}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate graphs from a netlog CSV file."
    )

    parser.add_argument(
        "--log-file",
        type=Path,
        default=DEFAULT_LOG_FILE,
        help=f"CSV log file path. Default: {DEFAULT_LOG_FILE}",
    )

    parser.add_argument(
        "--speed-graph",
        type=Path,
        default=DEFAULT_SPEED_GRAPH,
        help=f"Speed graph output path. Default: {DEFAULT_SPEED_GRAPH}",
    )

    parser.add_argument(
        "--latency-graph",
        type=Path,
        default=DEFAULT_LATENCY_GRAPH,
        help=f"Latency graph output path. Default: {DEFAULT_LATENCY_GRAPH}",
    )

    parser.add_argument(
        "--show",
        action="store_true",
        help="Show graphs interactively after saving.",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    log_file = args.log_file.expanduser()
    speed_graph = args.speed_graph.expanduser()
    latency_graph = args.latency_graph.expanduser()

    df = load_clean(log_file)

    if df.empty:
        print("No usable data to plot.")
        return

    plot_speed(df, speed_graph)
    plot_latency(df, latency_graph)

    if args.show:
        plt.show()
    plt.close("all")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, pd.errors.ParserError) as error:
        raise SystemExit(str(error)) from error

