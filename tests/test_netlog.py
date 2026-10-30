import csv
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import netlog_collect as collector
from netlog_data import load_clean


class Measurements(unittest.TestCase):
    def test_speed_conversion_and_failure(self):
        with patch.object(collector.subprocess, "check_output", return_value='{"ping":{"latency":3},"download":{"bandwidth":50000000},"upload":{"bandwidth":25000000}}'):
            self.assertEqual(collector.run_speedtest(), ("3.00", "400.00", "200.00"))
        with patch.object(collector.subprocess, "check_output", side_effect=FileNotFoundError):
            self.assertEqual(collector.run_speedtest(), ("", "", ""))

    def test_ping_jitter_and_failure(self):
        with patch.object(collector.subprocess, "check_output", return_value="time=2.0 ms\ntime=6.0 ms\ntime=4.0 ms"):
            self.assertEqual(collector.run_ping_window("example.com", 1), ("2.00", "4.00", "6.00", "3.00"))
        with patch.object(collector.subprocess, "check_output", side_effect=FileNotFoundError):
            self.assertEqual(collector.run_ping_window("example.com", 1), ("", "", "", ""))

    def test_csv_initialization_and_incompatible_header(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)/"log.csv"
            path.touch()
            collector.ensure_log_file(path)
            with path.open() as stream:
                self.assertEqual(next(csv.reader(stream)), collector.CSV_HEADER)
            path.write_text("wrong,header\n")
            with self.assertRaises(ValueError):
                collector.ensure_log_file(path)

    def test_invalid_intervals(self):
        with patch.object(sys, "argv", ["netlog_collect.py", "--cycle-seconds", "0"]):
            with self.assertRaises(SystemExit) as caught:
                collector.parse_args()
            self.assertEqual(caught.exception.code, 2)

    def test_failed_rows_counted_and_ping_missing(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)/"log.csv"
            path.write_text(",".join(collector.CSV_HEADER)+"\n2026-10-30 12:00:00,2,0,0,0,0,100,100\n2026-10-30 12:01:00,,,,,,,\n")
            df = load_clean(path)
            self.assertEqual(len(df), 1)
            self.assertEqual(df.attrs["failed_speedtests"], 1)
            self.assertTrue(df["latency_avg"].isna().all())

    def test_missing_columns(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)/"log.csv"; path.write_text("time,download\n2026-10-30,100\n")
            with self.assertRaisesRegex(ValueError, "Missing CSV columns"):
                load_clean(path)

    def test_wrapper_does_not_stop_unrelated_pid(self):
        with tempfile.TemporaryDirectory() as d:
            state = Path(d)/"state"; state.mkdir()
            (state/"netlog_collect.pid").write_text(str(os.getpid()))
            env = {**os.environ, "NETLOG_DATA_DIR":d, "NETLOG_STATE_DIR":str(state)}
            script = Path(collector.__file__).with_name("netlog_watch.sh")
            result = subprocess.run(["bash",str(script),"stop"],env=env,capture_output=True,text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse((state/"netlog_collect.pid").exists())


if __name__ == "__main__":
    unittest.main()
