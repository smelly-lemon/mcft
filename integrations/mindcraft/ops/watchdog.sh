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

# Brain check: Ollama must answer a 1-token completion. Busy is NOT wedged
# (agent requests queue ahead of the probe), so allow one slow/failed probe.
# Escalation ladder learned from the 07-19 wedges: killing just the runner
# does NOT heal a wedged serve (18:40/19:00 kills changed nothing; serve
# stopped logging requests entirely). 2 fails -> kill runner; 3+ fails ->
# full app restart + async preload. Counter resets only on probe success.
PROBE_STATE=/tmp/mcft_ollama_probe_fails
PRELOAD='{"model": "qwen3.6:35b", "prompt": "hi", "stream": false, "keep_alive": -1, "options": {"num_predict": 1}}'
if lsof -nP -iTCP:11434 -sTCP:LISTEN >/dev/null 2>&1; then
    probe=$(curl -s -m 290 http://localhost:11434/api/generate -d "$PRELOAD" 2>/dev/null)
    if echo "$probe" | grep -q '"done"'; then
        rm -f "$PROBE_STATE"
    else
        fails=$(( $(cat "$PROBE_STATE" 2>/dev/null || echo 0) + 1 ))
        echo "$fails" > "$PROBE_STATE"
        echo "$(ts) ollama probe failed ($fails consecutive)" >> "$LOG"
        if (( fails == 2 )); then
            echo "$(ts) killing wedged ollama runner" >> "$LOG"
            pkill -f "ollama runner" 2>/dev/null
        elif (( fails >= 3 )); then
            echo "$(ts) runner kill did not heal; full ollama app restart" >> "$LOG"
            killall ollama 2>/dev/null
            sleep 5
            open -ga Ollama
            sleep 10
            (curl -s -m 240 http://localhost:11434/api/generate -d "$PRELOAD" >/dev/null 2>&1 &)
        fi
    fi
else
    echo "$(ts) ollama serve not listening; relaunching app" >> "$LOG"
    open -ga Ollama
    sleep 10
    (curl -s -m 240 http://localhost:11434/api/generate -d "$PRELOAD" >/dev/null 2>&1 &)
fi

# Both agents must be running: Mindcraft's "exited too quickly and will not
# be restarted" latch leaves permanent one-bot holes (Jolt was down 3h on
# 07-19 while the old any-agent check passed).
EXPECTED_AGENTS=2
main_alive=$(pgrep -f "node main.js" | head -1)
agents_count=$(pgrep -f "init_agent.js" | wc -l | tr -d " ")

if [[ -n "$main_alive" && "$agents_count" -ge "$EXPECTED_AGENTS" ]]; then
    exit 0
fi

echo "$(ts) restarting (main=${main_alive:-dead} agents=$agents_count/$EXPECTED_AGENTS)" >> "$LOG"
pkill -f "init_agent.js" 2>/dev/null
pkill -f "node main.js" 2>/dev/null
sleep 3

cd "$MINDCRAFT_DIR" || exit 1
export PATH="$NODE_BIN:$PATH"
nohup node main.js >> mindcraft.log 2>&1 &
echo "$(ts) restarted mindcraft (pid $!)" >> "$LOG"
