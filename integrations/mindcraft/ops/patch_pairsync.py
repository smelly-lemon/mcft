"""Patch mindserver_proxy.js: partner reconnect triggers a re-sync note.

Measured 2026-07-20: after any restart the surviving bot's conversation
state goes stale - Sable's journal declared "PARTNER: Jolt (idle/
unresponsive)" while Jolt was alive and building. Role splits decay into
solo side quests after every crash/restart.

On an agents-status update where another agent transitions into the game,
inject one system note so the model re-syncs roles. Baseline set on first
status (no fire at initial spawn for already-present agents). Idempotent.
"""

from __future__ import annotations

from pathlib import Path

MC = Path.home() / "Desktop" / "mindcraft"

proxy = MC / "src" / "agent" / "mindserver_proxy.js"
text = proxy.read_text(encoding="utf-8")

MARKER = "mcft pairsync"
if MARKER in text:
    print("already patched")
    raise SystemExit(0)

OLD = """        this.socket.on('agents-status', (agents) => {
            this.agents = agents;
            convoManager.updateAgents(agents);"""
NEW = """        this.socket.on('agents-status', (agents) => {
            // mcft pairsync: nudge on partner (re)connect - conversation
            // state goes stale across restarts and role splits decay.
            const _now_in = agents.filter(a => a.in_game).map(a => a.name);
            if (this._mcft_prev_in && this.agent?.history) {
                for (const n of _now_in) {
                    if (n !== this.agent.name && !this._mcft_prev_in.includes(n)) {
                        console.warn(`${this.agent.name} mcft pairsync: ${n} (re)joined`);
                        this.agent.history.add('system',
                            `${n} just (re)joined the world and may have lost recent conversation context. ` +
                            `Briefly re-sync your roles with them (e.g. !startConversation("${n}", "status?")) before continuing.`);
                    }
                }
            }
            this._mcft_prev_in = _now_in;
            this.agents = agents;
            convoManager.updateAgents(agents);"""

assert OLD in text, "agents-status anchor not found"
text = text.replace(OLD, NEW, 1)
proxy.write_text(text, encoding="utf-8")
print("patched mindserver_proxy.js with pairsync")
