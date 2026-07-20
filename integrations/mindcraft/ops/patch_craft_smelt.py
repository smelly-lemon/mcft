"""Patch craftRecipe and smeltItem failure paths with actionable errors.

Measured 2026-07-20 (eras C+D, 221 craft / 85 smelt uses):
  - 63 craft fails are a CRASH: getItemCraftingRecipes() returns null for
    items with no crafting recipe (charcoal...) and .length throws.
  - 38 craft fails are bare "missing ingredient" throws from bot.craft with
    zero detail, so the model can't plan the fix.
  - 63 smelt fails are the charcoal spiral: smelting coal/coal_ore/raw_coal
    while the hint never says charcoal = smelt logs.
Idempotent (marker-guarded per patch).
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

# E1a: null recipes crash -> explanatory failure.
patch(
    skills,
    """    if (mc.getItemCraftingRecipes(itemName).length == 0) {
        log(bot, `${itemName} is either not an item, or it does not have a crafting recipe!`);
        return false;
    }""",
    """    const _mcft_recipes = mc.getItemCraftingRecipes(itemName); // mcft: was a null-deref crash
    if (!_mcft_recipes || _mcft_recipes.length == 0) {
        log(bot, `${itemName} has NO crafting recipe - it cannot be crafted. It may come from smelting (charcoal: !smeltItem("oak_log", 8)), mining, or mob drops.`);
        return false;
    }""",
    "mcft: was a null-deref crash",
)

# E1b: zero-craftable guard + informative missing-ingredient report instead
# of letting bot.craft throw a bare "missing ingredient" exception.
patch(
    skills,
    """    await bot.craft(recipe, Math.min(craftLimit.num, num), craftingTable);
    if(craftLimit.num<num) log(bot, `Not enough ${craftLimit.limitingResource} to craft ${num}, crafted ${craftLimit.num}. You now have ${world.getInventoryCounts(bot)[itemName]} ${itemName}.`);""",
    """    if (craftLimit.num <= 0) { // mcft: report exactly what is missing
        const _short = Object.entries(requiredIngredients)
            .filter(([k, v]) => (inventory[k] || 0) < v)
            .map(([k, v]) => `${k} (need ${v}, have ${inventory[k] || 0})`)
            .join(', ');
        log(bot, `Cannot craft ${itemName}: missing ingredients - ${_short || 'unknown'}. Gather these first.`);
        if (placedTable) {
            await collectBlock(bot, 'crafting_table', 1);
        }
        return false;
    }
    try {
        await bot.craft(recipe, Math.min(craftLimit.num, num), craftingTable);
    } catch (err) {
        const _req = Object.entries(requiredIngredients)
            .map(([k, v]) => `${k} x${v}`).join(', ');
        log(bot, `Craft of ${itemName} failed (${err.message}). Recipe needs: ${_req}. Check your inventory and gather what is missing.`);
        if (placedTable) {
            await collectBlock(bot, 'crafting_table', 1);
        }
        return false;
    }
    if(craftLimit.num<num) log(bot, `Not enough ${craftLimit.limitingResource} to craft ${num}, crafted ${craftLimit.num}. You now have ${world.getInventoryCounts(bot)[itemName]} ${itemName}.`);""",
    "mcft: report exactly what is missing",
)

# E2: charcoal-aware smelt hint (only inside the not-smeltable branch).
patch(
    skills,
    """    if (!mc.isSmeltable(itemName)) {
        log(bot, `Cannot smelt ${itemName}. Hint: make sure you are smelting the 'raw' item.`);
        return false;
    }""",
    """    if (!mc.isSmeltable(itemName)) {
        if (String(itemName).includes('coal')) { // mcft: end the charcoal spiral
            log(bot, `Cannot smelt ${itemName}. Coal/charcoal are FUEL, not smelting inputs. To get charcoal: smelt logs, e.g. !smeltItem("oak_log", 8). To get coal: mine it with !collectBlocks("coal_ore", 8).`);
            return false;
        }
        log(bot, `Cannot smelt ${itemName}. Hint: make sure you are smelting the 'raw' item.`);
        return false;
    }""",
    "mcft: end the charcoal spiral",
)

print("done")
