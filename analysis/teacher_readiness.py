"""Deep analysis of all mcft trajectory data before the clean teacher run.

Reads the synced episode corpus (default /tmp/mcft_analysis/episodes) and the
Mindcraft console log, splits by configuration era, and reports:

  1. Era overview: volume, throughput, latency, prompt size
  2. Command usage + failure rates per era
  3. Failure taxonomy (normalized message signatures) for problem commands
  4. Step classification: productive / movement / query / social / recovery
  5. Coordination: handoffs, chest usage, dialogue ratio, pair desync
  6. Site discipline: distance-from-site and underground fractions
  7. Deaths and near-deaths
  8. Repetition and alternation per era
  9. Journal drift: on-mission vs off-mission GOAL lines (log, aggregate)

Stdlib only. Usage: python3 analysis/teacher_readiness.py [data_dir]
"""

from __future__ import annotations

import glob
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

DATA = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/mcft_analysis")
SITE = (95.0, 85.0, -283.0)

# Configuration eras (UTC ISO prefixes compare lexicographically).
ERAS = [
    ("A_dev", "0000", "2026-07-18T21:50"),          # early patches trickling in
    ("B_patched", "2026-07-18T21:50", "2026-07-19T11:23"),  # v2+guards+big memory
    ("X_outage", "2026-07-19T11:23", "2026-07-19T22:10"),   # ollama wedge garbage
    ("C_churn", "2026-07-19T22:10", "2026-07-20T04:00"),    # recovery churn, jolt hole
    ("D_clean", "2026-07-20T04:00", "9999"),        # all guards, clean night
]

SENTINELS = ("No response data", "My brain disconnected")

PROGRESS_CMDS = {
    "!placeHere", "!collectBlocks", "!craftRecipe", "!smeltItem",
    "!attack", "!attackPlayer", "!collectAllBlocks", "!harvest",
}
MOVE_CMDS = {
    "!goToCoordinates", "!goToPlayer", "!moveAway", "!goToBed",
    "!followPlayer", "!goToRememberedPlace", "!searchForBlock",
    "!searchForEntity", "!moveAwayFromEntity", "!digDown",
}
QUERY_CMDS = {
    "!stats", "!inventory", "!nearbyBlocks", "!craftable", "!entities",
    "!viewChest", "!savedPlaces", "!getBlueprint", "!getBlueprintLevel",
    "!listBlueprints", "!help",
}
SOCIAL_CMDS = {"!startConversation", "!endConversation"}
INV_CMDS = {
    "!equip", "!discard", "!putInChest", "!takeFromChest", "!consume",
    "!giveToPlayer", "!givePlayer", "!rememberHere",
}
GOAL_CMDS = {"!goal", "!endGoal", "!restart", "!stay", "!stop", "!setMode"}

MISSION_WORDS = re.compile(
    r"house|wall|roof|door|farm|wheat|homestead|site|build", re.I
)


def era_of(ts: str) -> str:
    for name, lo, hi in ERAS:
        if lo <= ts < hi:
            return name
    return "?"


def norm_msg(msg: str) -> str:
    """Collapse a failure message into a signature bucket."""
    s = re.sub(r"-?\d+(\.\d+)?", "#", msg)
    s = re.sub(r'"[^"]*"', '"..."', s)
    s = s.replace("\n", " ").strip()
    # keep the most informative tail
    return s[-90:]


def pctl(xs: list, p: float):
    if not xs:
        return None
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(len(xs) * p))]


