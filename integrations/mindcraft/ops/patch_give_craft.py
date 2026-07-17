"""Patch giveToPlayer distance logic and add did-you-mean to item validation.

Measured motivation (2026-07-17): !givePlayer failed 61% (79/129) — the
too-close check demands 5 blocks after only requesting 2, and the pickup
wait is 3s, too short for a receiver bot mid-action. !craftRecipe failures
are 40% hallucinated item names with an uninformative error. Idempotent.
"""

from __future__ import annotations

from pathlib import Path

MC = Path.home() / "Desktop" / "mindcraft"


def patch(path: Path, old: str, new: str, marker: str) -> None:
    text = path.read_text(encoding="utf-8")
    if marker in text:
        print(f"skip (already patched): {marker[:40]}")
        return
    assert old in text, f"anchor not found in {path.name}: {old[:60]!r}"
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"patched {path.name}: {marker[:40]}")


skills = MC / "src" / "agent" / "library" / "skills.js"

# Consistent separation target: move away to 3, accept >= 2 (was: move to
# 2/5, require >= 5 — self-contradictory and the main "too close" cause).
patch(
    skills,
    """        await moveAwayFromEntity(bot, player, 2);
        while (too_close && !bot.interrupt_code) {
            await new Promise(resolve => setTimeout(resolve, 500));
            too_close = bot.entity.position.distanceTo(player.position) < 5;
            if (too_close) {
                await moveAwayFromEntity(bot, player, 5);
            }""",
    """        await moveAwayFromEntity(bot, player, 3); // mcft: consistent 2-3 block target
        while (too_close && !bot.interrupt_code) {
            await new Promise(resolve => setTimeout(resolve, 500));
            too_close = bot.entity.position.distanceTo(player.position) < 2;
            if (too_close) {
                await moveAwayFromEntity(bot, player, 3);
            }""",
    "mcft: consistent 2-3 block target",
)

# Longer pickup window: receiver bots mid-action need more than 3s.
patch(
    skills,
    """        let start = Date.now();
        while (!given && !bot.interrupt_code) {
            await new Promise(resolve => setTimeout(resolve, 500));
            if (given) {
                return true;
            }
            if (Date.now() - start > 3000) {
                break;
            }
        }
    }
    log(bot, `Failed to give ${itemType} to ${username}, it was never received.`);""",
    """        let start = Date.now();
        while (!given && !bot.interrupt_code) {
            await new Promise(resolve => setTimeout(resolve, 500));
            if (given) {
                return true;
            }
            if (Date.now() - start > 10000) { // mcft: was 3s; busy receivers collect late
                break;
            }
        }
        if (given) return true;
    }
    log(bot, `Failed to give ${itemType} to ${username}, it was never received.`);""",
    "mcft: was 3s; busy receivers collect late",
)

# Did-you-mean on invalid item names.
index = MC / "src" / "agent" / "commands" / "index.js"
patch(
    index,
    'import { getBlockId, getItemId } from "../../utils/mcdata.js";',
    'import { getBlockId, getItemId, getAllItems } from "../../utils/mcdata.js";\n'
    "// mcft: did-you-mean for hallucinated item names (40% of craft failures)\n"
    "function mcftSuggestItem(arg) {\n"
    "    try {\n"
    "        const names = getAllItems().map(i => i.name);\n"
    "        const a = String(arg).toLowerCase();\n"
    "        const best = names.find(n => n === a + 's' || n + 's' === a) ||\n"
    "                     names.find(n => n.includes(a) || a.includes(n));\n"
    "        return best ? ` Did you mean \"${best}\"?` : '';\n"
    "    } catch (e) { return ''; }\n"
    "}",
    "mcftSuggestItem",
)
patch(
    index,
    "            if(getItemId(arg) == null) return `Invalid item type: ${arg}.`",
    "            if(getItemId(arg) == null) return "
    "`Invalid item type: ${arg}.${mcftSuggestItem(arg)}`",
    "mcftSuggestItem(arg)}`",
)

print("done")
