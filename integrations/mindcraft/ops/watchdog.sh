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

# Brain check, v4. Passive first: a 200 on /api/chat in the last 10 min in
# the newest server log means the brain demonstrably works - no probe needed.
# Active probe (only when bots are idle or failing) MUST use the same
# num_ctx as the agents: the v3 probe used the default context size, which
# demands a second runner instance that can never load under agent traffic,
# so every probe starved and false-alarmed (07-19 19:44-20:24), and the
# forced context-swap pressure is itself a suspected wedge trigger.
# Escalation: 2 fails -> kill runner; 3+ -> real app restart (quit the
# menu-bar supervisor too - bare killall gets respawned instantly).
PROBE_STATE=/tmp/mcft_ollama_probe_fails

# Probe model/ctx read from the deployed profile so model swaps (era bumps,
# Phase 4 bake-offs) can't desync the probe from agent traffic - a probe on
# the wrong model/ctx loads a second runner and false-alarms (07-19 lesson).
read -r PROBE_MODEL PROBE_CTX <<< "$(python3 -c "
import json
p = json.load(open('$MINDCRAFT_DIR/profiles/sable.json'))
m = p.get('model', {})
print(m.get('model', 'qwen3.6:35b'), m.get('params', {}).get('options', {}).get('num_ctx', 16384))
" 2>/dev/null)"
PROBE_MODEL=${PROBE_MODEL:-qwen3.6:35b}
PROBE_CTX=${PROBE_CTX:-16384}
PROBE_BODY='{"model": "'$PROBE_MODEL'", "messages": [{"role": "user", "content": "hi"}], "stream": false, "keep_alive": -1, "options": {"num_predict": 1, "num_ctx": '$PROBE_CTX'}}'

ollama_restart() {
    osascript -e 'quit app "Ollama"' >/dev/null 2>&1
    pkill -f "Ollama.app" 2>/dev/null
    pkill -f "ollama serve" 2>/dev/null
    sleep 5
    pkill -9 -f "ollama serve" 2>/dev/null
    open -ga Ollama
    sleep 10
    (curl -s -m 240 http://localhost:11434/api/chat -d "$PROBE_BODY" >/dev/null 2>&1 &)
}

if lsof -nP -iTCP:11434 -sTCP:LISTEN >/dev/null 2>&1; then
    brain_ok=0
    newest_log=$(ls -t "$HOME"/.ollama/logs/server*.log 2>/dev/null | head -1)
    if [[ -n "$newest_log" ]]; then
        last_ok=$(tail -300 "$newest_log" | grep ' 200 ' | grep 'api/chat' | tail -1 \
            | sed -E 's|^\[GIN\] ([0-9/]+ - [0-9:]+).*|\1|')
        if [[ -n "$last_ok" ]]; then
            last_epoch=$(date -j -f "%Y/%m/%d - %H:%M:%S" "$last_ok" +%s 2>/dev/null)
            if [[ -n "$last_epoch" ]] && (( $(date +%s) - last_epoch < 600 )); then
                brain_ok=1
            fi
        fi
    fi
    if (( ! brain_ok )); then
        probe=$(curl -s -m 290 http://localhost:11434/api/chat -d "$PROBE_BODY" 2>/dev/null)
        echo "$probe" | grep -q '"done"' && brain_ok=1
    fi
    if (( brain_ok )); then
        rm -f "$PROBE_STATE"
    else
        fails=$(( $(cat "$PROBE_STATE" 2>/dev/null || echo 0) + 1 ))
        echo "$fails" > "$PROBE_STATE"
        echo "$(ts) ollama brain check failed ($fails consecutive)" >> "$LOG"
        if (( fails == 2 )); then
            echo "$(ts) killing wedged ollama runner" >> "$LOG"
            pkill -f "ollama runner" 2>/dev/null
        elif (( fails >= 3 )); then
            echo "$(ts) full ollama app restart" >> "$LOG"
            ollama_restart
        fi
    fi
else
    echo "$(ts) ollama serve not listening; relaunching app" >> "$LOG"
    open -ga Ollama
    sleep 10
    (curl -s -m 240 http://localhost:11434/api/chat -d "$PROBE_BODY" >/dev/null 2>&1 &)
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
