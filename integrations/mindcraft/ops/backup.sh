#!/bin/zsh
# Nightly corpus snapshot on the Studio. The corpus (trajectories, journals,
# metrics) is the asset; world dirs are archived separately at era boundaries.
# Invoked by watchdog_daemon.sh (which has TCC-blessed Desktop access; cron
# and launchd do not - see watchdog.log 2026-07-17). Keeps 7 days.
set -e
DEST="$HOME/Backups/mcft"
mkdir -p "$DEST"
STAMP=$(date +%F)
OUT="$DEST/corpus-$STAMP.tgz"
[[ -f "$OUT" ]] && exit 0
cd "$HOME/Desktop/mindcraft"
tar czf "$OUT.tmp" data/raw bots metrics mindcraft.log 2>/dev/null || true
mv "$OUT.tmp" "$OUT"
# prune to the 7 newest
ls -t "$DEST"/corpus-*.tgz 2>/dev/null | tail -n +8 | xargs rm -f 2>/dev/null || true
echo "$(date '+%F %T') corpus backup written: $OUT ($(du -h "$OUT" | cut -f1 | tr -d ' '))"