def main() -> None:
    steps_by_era: dict[str, list[dict]] = defaultdict(list)
    for f in glob.glob(str(DATA / "episodes" / "*" / "steps.jsonl")):
        prev, prev2 = None, None
        for line in open(f, encoding="utf-8"):
            try:
                s = json.loads(line)
            except json.JSONDecodeError:
                continue
            out = s.get("model_output") or ""
            s["_rep"] = out == prev and out != ""
            s["_alt"] = out != "" and out == prev2 and out != prev
            prev2, prev = prev, out
            s["_era"] = era_of(s.get("timestamp", ""))
            steps_by_era[s["_era"]].append(s)

    order = [e for e, _, _ in ERAS if e in steps_by_era]

    print("=" * 100)
    print("1. ERA OVERVIEW")
    hdr = (
        f"{'era':<10} {'steps':>6} {'hours':>6} {'st/h':>5} {'lat p50':>8} "
        f"{'lat p95':>8} {'in-chars p50':>13} {'sable':>6} {'jolt':>6}"
    )
    print(hdr)
    for era in order:
        ss = steps_by_era[era]
        ts = sorted(s["timestamp"] for s in ss)
        # active hours: count distinct 10-minute buckets with any step
        buckets = {t[:15] for t in ts}
        hours = len(buckets) / 6
        lat = [s["latency_ms"] for s in ss if s.get("latency_ms")]
        inlen = [len(s.get("model_input") or "") for s in ss]
        per = Counter(s.get("persona_id") for s in ss)
        print(
            f"{era:<10} {len(ss):>6} {hours:>6.1f} {len(ss)/max(hours,0.1):>5.0f} "
            f"{(pctl(lat,0.5) or 0)/1000:>7.1f}s {(pctl(lat,0.95) or 0)/1000:>7.1f}s "
            f"{pctl(inlen,0.5):>13} {per['sable']:>6} {per['jolt']:>6}"
        )

    print()
    print("=" * 100)
    print("2. COMMAND USAGE + FAILURE RATES PER ERA (top commands, fail% | uses)")
    all_cmds = Counter()
    for ss in steps_by_era.values():
        for s in ss:
            if s.get("parsed_command") and s.get("execution_result"):
                all_cmds[s["parsed_command"]] += 1
    top = [c for c, _ in all_cmds.most_common(12)]
    print(f"{'command':<20}" + "".join(f"{e:>18}" for e in order))
    for cmd in top:
        row = f"{cmd:<20}"
        for era in order:
            u = f_ = 0
            for s in steps_by_era[era]:
                if s.get("parsed_command") == cmd and s.get("execution_result"):
                    u += 1
                    if not s["execution_result"].get("ok"):
                        f_ += 1
            row += f"{(100*f_/u if u else float('nan')):>10.0f}% |{u:>5}" if u else f"{'-':>18}"
        print(row)

    print()
    print("=" * 100)
    print("3. FAILURE TAXONOMY (eras C+D, top signatures per problem command)")
    recent = steps_by_era.get("C_churn", []) + steps_by_era.get("D_clean", [])
    for cmd in ("!craftRecipe", "!givePlayer", "!collectBlocks", "!smeltItem", "!placeHere"):
        sigs = Counter()
        u = 0
        for s in recent:
            if s.get("parsed_command") == cmd and s.get("execution_result"):
                u += 1
                er = s["execution_result"]
                if not er.get("ok"):
                    sigs[norm_msg(er.get("message") or "")] += 1
        if not u:
            continue
        print(f"\n{cmd} ({u} uses, {sum(sigs.values())} fails):")
        for m, c in sigs.most_common(4):
            print(f"  {c:4}  ...{m!r}")

    print()
    print("=" * 100)
    print("4. STEP CLASSIFICATION PER ERA (% of steps)")
    cats = ["progress-ok", "progress-fail", "movement", "query", "social",
            "inventory", "goal-mgmt", "chat/none", "sentinel"]
    print(f"{'era':<10}" + "".join(f"{c:>14}" for c in cats))
    for era in order:
        n = len(steps_by_era[era])
        cnt = Counter()
        for s in steps_by_era[era]:
            out = s.get("model_output") or ""
            cmd = s.get("parsed_command")
            er = s.get("execution_result") or {}
            if any(x in out for x in SENTINELS):
                cnt["sentinel"] += 1
            elif cmd in PROGRESS_CMDS:
                cnt["progress-ok" if er.get("ok") else "progress-fail"] += 1
            elif cmd in MOVE_CMDS:
                cnt["movement"] += 1
            elif cmd in QUERY_CMDS:
                cnt["query"] += 1
            elif cmd in SOCIAL_CMDS:
                cnt["social"] += 1
            elif cmd in INV_CMDS:
                cnt["inventory"] += 1
            elif cmd in GOAL_CMDS:
                cnt["goal-mgmt"] += 1
            else:
                cnt["chat/none"] += 1
        print(f"{era:<10}" + "".join(f"{100*cnt[c]/n:>13.1f}%" for c in cats))

    print()
    print("=" * 100)
    print("5. COORDINATION")
    for era in order:
        ss = steps_by_era[era]
        give_u = give_f = chest = conv = 0
        for s in ss:
            cmd, er = s.get("parsed_command"), s.get("execution_result") or {}
            if cmd in ("!givePlayer", "!giveToPlayer") and er:
                give_u += 1
                give_f += 0 if er.get("ok") else 1
            if cmd in ("!putInChest", "!takeFromChest"):
                chest += 1
            if cmd in SOCIAL_CMDS:
                conv += 1
        # pair desync: 10-min buckets where exactly one bot stepped
        b_s = {s["timestamp"][:15] for s in ss if s.get("persona_id") == "sable"}
        b_j = {s["timestamp"][:15] for s in ss if s.get("persona_id") == "jolt"}
        both = len(b_s & b_j)
        solo = len(b_s ^ b_j)
        print(
            f"{era:<10} give {give_f}/{give_u} failed | chest ops {chest:>3} | "
            f"conv cmds {conv:>3} | co-active buckets {both:>4} solo {solo:>4}"
            f" ({100*solo/max(both+solo,1):.0f}% solo)"
        )

    print()
    print("=" * 100)
    print("6. SITE DISCIPLINE (dist from site & underground, per era)")
    for era in order:
        ss = steps_by_era[era]
        dists, under = [], 0
        for s in ss:
            pos = (s.get("game_state") or {}).get("position")
            if not pos:
                continue
            d = math.dist(pos, SITE)
            dists.append(d)
            if pos[1] < 75:
                under += 1
        if not dists:
            continue
        far = sum(1 for d in dists if d > 30)
        print(
            f"{era:<10} dist p50 {pctl(dists,0.5):>6.0f}  p95 {pctl(dists,0.95):>6.0f}  "
            f">30 blocks: {100*far/len(dists):>4.1f}%   underground(y<75): {100*under/len(dists):>4.1f}%"
        )

    print()
    print("=" * 100)
    print("7. DEATHS / NEAR-DEATHS (health from game_state)")
    for era in order:
        ss = sorted(steps_by_era[era], key=lambda s: s["timestamp"])
        lowh = sum(1 for s in ss if (s.get("game_state") or {}).get("health", 20) <= 6)
        deaths = 0
        last_h = {}
        for s in ss:
            gs = s.get("game_state") or {}
            h, pid = gs.get("health"), s.get("persona_id")
            if h is None:
                continue
            if pid in last_h and last_h[pid] <= 4 and h >= 19:
                deaths += 1
            last_h[pid] = h
        print(f"{era:<10} near-death steps (h<=6): {lowh:>4}   likely deaths: {deaths}")

    print()
    print("=" * 100)
    print("8. REPETITION / ALTERNATION PER 1K")
    for era in order:
        ss = steps_by_era[era]
        n = len(ss)
        print(
            f"{era:<10} rep {1000*sum(s['_rep'] for s in ss)/n:>6.1f}   "
            f"alt {1000*sum(s['_alt'] for s in ss)/n:>6.1f}"
        )

    print()
    print("=" * 100)
    print("9. JOURNAL DRIFT (mindcraft.log, aggregate + last-quarter tail)")
    log = (DATA / "mindcraft.log").read_text(encoding="utf-8", errors="replace")
    lines = log.split("\n")
    goals = []
    for i, ln in enumerate(lines):
        if "Memory updated to" in ln:
            block = "\n".join(lines[i : i + 12])
            m = re.search(r"GOAL:\s*(.+)", block)
            if m:
                goals.append((i, m.group(1).strip()[:90]))
    on = sum(1 for _, g in goals if MISSION_WORDS.search(g))
    print(f"journal updates with GOAL line: {len(goals)}; on-mission: {on} "
          f"({100*on/max(len(goals),1):.0f}%)")
    tail = [g for i, g in goals if i > len(lines) * 3 // 4]
    t_on = sum(1 for g in tail if MISSION_WORDS.search(g))
    print(f"last quarter of log: {len(tail)} updates, on-mission {100*t_on/max(len(tail),1):.0f}%")
    off = [g for _, g in goals if not MISSION_WORDS.search(g)]
    print("sample off-mission goals:")
    for g in list(dict.fromkeys(off))[:8]:
        print(f"   {g!r}")

    print()
    print("=" * 100)
    print("10. CHAT CONTENT (step_type == chat)")
    chats = [s for ss in steps_by_era.values() for s in ss if s.get("step_type") == "chat"]
    lens = [len(s.get("model_output") or "") for s in chats]
    print(f"chat steps: {len(chats)}  ({100*len(chats)/sum(len(v) for v in steps_by_era.values()):.1f}% of all)")
    if chats:
        print(f"length p50: {pctl(lens,0.5)} chars")
        for s in chats[-5:]:
            print(f"   [{s['persona_id']}] {(s.get('model_output') or '')[:100]!r}")


if __name__ == "__main__":
    main()
