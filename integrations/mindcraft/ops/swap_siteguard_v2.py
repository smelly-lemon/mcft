"""One-time swap of the deployed siteguard v1 nudge to v2 (in-place).

For already-patched agent.js installs. Fresh installs get v2 directly from
patch_siteguard.py. See that file's docstring for the v2 rationale.
"""

from __future__ import annotations

from pathlib import Path

MC = Path.home() / "Desktop" / "mindcraft"

V1_NUDGE = (
    "'You have been deep underground or far from the home site for over 10 "
    "minutes. Mining trips are ONLY for mission materials - take your haul "
    "back to the site NOW and continue the mission phase there. Your "
    "journal GOAL must be the current mission phase, not a mining project.'"
)

V2_NUDGE = (
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

if "surface level is Y=" in text:
    print("already v2")
    raise SystemExit(0)

assert text.count(V1_NUDGE) == 1, f"v1 nudge not found exactly once ({text.count(V1_NUDGE)})"
text = text.replace(V1_NUDGE, V2_NUDGE, 1)
agent.write_text(text, encoding="utf-8")
print("siteguard nudge swapped to v2")
