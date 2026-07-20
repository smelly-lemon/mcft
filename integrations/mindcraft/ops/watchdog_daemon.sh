#!/bin/zsh
# Watchdog daemon: loops forever, checking/restarting Mindcraft every 5 min.
# Started via nohup from an SSH session (cron is denied ~/Desktop access by
# macOS TCC — see watchdog.log 2026-07-17). Guards against duplicate copies.
# Also runs the nightly corpus backup (same TCC reasoning: this process is
# the one blessed context that can read ~/Desktop unattended).

WATCHDOG="$HOME/Desktop/mindcraft/ops/watchdog.sh"
BACKUP="$HOME/Desktop/mindcraft/ops/backup.sh"
LOG="$HOME/Desktop/mindcraft/watchdog.log"
LOCK="/tmp/mcft_watchdog_daemon.pid"

if [[ -f "$LOCK" ]] && kill -0 "$(cat $LOCK)" 2>/dev/null; then
    echo "watchdog daemon already running (pid $(cat $LOCK))"
    exit 0
fi
echo $$ > "$LOCK"

while true; do
    "$WATCHDOG"
    if [[ -x "$BACKUP" && ! -f "$HOME/Backups/mcft/corpus-$(date +%F).tgz" ]]; then
        "$BACKUP" >> "$LOG" 2>&1
    fi
    sleep 300
done
