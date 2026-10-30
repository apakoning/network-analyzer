# Usage examples

Run commands from the repository with its virtual environment activated. `bash netlog_watch.sh --help` lists wrapper actions; each Python script supports `--help`.

## Custom collection interval and target

```bash
python netlog_collect.py --once --ping-target 9.9.9.9 --ping-window 10
bash netlog_watch.sh start --cycle-seconds 1800 --ping-target 9.9.9.9
```

Options after `start` are passed to the collector. Intervals and ping windows must be positive integers. A long-running speed test may exceed the requested interval.

## Custom data directory

Keep the same environment for start, analysis, plotting and stop:

```bash
export NETLOG_DATA_DIR="$HOME/network-tests"
export NETLOG_STATE_DIR="$HOME/.local/state/network-tests"
export NETLOG_PYTHON="$PWD/.venv/bin/python"
bash netlog_watch.sh start
bash netlog_watch.sh analyze
MPLBACKEND=Agg bash netlog_watch.sh plot
bash netlog_watch.sh stop
```

The generated PNG files follow `NETLOG_DATA_DIR`. `NETLOG_LOG_FILE` can override just the CSV path. Do not run multiple collectors against the same CSV; use separate data and state directories for separate experiments.

## Inspect raw measurements

```bash
bash netlog_watch.sh tail
# Ctrl+C exits tail; the collector remains running.
```

If startup fails, read `netlog_collect.out` in the state directory. Check that the official Ookla CLI works manually and that its initial terms prompt has been handled. Graph generation on a server or TTY can use `MPLBACKEND=Agg`.

## Offline demonstration

```bash
python netlog_analyze.py --log-file examples/sample-netlog.csv
MPLBACKEND=Agg python netlog_plot.py --log-file examples/sample-netlog.csv \
  --speed-graph /tmp/netlog-speed.png --latency-graph /tmp/netlog-latency.png
```

No credentials, personal network logs or real host reports are included in the example data.
