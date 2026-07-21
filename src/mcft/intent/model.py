"""Intent graph v1: code-owned goal tree with a values layer.

Design (docs/intent-graph-design.md): the graph is owned by code; models
propose ops through a narrow, validated interface (`IntentGraph.apply_op`).
The prompt never sees the whole graph - only `render_path_view` (~200 tokens).

v1 is a tree (single parent). The "network" upgrade (multiple parents, causal
edges) is deferred until models prove they can drive this op surface.
"""

from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from mcft.schemas import StrictModel, new_id, utc_now

Coords = tuple[int, int, int]

# Anchor conflicts: a proposed work location further than this from the
# effective anchor is rejected (the Sable 2026-07-20 Y-blend class).
ANCHOR_TOLERANCE_HORIZ = 40
ANCHOR_TOLERANCE_DEPTH = 12

# Blocks decay: "blocked" means step away, not dead. The era-F soak
# (2026-07-21) deadlocked in <2h when permanent blocks burned through the
# whole tree and no op could revive anything.
BLOCK_COOLDOWN_MINUTES = 20


class IntentNode(StrictModel):
    id: str = Field(default_factory=lambda: new_id()[:8])
    kind: Literal["value", "goal", "task"]
    title: str
    # rationale on the edge to the parent ("why does this serve its parent?")
    why: str = ""
    parent: str | None = None            # None only for roots (values, mission root)
    status: Literal["active", "done", "blocked", "abandoned"] = "active"
    owner: str = "shared"                # persona id or "shared"
    anchor: Coords | None = None         # inherited from nearest ancestor if None
    created_by: Literal["system", "persona", "operator", "viewer"] = "system"
    created_at: str = Field(default_factory=lambda: utc_now().isoformat())
    # values only: per-persona weights, e.g. {"sable": 0.8}
    weights: dict[str, float] = Field(default_factory=dict)
    # goals/tasks: how much this node serves each value, e.g. {"safety": 0.8}.
    # This is the steering surface: alignment(bot, node) ranks sibling choices.
    serves_values: dict[str, float] = Field(default_factory=dict)
    status_reason: str = ""
    # blocked nodes reactivate after this ISO timestamp (see _expire_blocks)
    blocked_until: str | None = None


class OpResult(StrictModel):
    ok: bool
    message: str                         # user-facing feedback, command-style
    node_id: str | None = None


