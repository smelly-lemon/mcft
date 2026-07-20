"""Patch agent.js with the site guard v2: deep/far nudge with literal coords.

Measured 2026-07-20: 61% of clean-era steps were underground (y < site-10)
and 21% were >30 blocks from the site; journal GOALs drifted to invented
material quests (copper smelting, bridges). The prompt-level site anchor
holds coordinates but not intent once mining starts.

v2 (soak finding, same day): v1's vague "return to the site NOW" failed to
rescue Sable from a corrupted "wall base (94, 59, -283)" journal coordinate -
it sat at Y=6 for 90 minutes while nudges fired, and its own escape attempts
used !goToSurface, which fails ~50% in shafts. v2 therefore (a) embeds the
literal site coordinates and a !goToCoordinates call (pathfinder handles
vertical), and (b) says BUILD coordinates below the site are corrupted -
without banning mining itself, which eval tasks and phase materials require.

Guard: every 60s, check position against the site in mcft_site.json (repo
root of the fork). After 10 consecutive violating minutes (y < site.y-10 or
horizontal distance > 40), inject one system nudge; 15-minute cooldown.
Disabled when mcft_site.json is absent. Idempotent.
"""

from __future__ import annotations

from pathlib import Path

MC = Path.home() / "Desktop" / "mindcraft"

# Backtick template literal: ${...} interpolated by JS at fire time.
NUDGE_JS = (
    "`You have been deep underground or far from the home site for over 10 "
    "minutes. The site is (${_site.x}, ${_site.y}, ${_site.z}) - surface level "
    "is Y=${_site.y}. Mining for mission materials is fine, but you have what "
    "you need or are lost: return now with !goToCoordinates(${_site.x}, "
    "${_site.y}, ${_site.z}, 3) (do NOT use goToSurface - it fails in shafts). "
    "IMPORTANT: any BUILD or wall coordinate in your plan with Y far below "
    "${_site.y} is corrupted - the house is AT the site, on the surface. Your "
    "journal GOAL must be the current mission phase.`"
)

agent = MC / "src" / "agent" / "agent.js"
text = agent.read_text(encoding="utf-8")

MARKER = "mcft siteguard"
if MARKER in text:
    print("already patched (run restore first for v2)")
    raise SystemExit(0)

anchor = "    startEvents() {\n"
assert text.count(anchor) == 1, "startEvents anchor not unique"

insert = f"""    startEvents() {{
        // mcft siteguard v2: nudge after 10 consecutive minutes deep/far,
        // with literal coords + goToCoordinates escape (see ops/patch_siteguard.py).
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
                    this.history.add('system', {NUDGE_JS});
                }}
            }}, 60 * 1000);
        }} catch (e) {{ /* no mcft_site.json -> guard disabled */ }}
"""
text = text.replace(anchor, insert, 1)

# readFileSync import: agent.js may not import fs; add if missing.
if "readFileSync" not in text.split("startEvents")[0]:
    first_import = text.index("import ")
    text = (
        text[:first_import]
        + "import { readFileSync } from 'fs'; // mcft siteguard\n"
        + text[first_import:]
    )

agent.write_text(text, encoding="utf-8")
print("patched agent.js with siteguard v2")
