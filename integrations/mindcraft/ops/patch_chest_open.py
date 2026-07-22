"""Chest-open guard v2.

Era-E finding (2026-07-21): the bots placed a block on top of their own
shared chest. Covered chests cannot open in Minecraft; bot.openContainer
throws, the model sees a truncated "!!Code threw exception!!", and retries
forever - takeFromChest failed 21% overall and 124/130 failures shared this
signature.

v1 pre-checked the block above and told the model exactly what to break.
The E-vs-F ablation showed that is not enough: both arms kept hitting the
same failure because the era-E world snapshot bakes in a dirt-covered chest
and the bots act on the advice only sometimes. v2 clears simple soft covers
(dirt, sand, planks...) itself - same philosophy as placeHere retrying
adjacent spots - and only reports when the cover is something unusual.

All three chest skills (takeFromChest / putInChest / viewChest) get:
1. Auto-clear: if the covering block is soft junk, break it and re-check.
2. Actionable report if still covered.
3. try/catch around openContainer so residual failures log recoverably.

Idempotent: handles vanilla, v1-patched, and v2-patched files.
"""

from __future__ import annotations

from pathlib import Path

MC = Path.home() / "Desktop" / "mindcraft"

skills = MC / "src" / "agent" / "library" / "skills.js"
text = skills.read_text(encoding="utf-8")

if "mcft chestguard v2" in text:
    print("already at v2")
    raise SystemExit(0)

V1_PRECHECK = """    // mcft chestguard: covered chests cannot open - say so, actionably.
    const _above = bot.blockAt(chest.position.offset(0, 1, 0));
    if (_above && _above.boundingBox === 'block') {
        log(bot, `The chest cannot open: ${_above.name} sits directly on top of it. ` +
            `Break the ${_above.name} at (${chest.position.x}, ${chest.position.y + 1}, ` +
            `${chest.position.z}) first, then try again.`);
        return false;
    }"""

V2_PRECHECK = """    // mcft chestguard v2: clear soft covers ourselves (advice alone was ignored).
    let _above = bot.blockAt(chest.position.offset(0, 1, 0));
    if (_above && _above.boundingBox === 'block') {
        const _soft = ['dirt', 'grass_block', 'sand', 'gravel', 'oak_planks', 'birch_planks',
            'spruce_planks', 'cobblestone', 'stone', 'oak_log', 'birch_log', 'oak_slab',
            'birch_slab', 'cobblestone_slab', 'moss_block', 'netherrack'];
        if (_soft.includes(_above.name)) {
            log(bot, `A ${_above.name} is covering the chest - clearing it first.`);
            try {
                await breakBlockAt(bot, chest.position.x, chest.position.y + 1, chest.position.z);
            } catch (_e) { /* fall through to the report below */ }
            _above = bot.blockAt(chest.position.offset(0, 1, 0));
        }
    }
    if (_above && _above.boundingBox === 'block') {
        log(bot, `The chest cannot open: ${_above.name} sits directly on top of it. ` +
            `Break the ${_above.name} at (${chest.position.x}, ${chest.position.y + 1}, ` +
            `${chest.position.z}) first, then try again.`);
        return false;
    }"""

if V1_PRECHECK in text:
    n = text.count(V1_PRECHECK)
    assert n == 3, f"expected 3 v1 pre-checks, found {n}"
    text = text.replace(V1_PRECHECK, V2_PRECHECK)
    skills.write_text(text, encoding="utf-8")
    print("upgraded chestguard v1 -> v2 in 3 chest skills")
    raise SystemExit(0)

# vanilla file: install v2 outright (pre-check + guarded open)
OLD = "    const chestContainer = await bot.openContainer(chest);"
assert text.count(OLD) == 3, f"expected 3 openContainer sites, found {text.count(OLD)}"

NEW = (
    V2_PRECHECK
    + """
    let chestContainer;
    try {
        chestContainer = await bot.openContainer(chest);
    } catch (err) {
        log(bot, `Failed to open the chest at (${chest.position.x}, ${chest.position.y}, ` +
            `${chest.position.z}): ${err.message}. Stand within 3 blocks of it, and if ` +
            `any block sits above the chest, break that block first.`);
        return false;
    }"""
)

text = text.replace(OLD, NEW)
skills.write_text(text, encoding="utf-8")
print("patched skills.js: chestguard v2 in 3 chest skills")