class IntentGraph(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nodes: dict[str, IntentNode] = Field(default_factory=dict)
    # each bot's current working leaf
    active: dict[str, str] = Field(default_factory=dict)

    # -- construction ------------------------------------------------------

    def add(self, node: IntentNode) -> IntentNode:
        if node.parent is not None:
            parent = self.nodes.get(node.parent)
            if parent is None:
                raise ValueError(f"parent {node.parent!r} does not exist")
            if parent.kind == "value":
                raise ValueError("value nodes cannot have children; goals serve values implicitly")
            if parent.status in ("done", "abandoned"):
                raise ValueError(f"parent {parent.title!r} is {parent.status}")
        elif node.kind != "value" and any(
            n.kind != "value" and n.parent is None for n in self.nodes.values()
        ):
            raise ValueError("only one mission root allowed in v1")
        self.nodes[node.id] = node
        return node

    # -- queries -----------------------------------------------------------

    def path(self, node_id: str) -> list[IntentNode]:
        """Root-to-node chain."""
        chain: list[IntentNode] = []
        seen: set[str] = set()
        cur: str | None = node_id
        while cur is not None:
            if cur in seen:
                raise ValueError(f"cycle detected at {cur!r}")
            seen.add(cur)
            node = self.nodes[cur]
            chain.append(node)
            cur = node.parent
        chain.reverse()
        return chain

    def children(self, node_id: str) -> list[IntentNode]:
        return [n for n in self.nodes.values() if n.parent == node_id]

    def effective_anchor(self, node_id: str) -> Coords | None:
        for node in reversed(self.path(node_id)):
            if node.anchor is not None:
                return node.anchor
        return None

    def anchor_conflict(self, node_id: str, coords: Coords) -> str | None:
        """Return a human-readable conflict description, or None if fine."""
        anchor = self.effective_anchor(node_id)
        if anchor is None:
            return None
        dx, dy, dz = (coords[0] - anchor[0], coords[1] - anchor[1], coords[2] - anchor[2])
        horiz = (dx * dx + dz * dz) ** 0.5
        if horiz > ANCHOR_TOLERANCE_HORIZ or dy < -ANCHOR_TOLERANCE_DEPTH:
            return (
                f"({coords[0]}, {coords[1]}, {coords[2]}) is {horiz:.0f} blocks out / "
                f"{-dy if dy < 0 else 0} blocks below the anchor {anchor} inherited by "
                f"this goal - likely a corrupted coordinate"
            )
        return None

    def orphans(self) -> list[IntentNode]:
        """Active non-value nodes whose parent chain contains a dead node."""
        out = []
        for node in self.nodes.values():
            if node.kind == "value" or node.status != "active":
                continue
            chain = self.path(node.id)[:-1]
            if any(p.status in ("done", "abandoned", "blocked") for p in chain):
                out.append(node)
        return out

    def values_for(self, persona: str, top: int = 3) -> list[tuple[str, float]]:
        vals = [
            (n.title, n.weights.get(persona, 0.0))
            for n in self.nodes.values()
            if n.kind == "value" and n.weights.get(persona, 0.0) > 0
        ]
        vals.sort(key=lambda t: -t[1])
        return vals[:top]

    def alignment(self, persona: str, node_id: str) -> float:
        """How well a goal serves this persona's values (the steering signal).

        Sums persona_weight * serves_values over the node and its ancestors
        (nearer nodes count fully, ancestors half) so tasks inherit purpose.
        """
        by_title = {
            n.title: n.weights.get(persona, 0.0)
            for n in self.nodes.values()
            if n.kind == "value"
        }
        score = 0.0
        chain = [n for n in self.path(node_id) if n.kind != "value"]
        for i, node in enumerate(reversed(chain)):
            factor = 1.0 if i == 0 else 0.5
            for value_title, serve in node.serves_values.items():
                score += factor * serve * by_title.get(value_title, 0.0)
        return score

    # -- self-healing --------------------------------------------------------

    def _expire_blocks(self) -> None:
        """Reactivate expired blocks; if nothing is open at all, heal the tree.

        Called before every op and view so the graph can never stay in the
        all-blocked deadlock the era-F soak produced.
        """
        now = utc_now().isoformat()
        goals = [n for n in self.nodes.values() if n.kind != "value"]
        for node in goals:
            if (
                node.status == "blocked"
                and node.blocked_until is not None
                and node.blocked_until <= now
            ):
                node.status = "active"
                node.status_reason = "block expired"
                node.blocked_until = None
        if goals and not any(n.status == "active" for n in goals):
            for node in goals:
                if node.status == "blocked":
                    node.status = "active"
                    node.status_reason = "auto-heal: tree had no open goals"
                    node.blocked_until = None
        # pointers must reference open goals (a partner's loop-breaker can
        # block the node this bot is standing on)
        for bot, node_id in list(self.active.items()):
            node = self.nodes.get(node_id)
            if node is None or node.status != "active":
                start = node.parent if node is not None else self._mission_root()
                leaf = self._next_leaf(bot, start)
                if leaf is not None:
                    self.active[bot] = leaf.id
                else:
                    self.active.pop(bot)

    # -- ops (the model-facing surface) -------------------------------------

    def apply_op(self, bot: str, op: str, **kwargs: str) -> OpResult:
        """Single entry point for model-proposed ops. Never raises."""
        try:
            self._expire_blocks()
            handler = {
                "goalDone": self._op_done,
                "goalAdd": self._op_add,
                "goalSwitch": self._op_switch,
            }.get(op)
            if handler is None:
                return OpResult(ok=False, message=f"unknown intent op {op!r}")
            return handler(bot, **kwargs)
        except (KeyError, ValueError, TypeError) as exc:
            return OpResult(ok=False, message=f"intent op rejected: {exc}")

    def _op_done(self, bot: str, reason: str = "") -> OpResult:
        node_id = self.active.get(bot)
        if node_id is None:
            return OpResult(ok=False, message="you have no active goal to complete")
        node = self.nodes[node_id]
        if self.children(node_id) and any(
            c.status == "active" for c in self.children(node_id)
        ):
            return OpResult(
                ok=False,
                message=f"{node.title!r} still has active subgoals - finish or abandon them first",
            )
        node.status = "done"
        node.status_reason = reason
        nxt = self._next_leaf(bot, node.parent)
        if nxt is not None:
            self.active[bot] = nxt.id
            because = nxt.why or "it serves the mission"
            return OpResult(
                ok=True,
                message=f"done: {node.title}. Next up: {nxt.title} (because {because})",
                node_id=nxt.id,
            )
        self.active.pop(bot, None)
        return OpResult(
            ok=True,
            message=f"done: {node.title}. No open subgoals - pick or add one.",
            node_id=None,
        )

    def _op_add(
        self,
        bot: str,
        title: str = "",
        why: str = "",
        parent_id: str = "",
        anchor: Coords | None = None,
        created_by: str = "persona",
    ) -> OpResult:
        if not title.strip():
            return OpResult(ok=False, message="goalAdd needs a title")
        if not why.strip():
            return OpResult(
                ok=False, message="goalAdd needs a why - every goal must serve its parent"
            )
        parent = parent_id or self.active.get(bot) or self._mission_root() or ""
        if parent not in self.nodes:
            return OpResult(ok=False, message=f"parent {parent!r} not found")
        node = self.add(
            IntentNode(
                kind="task",
                title=title.strip(),
                why=why.strip(),
                parent=parent,
                owner=bot,
                anchor=anchor,
                created_by=created_by,  # type: ignore[arg-type]
            )
        )
        self.active[bot] = node.id
        return OpResult(ok=True, message=f"added and switched to: {node.title}", node_id=node.id)

    def _op_switch(self, bot: str, node_id: str = "", why: str = "") -> OpResult:
        node = self.nodes.get(node_id) or self._by_title(node_id)
        if node is None:
            return OpResult(ok=False, message=f"no such goal {node_id!r}")
        if node.kind == "value":
            return OpResult(
                ok=False, message="cannot work a value directly - pick a goal that serves it"
            )
        if node.status == "blocked":
            # switching to a blocked goal is a deliberate revive (escape hatch)
            node.status = "active"
            node.status_reason = f"revived by {bot}: {why}" if why else f"revived by {bot}"
            node.blocked_until = None
        elif node.status != "active":
            return OpResult(ok=False, message=f"{node.title!r} is {node.status}")
        self.active[bot] = node.id
        return OpResult(ok=True, message=f"switched to: {node.title}", node_id=node.id)

    def _by_title(self, text: str) -> IntentNode | None:
        """Models often pass titles instead of ids; accept an exact title match."""
        want = text.strip().lower()
        matches = [
            n
            for n in self.nodes.values()
            if n.kind != "value" and n.title.strip().lower() == want
        ]
        return matches[0] if len(matches) == 1 else None

    def _mission_root(self) -> str | None:
        for node in self.nodes.values():
            if node.kind != "value" and node.parent is None:
                return node.id
        return None

    # -- code-driven ops (loop-breaker / siteguard integration) --------------

    def block(self, node_id: str, reason: str) -> list[IntentNode]:
        """Step away from a stuck goal; return sibling alternatives.

        Era-F soak lesson: only persona-created tasks actually change status
        (with a decay timer). System mission goals are structure - the
        loop-breaker steers the bot's pointer away but must never kill them.
        """
        self._expire_blocks()
        node = self.nodes[node_id]
        if node.created_by != "system":
            node.status = "blocked"
            node.status_reason = reason
            until = utc_now() + timedelta(minutes=BLOCK_COOLDOWN_MINUTES)
            node.blocked_until = until.isoformat()
        if node.parent is None:
            return []
        return [
            c
            for c in self.children(node.parent)
            if c.status == "active" and c.id != node_id
        ]

    def _next_leaf(self, bot: str, start: str | None) -> IntentNode | None:
        """Nearest active descendant leaf under `start` (or any open node)."""
        def first_active_leaf(node_id: str) -> IntentNode | None:
            kids = [c for c in self.children(node_id) if c.status == "active"]
            if not kids:
                node = self.nodes[node_id]
                return node if node.status == "active" and node.kind != "value" else None
            for kid in kids:
                leaf = first_active_leaf(kid.id)
                if leaf is not None:
                    return leaf
            return None

        cur = start
        while cur is not None:
            leaf = first_active_leaf(cur)
            if leaf is not None:
                return leaf
            cur = self.nodes[cur].parent
        return None

    # -- prompt rendering ----------------------------------------------------

    def render_path_view(self, bot: str, partner: str | None = None, max_siblings: int = 3) -> str:
        """The INTENT prompt section. Budget: ~200 tokens."""
        self._expire_blocks()
        lines: list[str] = ["INTENT (why you are doing what you are doing):"]
        vals = self.values_for(bot)
        if vals:
            lines.append("You value: " + ", ".join(f"{t} ({w:.1f})" for t, w in vals))
        node_id = self.active.get(bot)
        if node_id is None:
            # pointerless bot: auto-point at the earliest open leaf rather
            # than asking the model to recover (era-F showed it fumbles that)
            leaf = self._next_leaf(bot, self._mission_root())
            if leaf is not None:
                self.active[bot] = leaf.id
                node_id = leaf.id
        if node_id is None:
            lines.append("No active goal. Add one with !goalAdd.")
        else:
            chain = self.path(node_id)
            for depth, node in enumerate(c for c in chain if c.kind != "value"):
                marker = "NOW:" if node.id == node_id else "    " * 0 + "->"
                why = f" - because {node.why}" if node.why else ""
                anchor = f" @ {node.anchor}" if node.anchor else ""
                lines.append(f"{'  ' * depth}{marker} [{node.id}] {node.title}{anchor}{why}")
            parent = chain[-1].parent
            if parent is not None:
                sibs = [
                    c for c in self.children(parent)
                    if c.id != node_id and c.status == "active"
                ]
                # steering: siblings most aligned with this persona's values first
                sibs.sort(key=lambda s: -self.alignment(bot, s.id))
                sibs = sibs[:max_siblings]
                if sibs:
                    lines.append(
                        "Alternatives serving the same parent: "
                        + "; ".join(f"[{s.id}] {s.title}" for s in sibs)
                    )
        if partner is not None:
            pid = self.active.get(partner)
            if pid is not None:
                ptitle = self.nodes[pid].title
                lines.append(f"{partner} is on: {ptitle}")
        return "\n".join(lines)

    # -- persistence ---------------------------------------------------------

    def save(self, path: str | Path) -> None:
        Path(path).write_text(self.model_dump_json(indent=1) + "\n", encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> IntentGraph:
        return cls.model_validate(json.loads(Path(path).read_text(encoding="utf-8")))
