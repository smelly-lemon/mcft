"""Patch collectBlocks arg validation with redirects for hallucinated names.

Measured 2026-07-18 (rolling digest): !collectBlocks failures climbed to
30-36%, dominated by requests for item names that are not blocks
("wheat_seeds", "stick") with an uninformative error. Mirrors the
did-you-mean approach that cut craftRecipe failures from ~32% to 4-10%.
Idempotent (marker-guarded); requires patch_give_craft.py applied first
(anchors on the import line it rewrote).
"""

from __future__ import annotations

from pathlib import Path

MC = Path.home() / "Desktop" / "mindcraft"

index = MC / "src" / "agent" / "commands" / "index.js"
text = index.read_text(encoding="utf-8")

MARKER = "mcftSuggestBlock"
if MARKER in text:
    print("already patched")
    raise SystemExit(0)

OLD_IMPORT = (
    'import { getBlockId, getItemId, getAllItems } from "../../utils/mcdata.js";'
)
NEW_IMPORT = '''import { getBlockId, getItemId, getAllItems, getAllBlocks } from "../../utils/mcdata.js";
// mcft: redirect hallucinated block names (top collectBlocks failure)
function mcftSuggestBlock(arg) {
    try {
        const a = String(arg).toLowerCase();
        if (a.includes('seed'))
            return ' Seeds are items, not blocks: break grass to get them, e.g. !collectBlocks("short_grass", 5).';
        if (getItemId(a) != null)
            return ` "${a}" is an item, not a collectible block. Obtain it another way, e.g. !craftRecipe("${a}", 1) if craftable.`;
        const names = getAllBlocks().map(b => b.name);
        const best = names.find(n => n === a + 's' || n + 's' === a) ||
                     names.find(n => n.includes(a) || a.includes(n));
        return best ? ` Did you mean "${best}"?` : '';
    } catch (e) { return ''; }
}'''
assert OLD_IMPORT in text, "import anchor not found (apply patch_give_craft.py first)"
text = text.replace(OLD_IMPORT, NEW_IMPORT, 1)

OLD_CHECK = (
    "            if(getBlockId(arg) == null) return "
    " `Invalid block type: ${arg}.`"
)
NEW_CHECK = (
    "            if(getBlockId(arg) == null) return "
    " `Invalid block type: ${arg}.${mcftSuggestBlock(arg)}`"
)
assert OLD_CHECK in text, "block validation anchor not found"
text = text.replace(OLD_CHECK, NEW_CHECK, 1)

index.write_text(text, encoding="utf-8")
print("patched index.js with collectBlocks name guard")
