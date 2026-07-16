"""Patch the Mindcraft fork to wire in the mcft trajectory logger.

Idempotent: skips any edit whose marker is already present. Run on the
Studio from anywhere; paths are fixed to the fork location.
"""

from __future__ import annotations

from pathlib import Path

MC = Path.home() / "Desktop" / "mindcraft"


def patch(path: Path, old: str, new: str, marker: str) -> None:
    text = path.read_text(encoding="utf-8")
    if marker in text:
        print(f"skip (already patched): {path.name}: {marker[:50]}")
        return
    assert old in text, f"anchor not found in {path}: {old[:80]!r}"
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"patched {path.name}: {marker[:50]}")


# --- prompter.js: capture system prompt + latency per generation ---
prompter = MC / "src" / "models" / "prompter.js"
patch(
    prompter,
    "            let generation;\n",
    "            let generation;\n            const _mcft_t0 = Date.now();\n",
    "_mcft_t0",
)
patch(
    prompter,
    'console.log("Generated response:", generation);',
    'console.log("Generated response:", generation);\n'
    "                this.mcft_last = { prompt: prompt, latency_ms: Date.now() - _mcft_t0, "
    "messages: JSON.stringify(messages) };",
    "this.mcft_last",
)

# --- agent.js: construct logger, log command and chat steps ---
agent = MC / "src" / "agent" / "agent.js"
patch(
    agent,
    "import { containsCommand",
    "import { McftLogger } from './mcft_logger.js';\nimport { containsCommand",
    "McftLogger",
)
patch(
    agent,
    "        this.history = new History(this);",
    "        this.history = new History(this);\n        this.mcft_logger = new McftLogger(this);",
    "new McftLogger",
)
patch(
    agent,
    "                console.log('Agent executed:', command_name, 'and got:', execute_res);",
    "                console.log('Agent executed:', command_name, 'and got:', execute_res);\n"
    "                this.mcft_logger?.logStep(res, command_name, execute_res);",
    "logStep(res, command_name",
)
patch(
    agent,
    "            else { // conversation response\n"
    "                this.history.add(this.name, res);",
    "            else { // conversation response\n"
    "                this.history.add(this.name, res);\n"
    "                this.mcft_logger?.logStep(res, null, null);",
    "logStep(res, null",
)

print("done")
