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


def test_block_never_kills_system_goals(graph: IntentGraph) -> None:
    # Era-F soak lesson: mission phases are structure; the loop-breaker
    # steers away from them but must not change their status.
    res = graph.apply_op("sable", "block", reason="repetition loop on placeHere")
    assert res.ok
    assert graph.nodes["walls"].status == "active"
    assert graph.active["sable"] != "walls"  # but the pointer moved off it


def test_block_on_persona_task_expires(graph: IntentGraph) -> None:
    res = graph.apply_op("sable", "goalAdd", title="cobble run", why="walls need stone")
    graph.apply_op("sable", "block", reason="stuck")
    node = graph.nodes[res.node_id]
    assert node.status == "blocked" and node.blocked_until is not None
    # decay: force the timer into the past; any op sweeps it back to active
    node.blocked_until = "2020-01-01T00:00:00+00:00"
    graph.apply_op("sable", "goalSwitch", node_id="walls")
    assert graph.nodes[res.node_id].status == "active"


def test_block_steering_does_not_ping_pong(graph: IntentGraph) -> None:
    # Ablation 2026-07-21: F2 doubled alternations because a bot blocked on
    # walls got steered to roof, blocked on roof, and got steered straight
    # back to walls. Fresh step-aways must be excluded from steering.
    visited = ["walls"]
    for _ in range(3):
        res = graph.apply_op("sable", "block", reason="stuck")
        assert res.ok
        assert res.node_id not in visited, f"ping-pong back to {res.node_id}"
        visited.append(res.node_id)


def test_block_falls_back_when_everything_avoided() -> None:
    # two-goal graph: once both are freshly avoided, revisiting beats idling
    g = IntentGraph()
    g.add(IntentNode(id="root", kind="goal", title="tiny base", anchor=(0, 64, 0)))
    g.add(IntentNode(id="a", kind="task", title="dig", parent="root"))
    g.add(IntentNode(id="b", kind="task", title="chop", parent="root"))
    g.active["sable"] = "a"
    assert g.apply_op("sable", "block", reason="x").node_id == "b"
    res = g.apply_op("sable", "block", reason="y")
    assert res.ok and res.node_id is not None  # never left pointerless


def test_switch_clears_step_away_guard(graph: IntentGraph) -> None:
    graph.apply_op("sable", "block", reason="stuck")
    assert "walls" in graph.recent_steps_away["sable"]
    graph.apply_op("sable", "goalSwitch", node_id="walls")  # deliberate return
    assert "walls" not in graph.recent_steps_away.get("sable", {})


def test_all_blocked_tree_heals(graph: IntentGraph) -> None:
    # the exact era-F deadlock: every goal blocked (legacy permanent blocks),
    # no pointers - the next op must auto-heal instead of dead-ending
    for node in graph.nodes.values():
        if node.kind != "value":
            node.status = "blocked"
    graph.active.clear()
    res = graph.apply_op("jolt", "goalAdd", title="restart the walls", why="mission stalled")
    assert res.ok, res.message
    assert graph.nodes["homestead"].status == "active"
    assert graph.nodes[res.node_id].parent == "homestead"  # root fallback


def test_switch_revives_blocked_goal(graph: IntentGraph) -> None:
    res = graph.apply_op("sable", "goalAdd", title="dig clay", why="bricks later")
    graph.apply_op("sable", "block", reason="flooded")
    revived = graph.apply_op("sable", "goalSwitch", node_id=res.node_id, why="water drained")
    assert revived.ok
    assert graph.nodes[res.node_id].status == "active"


def test_switch_accepts_exact_title(graph: IntentGraph) -> None:
    res = graph.apply_op("jolt", "goalSwitch", node_id="flat roof over the house")
    assert res.ok and res.node_id == "roof"


def test_partner_block_repoints_stranded_bot(graph: IntentGraph) -> None:
    # both bots on the same persona subgoal; sable blocks it, stranding jolt
    res = graph.apply_op("sable", "goalAdd", title="plank haul", why="walls need planks")
    graph.apply_op("jolt", "goalSwitch", node_id=res.node_id)
    graph.apply_op("sable", "block", reason="stuck")
    view = graph.render_path_view("jolt")
    assert graph.nodes[graph.active["jolt"]].status == "active"
    assert "NOW:" in view


def test_orphans_detected(graph: IntentGraph) -> None:
    top = graph.apply_op("jolt", "goalAdd", title="cobble run", why="walls need stone")
    sub = graph.apply_op("jolt", "goalAdd", title="find deep vein", why="cobble run needs it")
    graph.nodes[top.node_id].status = "abandoned"
    orphaned = {n.id for n in graph.orphans()}
    assert sub.node_id in orphaned


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


def test_alignment_is_the_steering_signal() -> None:
    personas = {
        "sable": {"craftsmanship": 0.9, "spectacle": 0.1},
        "jolt": {"craftsmanship": 0.2, "spectacle": 0.9},
    }
    g = seed_homestead((0, 86, 64), personas)
    # 'improve' serves spectacle+craftsmanship; 'door' serves safety (unweighted here).
    assert g.alignment("jolt", "improve") > g.alignment("jolt", "door")
    # Sable's craftsmanship makes 'improve' strong for her too, but ranking
    # between personas differs on the spectacle-heavy node.
    assert g.alignment("jolt", "improve") > g.alignment("sable", "improve") - 0.9 * 0.8
    # Tasks inherit half their parent's serves_values.
    g.apply_op("jolt", "goalSwitch", node_id="improve")
    res = g.apply_op("jolt", "goalAdd", title="torch spiral", why="make it shine")
    parent_only = g.alignment("jolt", "improve")
    assert g.alignment("jolt", res.node_id) == pytest.approx(parent_only * 0.5)


def test_render_sorts_siblings_by_alignment() -> None:
    personas = {"jolt": {"spectacle": 1.0}}
    g = seed_homestead((0, 86, 64), personas)
    g.apply_op("jolt", "goalSwitch", node_id="walls")
    view = g.render_path_view("jolt")
    alts = next(line for line in view.splitlines() if line.startswith("Alternatives"))
    # 'improve' (spectacle 0.8) must outrank 'door' (no spectacle) for Jolt.
    assert alts.index("improve") < alts.index("door")
