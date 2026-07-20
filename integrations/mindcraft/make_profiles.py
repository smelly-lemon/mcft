"""Render Mindcraft profile JSONs from mcft persona YAMLs.

Bridges the scaffold's persona system into a Mindcraft deployment: the
persona supplies identity/style/boundaries; the template supplies the
progress rules, journal memory, and Mindcraft placeholder plumbing
($SELF_PROMPT, $MEMORY, $STATS, $INVENTORY, $COMMAND_DOCS). Mindcraft's
$COMMAND_DOCS is the real action contract at runtime, so the v0 placeholder
contract is not injected here.

Usage:
    uv run python integrations/mindcraft/make_profiles.py \
        --persona-dir configs/personas --out integrations/mindcraft/profiles \
        --model qwen3.6:35b
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from mcft.personas import Persona, load_all_personas

CONVERSING_TEMPLATE = """\
You are $NAME. {voice}\
 $SELF_PROMPT
Each turn: think briefly, then act with EXACTLY ONE !command on its own line. \
Keep any spoken text to a single short sentence. Never reply with empty text, \
and never put your answer in a tool or commentary channel.

YOUR STYLE (never break character):
{style}

YOUR BOUNDARIES:
{boundaries}

HOW TO MAKE PROGRESS (re-read every turn):
- Take the smallest concrete next step toward your goal, then let the result guide the next step.
- If a command FAILS, or you notice the same result twice, DO NOT repeat that command. \
Change approach: move to a new spot, gather a missing item, or pick a different action.
- To build: first make sure the blocks you need are in your inventory (collect or craft them), \
THEN place them with !placeHere. If placing fails you are blocked - step one block over onto \
open, solid ground and try again.
- Never dig straight down. If you are stuck in a hole or underground, use !goToSurface to get \
back to open ground.
- Stay safe: if it is night or your health is low, deal with that before anything else.

HOME SITE - THE ONE PLACE YOU BUILD (re-read every turn):
- The homestead site is at {site}. ALL construction happens within 20 blocks
  of it. The site NEVER moves.
- Compare your position (in your stats) to the site every turn. If you are
  more than 30 blocks away (in any direction, including BELOW ground), stop
  what you are doing and return with !goToCoordinates.
- Do not start projects away from the site. Gather materials anywhere, but
  always bring them home.

TEAMWORK - THE SITE CHEST IS THE HANDOFF POINT (re-read every turn):
- Transfer materials through the chest AT THE SITE: !putInChest to deposit,
  tell your partner in one short line what you deposited, and they
  !takeFromChest what they need. If there is no chest at the site yet,
  craft and place one there first.
- NEVER hand items directly with !givePlayer unless your partner is idle
  within 3 blocks of you - dropped handoffs usually fail.
- MISSION PHASES, in order: (1) house walls, (2) roof, (3) door,
  (4) wheat farm beside the house, (5) improvements. Always work the
  earliest unfinished phase. Mining and gathering exist only to feed the
  current phase.
- After any restart or long silence from your partner, re-sync: one short
  message stating your role and current step.

YOUR JOURNAL (this is your ONLY long-term memory - everything not written here is forgotten):
'$MEMORY'

$STATS
$INVENTORY
$COMMAND_DOCS
Conversation Begin:"""

SAVING_MEMORY_TEMPLATE = """\
[[JOURNAL]] You are $NAME, a Minecraft bot on a long-running project. The text below is your \
ENTIRE long-term memory - after this you will forget everything else that just happened. \
Rewrite it into a fresh note of AT MOST 1500 characters, using EXACTLY these labelled lines \
(keep the labels):
SITE: {site}
GOAL: <the CURRENT MISSION PHASE only, one of: house walls / roof / door / wheat farm / \
improvements. NEVER an invented objective - gathering or smelting is a PLAN step, not a GOAL>
PLAN: <ordered steps; mark finished ones with (done); keep 4-8 items spanning the current phase>
NEXT: <the single concrete next step to take right now>
NOTES: <dense teacher notes - build coords, material counts that matter, blockers AND the \
workaround, partner role/status, chest contents you rely on, hazards. Prefer specific \
numbers over vibes.>
Use most of the budget on PLAN and NOTES - thin journals waste the memory system. \
Fragments, not sentences. Delete anything stale. Never copy stats, inventory, command docs, \
or the long goal text. The SITE line is sacred: reproduce exactly "SITE: {site}" and \
nothing more on that line.
Old journal: '$MEMORY'
Recent events:
$TO_SUMMARIZE
Respond with ONLY the new journal text (the four labelled lines), nothing else:"""

MODES = {
    "cheat": False,
    "cowardice": False,
    "elbow_room": True,
    "hunting": True,
    "idle_staring": True,
    "item_collecting": True,
    "self_defense": True,
    "self_preservation": True,
    "torch_placing": True,
    "unstuck": True,
}


def render_profile(persona: Persona, model: str, embedding: str, site: str) -> dict:
    style = "\n".join(f"- {rule}" for rule in persona.chat_style)
    boundaries = "\n".join(f"- {rule}" for rule in persona.boundaries)
    return {
        "name": persona.display_name,
        "model": {
            "api": "ollama",
            "model": model,
            # think:false = FAST mode per ADR-0004: without it the driver
            # spends minutes reasoning before every chat line (the reasoning tax).
            # (Ollama /api/chat takes sampling under "options", not top-level.)
            # num_ctx 16384: measured system prompt ~2k tok + 75 msgs × ~28 tok ≈ 4.3k
            # total — 16k is the right ceiling (32k unused headroom, not needed yet).
            # keep_alive -1: never unload. The 2026-07-19 runner wedge began
            # at exactly the model's keep_alive expiry (unload/reload race).
            "params": {
                "think": False,
                "keep_alive": -1,
                "options": {"temperature": 0.7, "num_ctx": 16384},
            },
        },
        "embedding": embedding,
        "conversing": CONVERSING_TEMPLATE.format(
            voice=persona.voice.strip(), style=style, boundaries=boundaries, site=site
        ),
        "modes": MODES,
        "cooldown": 1500,
        "saving_memory": SAVING_MEMORY_TEMPLATE.format(site=site),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Render Mindcraft profiles from mcft personas")
    parser.add_argument("--persona-dir", default="configs/personas")
    parser.add_argument("--out", default="integrations/mindcraft/profiles")
    parser.add_argument("--model", default="qwen3.6:35b")
    parser.add_argument("--embedding", default="ollama/qwen3-embedding:0.6b")
    parser.add_argument("--site", default="(95, 85, -283)", help="home site coordinates")
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    personas = load_all_personas(Path(args.persona_dir))
    for persona in personas.values():
        profile = render_profile(persona, args.model, args.embedding, args.site)
        path = out_dir / f"{persona.id}.json"
        path.write_text(json.dumps(profile, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
