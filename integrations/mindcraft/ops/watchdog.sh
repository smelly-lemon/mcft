#!/bin/zsh
# Mindcraft watchdog: restart the bot stack if the mindserver or all agent
# processes are gone. Installed as a cron job on the Studio (every 5 min).
# Restart-safety: skips restart if the Minecraft server itself is down
# (agents can't log in, and restart loops would thrash).

MINDCRAFT_DIR="$HOME/Desktop/mindcraft"
NODE_BIN="$HOME/.nvm/versions/node/v20.20.2/bin"
LOG="$MINDCRAFT_DIR/watchdog.log"

ts() { date "+%Y-%m-%d %H:%M:%S"; }

# Minecraft server must be up before we try anything.
if ! lsof -nP -iTCP:25566 -sTCP:LISTEN >/dev/null 2>&1; then
    echo "$(ts) minecraft server down on :25566; skipping" >> "$LOG"
    exit 0
fi

# Brain check: Ollama must answer a 1-token completion. Busy is NOT wedged:
# agent requests queue ahead of the probe (one at a time on this model), so
# give the probe a long timeout and require 2 consecutive failures before
# killing the runner. History: the 07-19 wedge hung every request at the
# server's own 5m limit for 11h; the first probe version (120s, single
# failure) misdiagnosed a busy runner and caused a kill/reload loop.
PROBE_STATE=/tmp/mcft_ollama_probe_fails
if lsof -nP -iTCP:11434 -sTCP:LISTEN >/dev/null 2>&1; then
    probe=$(curl -s -m 290 http://localhost:11434/api/generate \
        -d '{"model": "qwen3.6:35b", "prompt": "hi", "stream": false, "keep_alive": -1, "options": {"num_predict": 1}}' 2>/dev/null)
    if echo "$probe" | grep -q '"done"'; then
        rm -f "$PROBE_STATE"
    else
        fails=$(( $(cat "$PROBE_STATE" 2>/dev/null || echo 0) + 1 ))
        echo "$fails" > "$PROBE_STATE"
        echo "$(ts) ollama probe failed ($fails consecutive)" >> "$LOG"
        if (( fails >= 2 )); then
            echo "$(ts) killing wedged ollama runner" >> "$LOG"
            pkill -f "ollama runner" 2>/dev/null
            rm -f "$PROBE_STATE"
        fi
    fi
else
    echo "$(ts) ollama serve not listening; relaunching app" >> "$LOG"
    open -ga Ollama
fi

main_alive=$(pgrep -f "node main.js" | head -1)
agents_alive=$(pgrep -f "init_agent.js" | head -1)

if [[ -n "$main_alive" && -n "$agents_alive" ]]; then
    exit 0
fi

echo "$(ts) restarting (main=${main_alive:-dead} agents=${agents_alive:-dead})" >> "$LOG"
pkill -f "init_agent.js" 2>/dev/null
pkill -f "node main.js" 2>/dev/null
sleep 3

cd "$MINDCRAFT_DIR" || exit 1
export PATH="$NODE_BIN:$PATH"
nohup node main.js >> mindcraft.log 2>&1 &
echo "$(ts) restarted mindcraft (pid $!)" >> "$LOG"
