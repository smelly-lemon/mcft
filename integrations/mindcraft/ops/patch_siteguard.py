"""Patch agent.js with the site guard: persistent deep/far mining nudge.

Measured 2026-07-20: 61% of clean-era steps were underground (y < site-10)
and 21% were >30 blocks from the site; journal GOALs drifted to invented
material quests (copper smelting, bridges). The prompt-level site anchor
holds coordinates but not intent once mining starts.

Guard: every 60s, check position against the site in mcft_site.json (repo
root of the fork). After 10 consecutive violating minutes (y < site.y-10 or
horizontal distance > 40), inject one system nudge; 15-minute cooldown.
Disabled when mcft_site.json is absent. Idempotent.
"""

from __future__ import annotations

from pathlib import Path

MC = Path.home() / "Desktop" / "mindcraft"

NUDGE = (
    "You have been deep underground or far from the home site for over 10 "
    "minutes. Mining trips are ONLY for mission materials - take your haul "
    "back to the site NOW and continue the mission phase there. Your "
    "journal GOAL must be the current mission phase, not a mining project."
)

agent = MC / "src" / "agent" / "agent.js"
text = agent.read_text(encoding="utf-8")

MARKER = "mcft siteguard"
if MARKER in text:
    print("already patched")
    raise SystemExit(0)

anchor = "    startEvents() {\n"
assert text.count(anchor) == 1, "startEvents anchor not unique"

insert = f"""    startEvents() {{
        // mcft siteguard: nudge after 10 consecutive minutes deep/far.
        try {{
            const _site = JSON.parse(readFileSync('mcft_site.json', 'utf8'));
            this._mcft_site_strikes = 0;
            this._mcft_site_cooldown = 0;
            setInterval(() => {{
                if (!this.bot?.entity?.position) return;
                const p = this.bot.entity.position;
                const horiz = Math.sqrt((p.x - _site.x) ** 2 + (p.z - _site.z) ** 2);
                const violating = p.y < _site.y - 10 || horiz > 40;
                this._mcft_site_strikes = violating ? this._mcft_site_strikes + 1 : 0;
                if (this._mcft_site_strikes >= 10 && Date.now() > this._mcft_site_cooldown) {{
                    this._mcft_site_strikes = 0;
                    this._mcft_site_cooldown = Date.now() + 15 * 60 * 1000;
                    console.warn(`${{this.name}} mcft siteguard nudge (y=${{Math.round(p.y)}} horiz=${{Math.round(horiz)}})`);
                    this.history.add('system', {NUDGE!r});
                }}
            }}, 60 * 1000);
        }} catch (e) {{ /* no mcft_site.json -> guard disabled */ }}
"""
text = text.replace(anchor, insert, 1)

# readFileSync import: agent.js may not import fs; add if missing.
if "readFileSync" not in text.split("startEvents")[0]:
    first_import = text.index("import ")
    text = text[:first_import] + "import { readFileSync } from 'fs'; // mcft siteguard\n" + text[first_import:]

agent.write_text(text, encoding="utf-8")
print("patched agent.js with siteguard")
