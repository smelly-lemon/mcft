#!/bin/zsh
# Watchdog daemon: loops forever, checking/restarting Mindcraft every 5 min.
# Started via nohup from an SSH session (cron is denied ~/Desktop access by
# macOS TCC — see watchdog.log 2026-07-17). Guards against duplicate copies.

WATCHDOG="$HOME/Desktop/mindcraft/ops/watchdog.sh"
LOCK="/tmp/mcft_watchdog_daemon.pid"

if [[ -f "$LOCK" ]] && kill -0 "$(cat $LOCK)" 2>/dev/null; then
    echo "watchdog daemon already running (pid $(cat $LOCK))"
    exit 0
fi
echo $$ > "$LOCK"

while true; do
    "$WATCHDOG"
    sleep 300
done
