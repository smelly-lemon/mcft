"""Chest-open guard (era-F boundary bundle).

Era-E finding (2026-07-21): the bots placed a block on top of their own
shared chest. Covered chests cannot open in Minecraft; bot.openContainer
throws, the model sees a truncated "!!Code threw exception!!", and retries
forever - takeFromChest failed 21% overall and 124/130 failures shared this
signature.

Fix, in all three chest skills (takeFromChest / putInChest / viewChest):
1. Pre-check the block above the chest; if solid, tell the model the exact
   block to break and where - actionable, like the E1 craft errors.
2. Wrap openContainer in try/catch so any residual open failure logs a
   recoverable message instead of throwing out of the skill.
"""

from __future__ import annotations

from pathlib import Path

MC = Path.home() / "Desktop" / "mindcraft"
MARKER = "mcft chestguard"

skills = MC / "src" / "agent" / "library" / "skills.js"
text = skills.read_text(encoding="utf-8")

if MARKER in text:
    print("already patched")
    raise SystemExit(0)

OLD = "    const chestContainer = await bot.openContainer(chest);"
assert text.count(OLD) == 3, f"expected 3 openContainer sites, found {text.count(OLD)}"

NEW = """    // mcft chestguard: covered chests cannot open - say so, actionably.
    const _above = bot.blockAt(chest.position.offset(0, 1, 0));
    if (_above && _above.boundingBox === 'block') {
        log(bot, `The chest cannot open: ${_above.name} sits directly on top of it. ` +
            `Break the ${_above.name} at (${chest.position.x}, ${chest.position.y + 1}, ` +
            `${chest.position.z}) first, then try again.`);
        return false;
    }
    let chestContainer;
    try {
        chestContainer = await bot.openContainer(chest);
    } catch (err) {
        log(bot, `Failed to open the chest at (${chest.position.x}, ${chest.position.y}, ` +
            `${chest.position.z}): ${err.message}. Stand within 3 blocks of it, and if ` +
            `any block sits above the chest, break that block first.`);
        return false;
    }"""

text = text.replace(OLD, NEW)
skills.write_text(text, encoding="utf-8")
print("patched skills.js: chestguard in 3 chest skills")
