"""Upgrade the mcft loop-breaker: alternation detection + context deflation.

Measured 2026-07-18 (rolling digest): repetition spiked to 130-150/1k steps
despite the v1 breaker. Two gaps: (1) A/B/A/B two-step ruts evade the
consecutive-identical check entirely; (2) after a v1 nudge the history still
holds the repeated turns, so the model pattern-matches straight back into
the loop (A A A(nudge) A A A(nudge)... signature in the logs).

V2 detects period-1 (AAA) and period-2 (ABAB) exact loops, removes the
duplicated turns from recent history to kill in-context momentum, then
nudges. Exact-match only, on purpose: number-advancing sequences like
placing slabs along a row are usually productive work, not loops.

Requires patch_loopbreaker.py applied (replaces its block). Idempotent.
"""

from __future__ import annotations

from pathlib import Path

MC = Path.home() / "Desktop" / "mindcraft"

V1_NUDGE = (
    "You have given the exact same response multiple times in a row and it is "
    "not working. STOP. Do something different this turn: change location, "
    "change target, or change the command entirely. State your new approach "
    "briefly, in character."
)

V1_BLOCK = f"""            // mcft loop-breaker: third identical output in a row is skipped
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
                this.history.add('system', {V1_NUDGE!r});
                continue;
            }}

"""

NUDGE_REPEAT = (
    "You have given the exact same response multiple times in a row and it is "
    "not working. STOP. Do something different this turn: change location, "
    "change target, or change the command entirely. State your new approach "
    "briefly, in character."
)
NUDGE_ALT = (
    "You are alternating between the same two responses and making no "
    "progress. STOP the cycle. Re-read your journal GOAL, then take one "
    "concrete different action: a new location, a new resource, or a new "
    "build step. State your new approach briefly, in character."
)

V2_BLOCK = f"""            // mcft loop-breaker v2: catch exact repeats (AAA) and two-step
            // alternating ruts (ABAB). Remove the duplicated turns from
            // recent history to kill in-context momentum, then nudge.
            this._mcft_res_hist = this._mcft_res_hist || [];
            this._mcft_res_hist.push(res);
            if (this._mcft_res_hist.length > 6) this._mcft_res_hist.shift();
            const _mh = this._mcft_res_hist;
            const _mn = _mh.length;
            const _mcft_p1 = _mn >= 3 && _mh[_mn-1] === _mh[_mn-2] && _mh[_mn-2] === _mh[_mn-3];
            const _mcft_p2 = !_mcft_p1 && _mn >= 4 && _mh[_mn-1] === _mh[_mn-3] && _mh[_mn-2] === _mh[_mn-4] && _mh[_mn-1] !== _mh[_mn-2];
            if (_mcft_p1 || _mcft_p2) {{
                const _dups = new Set(_mcft_p1 ? [res] : [res, _mh[_mn-2]]);
                for (const _d of Array.from(_dups)) {{
                    try {{ _dups.add(truncCommandMessage(_d)); }} catch (e) {{}}
                }}
                this._mcft_res_hist = [];
                const _mt = this.history.turns;
                const _floor = Math.max(0, _mt.length - 12);
                let _removed = 0;
                for (let i = _mt.length - 1; i >= _floor; i--) {{
                    if (_mt[i] && _dups.has(_mt[i].content)) {{ _mt.splice(i, 1); _removed++; }}
                }}
                console.warn(`${{this.name}} mcft loop-breaker v2 (${{_mcft_p1 ? 'repeat' : 'alternation'}}), removed ${{_removed}} duplicate turns`);
                this.history.add('system', _mcft_p1 ? {NUDGE_REPEAT!r} : {NUDGE_ALT!r});
                continue;
            }}

"""

agent = MC / "src" / "agent" / "agent.js"
text = agent.read_text(encoding="utf-8")

if "_mcft_res_hist" in text:
    print("already patched (v2)")
    raise SystemExit(0)

assert V1_BLOCK in text, "v1 loop-breaker block not found; apply patch_loopbreaker.py first"
text = text.replace(V1_BLOCK, V2_BLOCK, 1)
agent.write_text(text, encoding="utf-8")
print("patched agent.js with loop-breaker v2")
