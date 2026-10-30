#!/usr/bin/env python3
# =========================================================
# netlog_collect.py
# =========================================================
#
# PURPOSE
# -------
# Collect internet performance data continuously.
#
# OUTPUT
# ------
# Default CSV:
#   ~/.local/share/netlog/netlog.csv
#
# DESIGN GOAL
# -----------
# This file ONLY collects data.
# No plotting.
# No analysis.
#
# REQUIREMENTS
# ------------
# - ping
# - Official Ookla speedtest CLI:
#     https://www.speedtest.net/apps/cli
# =========================================================

import argparse
import csv
import json
import os
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path


DEFAULT_LOG_FILE = Path.home() / ".local" / "share" / "netlog" / "netlog.csv"
DEFAULT_CYCLE_SECONDS = 900
DEFAULT_PING_TARGET = "1.1.1.1"
DEFAULT_PING_WINDOW_SECONDS = 20


CSV_HEADER = [
    "time",
    "speedtest_ping",
    "latency_min",
    "latency_avg",
    "latency_max",
    "jitter",
    "download",
    "upload",
]


def ensure_log_file(log_file: Path) -> None:
    """
    Create the CSV file with a header if it does not exist yet.
    """
    log_file.parent.mkdir(parents=True, exist_ok=True)

    if not log_file.exists() or log_file.stat().st_size == 0:
        with log_file.open("w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(CSV_HEADER)
    else:
        with log_file.open(newline="") as f:
            if next(csv.reader(f), None) != CSV_HEADER:
                raise ValueError("Existing CSV has an incompatible header; choose a new --log-file.")


def extract_json_object(output: str) -> dict:
    """
    Extract the first JSON object from command output.

    The Ookla CLI normally prints clean JSON, but this function is defensive:
    if extra text appears before or after the JSON, it still tries to recover.
    """
    output = output.strip()

    if not output:
        raise RuntimeError("speedtest returned empty output")

    start = output.find("{")
    end = output.rfind("}")

    if start == -1 or end == -1 or end <= start:
        raise RuntimeError(f"speedtest returned non-JSON output: {output[:200]}")

    json_text = output[start : end + 1]
    return json.loads(json_text)


def run_speedtest() -> tuple[str, str, str]:
    """
    Run the official Ookla Speedtest CLI.

    Returns:
        speedtest_ping, download, upload

    Download and upload are returned in Mbps.
    On failure, returns empty fields.
    """
    try:
        result = subprocess.check_output(
            [
                "speedtest",
                "--format=json",
            ],
            timeout=90,
            stderr=subprocess.STDOUT,
            text=True,
        )

        data = extract_json_object(result)

        ping = f"{data['ping']['latency']:.2f}"

        # Ookla reports bandwidth in Bytes/sec.
        download = f"{data['download']['bandwidth'] * 8 / 1_000_000:.2f}"
        upload = f"{data['upload']['bandwidth'] * 8 / 1_000_000:.2f}"

        return ping, download, upload

    except Exception as err:
        print(f"WARNING: speedtest failed: {err}", flush=True)
        return "", "", ""


def run_ping_window(
    target: str,
    seconds: int,
) -> tuple[str, str, str, str]:
    """
    Run continuous ping sampling for a short window.

    Captures:
    - latency_min
    - latency_avg
    - latency_max
    - jitter

    Jitter here is defined as:
    average absolute difference between successive RTT samples.

    Returns formatted strings.
    On failure, returns empty fields.
    """
    try:
        result = subprocess.check_output(
            ["ping", "-n", "-i", "0.2", "-w", str(seconds), target],
            timeout=seconds + 5,
            env={**os.environ, "LC_ALL": "C"},
            stderr=subprocess.STDOUT,
            text=True,
        )

        rtts = []

        for line in result.splitlines():
            if "time=" in line:
                try:
                    part = line.split("time=")[1].split()[0]
                    rtts.append(float(part))
                except Exception:
                    pass

        if not rtts:
            return "", "", "", ""

        latency_min = min(rtts)
        latency_avg = sum(rtts) / len(rtts)
        latency_max = max(rtts)

        if len(rtts) > 1:
            diffs = [abs(rtts[i] - rtts[i - 1]) for i in range(1, len(rtts))]
            jitter = sum(diffs) / len(diffs)
        else:
            jitter = 0.0

        return (
            f"{latency_min:.2f}",
            f"{latency_avg:.2f}",
            f"{latency_max:.2f}",
            f"{jitter:.2f}",
        )

    except Exception as err:
        print(f"WARNING: ping failed: {err}", flush=True)
        return "", "", "", ""


def collect_once(
    log_file: Path,
    ping_target: str,
    ping_window_seconds: int,
) -> None:
    """
    Perform one full measurement cycle:
    1. Run ping window for latency/jitter
    2. Run speedtest for throughput
    3. Append one CSV row
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    latency_min, latency_avg, latency_max, jitter = run_ping_window(
        target=ping_target,
        seconds=ping_window_seconds,
    )

    speedtest_ping, download, upload = run_speedtest()

    with log_file.open("a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                timestamp,
                speedtest_ping,
                latency_min,
                latency_avg,
                latency_max,
                jitter,
                download,
                upload,
            ]
        )

    print(
        f"[{timestamp}] "
        f"st_ping={speedtest_ping} ms | "
        f"lat(min/avg/max)={latency_min}/{latency_avg}/{latency_max} ms | "
        f"jitter={jitter} ms | "
        f"down={download} Mbps | up={upload} Mbps",
        flush=True,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect internet performance data into a CSV log."
    )

    parser.add_argument(
        "--log-file",
        type=Path,
        default=DEFAULT_LOG_FILE,
        help=f"CSV log file path. Default: {DEFAULT_LOG_FILE}",
    )

    parser.add_argument(
        "--cycle-seconds",
        type=int,
        default=DEFAULT_CYCLE_SECONDS,
        help=f"Seconds between collection cycles. Default: {DEFAULT_CYCLE_SECONDS}",
    )

    parser.add_argument(
        "--ping-target",
        default=DEFAULT_PING_TARGET,
        help=f"Ping target for latency/jitter checks. Default: {DEFAULT_PING_TARGET}",
    )

    parser.add_argument(
        "--ping-window",
        type=int,
        default=DEFAULT_PING_WINDOW_SECONDS,
        help=f"Seconds to sample ping traffic per cycle. Default: {DEFAULT_PING_WINDOW_SECONDS}",
    )

    parser.add_argument(
        "--once",
        action="store_true",
        help="Run one measurement cycle and exit.",
    )

    args = parser.parse_args()
    if args.cycle_seconds <= 0 or args.ping_window <= 0:
        parser.error("--cycle-seconds and --ping-window must be positive")
    return args


def main() -> None:
    args = parse_args()
    log_file = args.log_file.expanduser()

    for command in ("ping", "speedtest"):
        if shutil.which(command) is None:
            raise RuntimeError(f"Required command not found: {command}")
    ensure_log_file(log_file)

    print("Starting collector...", flush=True)
    print(f"Logging to: {log_file}", flush=True)
    print(f"Ping target: {args.ping_target}", flush=True)
    print(f"Cycle seconds: {args.cycle_seconds}", flush=True)

    if args.once:
        collect_once(log_file, args.ping_target, args.ping_window)
        return

    while True:
        cycle_start = time.monotonic()

        collect_once(log_file, args.ping_target, args.ping_window)

        elapsed = time.monotonic() - cycle_start
        sleep_for = max(1, int(args.cycle_seconds - elapsed))
        time.sleep(sleep_for)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCollector stopped.", flush=True)
    except (OSError, ValueError, RuntimeError) as error:
        raise SystemExit(str(error)) from error

