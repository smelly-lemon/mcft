"""Patch !placeHere with nearby-offset retries.

Measured motivation (2026-07-17, 5,777 steps): placeHere is the most-used
command (2,360 calls) and the top failure source (273 fails: 116 "nothing to
place on" at the bot's feet, 158 blocked/generic). Retrying adjacent offsets
before giving up fixes most cases without prompt changes. Idempotent.
"""

from __future__ import annotations

from pathlib import Path

MC = Path.home() / "Desktop" / "mindcraft"

actions = MC / "src" / "agent" / "commands" / "actions.js"
text = actions.read_text(encoding="utf-8")

MARKER = "mcft placeHere retry"
if MARKER in text:
    print("already patched")
    raise SystemExit(0)

old = """        perform: runAsAction(async (agent, type) => {
            let pos = agent.bot.entity.position;
            await skills.placeBlock(agent.bot, type, pos.x, pos.y, pos.z);
        })"""

new = """        perform: runAsAction(async (agent, type) => {
            // mcft placeHere retry: feet, then horizontal neighbors, then below.
            let pos = agent.bot.entity.position;
            const offsets = [[0,0,0],[1,0,0],[-1,0,0],[0,0,1],[0,0,-1],[0,-1,0]];
            for (const [dx,dy,dz] of offsets) {
                const ok = await skills.placeBlock(agent.bot, type, pos.x+dx, pos.y+dy, pos.z+dz);
                if (ok) return;
            }
        })"""

assert old in text, "placeHere anchor not found"
actions.write_text(text.replace(old, new, 1), encoding="utf-8")
print("patched actions.js: placeHere retries nearby offsets")
