"""Patch the Mindcraft fork with the mcft loop-breaker.

Detects exact-repeat model outputs in the agent response loop; on the third
identical output in a row it skips execution and injects a system nudge so
the next generation changes approach. Idempotent (marker-guarded).

Measured motivation (2026-07-17, 5,777 logged steps): 155 exact
consecutive-repeat outputs; repetition loops are Andy-4.2's top documented
failure mode and ours too.
"""

from __future__ import annotations

from pathlib import Path

MC = Path.home() / "Desktop" / "mindcraft"

NUDGE = (
    "You have given the exact same response multiple times in a row and it is "
    "not working. STOP. Do something different this turn: change location, "
    "change target, or change the command entirely. State your new approach "
    "briefly, in character."
)

agent = MC / "src" / "agent" / "agent.js"
text = agent.read_text(encoding="utf-8")

MARKER = "_mcft_rep_count"
if MARKER in text:
    print("already patched")
    raise SystemExit(0)

anchor = "            let command_name = containsCommand(res);"
assert text.count(anchor) == 1, f"anchor not unique: {text.count(anchor)}"

insert = f"""            // mcft loop-breaker: third identical output in a row is skipped
            // and replaced with a change-approach nudge.
            if (res === this._mcft_last_res) {{
                this._mcft_rep_count = (this._mcft_rep_count || 0) + 1;
            }} else {{
                this._mcft_rep_count = 0;
            }}
            this._mcft_last_res = res;
            if (this._mcft_rep_count >= 2) {{
                this._mcft_rep_count = 0;
                this._mcft_last_res = null;
                console.warn(`${{this.name}} mcft loop-breaker triggered`);
                this.history.add('system', {NUDGE!r});
                continue;
            }}

"""
text = text.replace(anchor, insert + anchor, 1)
agent.write_text(text, encoding="utf-8")
print("patched agent.js with loop-breaker")
