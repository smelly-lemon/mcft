"""Patch goToPosition: near-arrival is success, not failure.

Measured 2026-07-19 (clean window, 474 goto uses): half of all failures are
"Unable to reach X, you are 2-3 blocks away" - the pathfinder stops beside
the target (usually against the structure being built) and the strict
distance <= min_distance+1 check calls it a failure. The bots then retry
the same coordinate (one racked up 11 identical failures), feeding
repetition loops and mislabeling functionally-successful steps as failures
in the training data. Arrival within max(min_distance+2, 3.5) blocks now
succeeds with an honest message. Idempotent (marker-guarded).
"""

from __future__ import annotations

from pathlib import Path

MC = Path.home() / "Desktop" / "mindcraft"

skills = MC / "src" / "agent" / "library" / "skills.js"
text = skills.read_text(encoding="utf-8")

MARKER = "mcft near-arrival"
if MARKER in text:
    print("already patched")
    raise SystemExit(0)

OLD = """        const distance = bot.entity.position.distanceTo(new Vec3(x, y, z));
        if (distance <= min_distance+1) {
            log(bot, `You have reached at ${x}, ${y}, ${z}.`);
            return true;
        }
        else {
            log(bot, `Unable to reach ${x}, ${y}, ${z}, you are ${Math.round(distance)} blocks away.`);
            return false;
        }"""
NEW = """        const distance = bot.entity.position.distanceTo(new Vec3(x, y, z));
        if (distance <= min_distance+1) {
            log(bot, `You have reached at ${x}, ${y}, ${z}.`);
            return true;
        }
        else if (distance <= Math.max(min_distance + 2, 3.5)) { // mcft near-arrival
            log(bot, `Arrived near ${x}, ${y}, ${z} - ${Math.round(distance)} blocks away, close enough to work from here.`);
            return true;
        }
        else {
            log(bot, `Unable to reach ${x}, ${y}, ${z}, you are ${Math.round(distance)} blocks away.`);
            return false;
        }"""

assert OLD in text, "goToPosition arrival check anchor not found"
text = text.replace(OLD, NEW, 1)
skills.write_text(text, encoding="utf-8")
print("patched skills.js with near-arrival success")
