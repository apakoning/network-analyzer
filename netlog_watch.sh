#!/usr/bin/env bash
# Manage the current user's Network Analyzer collector.
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="${NETLOG_DATA_DIR:-${XDG_DATA_HOME:-$HOME/.local/share}/netlog}"
STATE_DIR="${NETLOG_STATE_DIR:-${XDG_STATE_HOME:-$HOME/.local/state}/netlog}"
LOG_FILE="${NETLOG_LOG_FILE:-$DATA_DIR/netlog.csv}"
PYTHON="${NETLOG_PYTHON:-python3}"
PID_FILE="$STATE_DIR/netlog_collect.pid"
LOG_STDOUT="$STATE_DIR/netlog_collect.out"
usage() {
  echo "Usage: $0 {start [collector options...]|stop|status|analyze|plot|tail}"
}
[[ $# -gt 0 ]] || { usage; exit 2; }
case "$1" in -h|--help) usage; exit 0;; esac
umask 077
mkdir -p "$DATA_DIR" "$STATE_DIR"
command -v flock >/dev/null || { echo "flock (util-linux) is required." >&2; exit 1; }
exec 9>"$STATE_DIR/control.lock"
flock -n 9 || { echo "Another control command is running." >&2; exit 1; }
running() {
  [[ -f "$PID_FILE" ]] || return 1
  PID="$(cat "$PID_FILE")"
  [[ "$PID" =~ ^[0-9]+$ && -r "/proc/$PID/cmdline" ]] || return 1
  kill -0 "$PID" 2>/dev/null || return 1
  tr '\0' '\n' < "/proc/$PID/cmdline" | grep -Fxq -- "$SCRIPT_DIR/netlog_collect.py"
}
action="$1"
shift
case "$action" in
  start)
    if running; then echo "Collector already running with PID $PID"; exit 0; fi
    command -v "$PYTHON" >/dev/null || { echo "Python interpreter not found: $PYTHON" >&2; exit 1; }
    command -v ping >/dev/null && command -v speedtest >/dev/null || { echo "Install ping and the official Ookla Speedtest CLI first." >&2; exit 1; }
    nohup "$PYTHON" "$SCRIPT_DIR/netlog_collect.py" "$@" --log-file "$LOG_FILE" >> "$LOG_STDOUT" 2>&1 9>&- &
    PID=$!
    echo "$PID" > "$PID_FILE"
    sleep 0.3
    if ! running; then rm -f "$PID_FILE"; echo "Collector exited; see $LOG_STDOUT" >&2; exit 1; fi
    echo "Collector started with PID $PID"
    echo "CSV: $LOG_FILE"
    echo "Output log: $LOG_STDOUT"
    ;;
  stop)
    if running; then kill -- "$PID"; echo "Stop requested for collector $PID.";
    else echo "Collector is not running; clearing stale state."; fi
    rm -f "$PID_FILE"
    ;;
  status)
    if running; then echo "Collector is running with PID $PID"; else echo "Collector is not running."; fi
    ;;
  analyze) "$PYTHON" "$SCRIPT_DIR/netlog_analyze.py" --log-file "$LOG_FILE" "$@" ;;
  plot) "$PYTHON" "$SCRIPT_DIR/netlog_plot.py" --log-file "$LOG_FILE" --speed-graph "$DATA_DIR/netlog_speed.png" --latency-graph "$DATA_DIR/netlog_latency.png" "$@" ;;
  tail) flock -u 9; tail -f -- "$LOG_FILE" ;;
  *) usage; exit 2 ;;
esac
