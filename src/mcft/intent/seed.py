"""Seed the standard homestead show graph (mirrors ops/soft_reset.py phases)."""

from __future__ import annotations

from mcft.intent.model import Coords, IntentGraph, IntentNode


def seed_homestead(site: Coords, personas: dict[str, dict[str, float]]) -> IntentGraph:
    """Build the mission tree: values + homestead root + ordered phase goals.

    personas: {"sable": {"craftsmanship": 0.8, ...}, "jolt": {...}}
    Value weights come from persona YAMLs; anchors inherit from the root.
    """
    g = IntentGraph()

    value_names = sorted({v for weights in personas.values() for v in weights})
    for name in value_names:
        g.add(
            IntentNode(
                id=f"val_{name[:6]}",
                kind="value",
                title=name,
                weights={p: w[name] for p, w in personas.items() if name in w},
            )
        )

    root = g.add(
        IntentNode(
            id="homestead",
            kind="goal",
            title="a permanent team homestead",
            why="a home base makes every future adventure possible - and it's ours",
            anchor=site,
        )
    )

    phases = [
        ("walls", "finish the house walls", "shelter comes before everything else"),
        ("roof", "flat roof over the house", "a house without a roof is a pen"),
        ("door", "hang the front door", "keep the night outside"),
        ("farm", "wheat farm within 10 blocks", "food security ends the scavenging"),
        ("improve", "torches, fences, decorations", "make it a home, not a box"),
    ]
    for node_id, title, why in phases:
        g.add(IntentNode(id=node_id, kind="goal", title=title, why=why, parent=root.id))

    for persona in personas:
        g.active[persona] = "walls"
    return g
