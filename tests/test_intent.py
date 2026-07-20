from __future__ import annotations

import pytest

from mcft.intent import IntentGraph, IntentNode
from mcft.intent.seed import seed_homestead

SITE = (95, 85, -283)
PERSONAS = {
    "sable": {"craftsmanship": 0.8, "curiosity": 0.5},
    "jolt": {"speed": 0.9, "craftsmanship": 0.2},
}


@pytest.fixture()
def graph() -> IntentGraph:
    return seed_homestead(SITE, PERSONAS)


def test_seed_shape(graph: IntentGraph) -> None:
    assert graph.active == {"sable": "walls", "jolt": "walls"}
    assert graph.effective_anchor("walls") == SITE  # inherited from root
    assert [t for t, _ in graph.values_for("jolt")][0] == "speed"


def test_single_mission_root(graph: IntentGraph) -> None:
    with pytest.raises(ValueError, match="one mission root"):
        graph.add(IntentNode(kind="goal", title="second base"))


def test_op_add_requires_why(graph: IntentGraph) -> None:
    res = graph.apply_op("sable", "goalAdd", title="gather cobble")
    assert not res.ok and "why" in res.message


def test_op_add_and_done_walks_back_up(graph: IntentGraph) -> None:
    res = graph.apply_op(
        "sable", "goalAdd", title="gather 32 cobblestone", why="walls need stone"
    )
    assert res.ok
    assert graph.active["sable"] == res.node_id
    assert graph.nodes[res.node_id].created_by == "persona"

    done = graph.apply_op("sable", "goalDone", reason="chest stocked")
    assert done.ok
    # walks back to the nearest open leaf under the same parent chain
    assert graph.active["sable"] == "walls"
    assert "walls" in done.message


def test_done_blocked_by_active_children(graph: IntentGraph) -> None:
    graph.apply_op("sable", "goalAdd", title="gather stone", why="walls need it")
    graph.apply_op("sable", "goalSwitch", node_id="walls")
    res = graph.apply_op("sable", "goalDone")
    assert not res.ok and "subgoals" in res.message


def test_op_switch_rejects_values_and_unknown(graph: IntentGraph) -> None:
    assert not graph.apply_op("sable", "goalSwitch", node_id="val_speed").ok
    assert not graph.apply_op("sable", "goalSwitch", node_id="nope").ok


def test_ops_never_raise(graph: IntentGraph) -> None:
    assert not graph.apply_op("sable", "goalTeleport").ok
    assert not graph.apply_op("sable", "goalAdd", title="x", why="y", parent_id="nope").ok


def test_anchor_conflict_catches_y_blend(graph: IntentGraph) -> None:
    # The Sable 2026-07-20 case: X/Z near site, Y hallucinated 26+ blocks down.
    conflict = graph.anchor_conflict("walls", (94, 59, -283))
    assert conflict is not None and "below" in conflict
    assert graph.anchor_conflict("walls", (97, 86, -281)) is None
    # Horizontal runaway is also caught.
    assert graph.anchor_conflict("walls", (200, 85, -283)) is not None


def test_block_returns_siblings(graph: IntentGraph) -> None:
    siblings = graph.block("walls", "repetition loop on placeHere")
    titles = {s.id for s in siblings}
    assert "roof" in titles and "walls" not in titles
    assert graph.nodes["walls"].status == "blocked"


def test_orphans_detected(graph: IntentGraph) -> None:
    res = graph.apply_op("jolt", "goalAdd", title="cobble run", why="walls need stone")
    graph.block("walls", "stuck")
    orphaned = {n.id for n in graph.orphans()}
    assert res.node_id in orphaned


def test_render_path_view_budget_and_content(graph: IntentGraph) -> None:
    graph.apply_op("sable", "goalAdd", title="gather 32 cobblestone", why="walls need stone")
    view = graph.render_path_view("sable", partner="jolt")
    assert "INTENT" in view
    assert "because walls need stone" in view
    assert "jolt is on:" in view
    assert "craftsmanship" in view
    # prompt budget: ~200 tokens ~= 800 chars
    assert len(view) < 900


def test_round_trip(tmp_path, graph: IntentGraph) -> None:
    graph.apply_op("sable", "goalAdd", title="gather stone", why="walls need it")
    p = tmp_path / "intent.json"
    graph.save(p)
    loaded = IntentGraph.load(p)
    assert loaded.active == graph.active
    assert loaded.nodes.keys() == graph.nodes.keys()
