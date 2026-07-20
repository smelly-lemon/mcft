"""Patch agent.js: guard checkTaskDone against the restart race.

Observed 2026-07-19 19:16 UTC-7: Jolt crashed, Mindcraft auto-restarted it,
and during re-init a queued conversation message from Sable reached
handleMessage -> checkTaskDone before this.task was constructed:
"TypeError: Cannot read properties of undefined (reading 'data')". The
second crash tripped "exited too quickly and will not be restarted",
leaving Jolt dead for 3 hours. One-line guard. Idempotent.
"""

from __future__ import annotations

from pathlib import Path

MC = Path.home() / "Desktop" / "mindcraft"

agent = MC / "src" / "agent" / "agent.js"
text = agent.read_text(encoding="utf-8")

OLD = """    async checkTaskDone() {
        if (this.task.data) {"""
NEW = """    async checkTaskDone() {
        if (this.task && this.task.data) { // mcft: task may not exist yet during restart re-init"""

if "task may not exist yet" in text:
    print("already patched")
    raise SystemExit(0)

assert OLD in text, "checkTaskDone anchor not found"
text = text.replace(OLD, NEW, 1)
agent.write_text(text, encoding="utf-8")
print("patched agent.js with checkTaskDone guard")
