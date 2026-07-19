"""Patch history.js: never clobber the journal with a failed generation.

Motivation (2026-07-19): Ollama wedged at 04:23 and every request returned
the "No response data." sentinel for ~11h. summarizeMemories dutifully
overwrote BOTH bots' journals (site anchor, plan, roles) with that
sentinel — cognition loss on top of the outage. Guard: reject summaries
that are empty, suspiciously short, or match known failure sentinels, and
keep the previous journal instead. Idempotent (marker-guarded).
"""

from __future__ import annotations

from pathlib import Path

MC = Path.home() / "Desktop" / "mindcraft"

history = MC / "src" / "agent" / "history.js"
text = history.read_text(encoding="utf-8")

MARKER = "mcft memguard"
if MARKER in text:
    print("already patched")
    raise SystemExit(0)

OLD = """    async summarizeMemories(turns) {
        console.log("Storing memories...");
        this.memory = await this.agent.prompter.promptMemSaving(turns);
"""
NEW = """    async summarizeMemories(turns) {
        console.log("Storing memories...");
        const _new_mem = await this.agent.prompter.promptMemSaving(turns);
        // mcft memguard: a failed generation must not clobber the journal
        // (2026-07-19: an Ollama outage overwrote both journals with
        // "No response data.", erasing the site anchor and plan).
        const _mem_bad = !_new_mem || _new_mem.trim().length < 30 ||
            _new_mem.includes('No response data') ||
            _new_mem.includes('My brain disconnected');
        if (_mem_bad) {
            console.warn('mcft memguard: rejected bad summary, keeping previous journal');
            return;
        }
        this.memory = _new_mem;
"""
assert OLD in text, "summarizeMemories anchor not found"
text = text.replace(OLD, NEW, 1)
history.write_text(text, encoding="utf-8")
print("patched history.js with memguard")
