#!/bin/zsh
# Hourly metrics digest daemon (nohup from SSH; cron lacks ~/Desktop access).

LOCK="/tmp/mcft_digest_daemon.pid"
if [[ -f "$LOCK" ]] && kill -0 "$(cat $LOCK)" 2>/dev/null; then
    echo "digest daemon already running (pid $(cat $LOCK))"
    exit 0
fi
echo $$ > "$LOCK"

while true; do
    python3 "$HOME/Desktop/mindcraft/ops/metrics_digest.py" \
        >> "$HOME/Desktop/mindcraft/metrics/digest.log" 2>&1
    sleep 3600
done
