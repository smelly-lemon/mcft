"""Seed mcft_intent.json for a Mindcraft deployment (run on the LAPTOP).

Builds the homestead mission graph from the Python source of truth
(mcft.intent.seed) with persona value weights from configs/personas/*.yaml,
then prints scp instructions. The JS runtime round-trips this file.

Usage: uv run python integrations/mindcraft/ops/seed_intent.py --site 0,86,64
"""

from __future__ import annotations

import argparse
from pathlib import Path

import yaml

from mcft.intent.seed import seed_homestead

REPO = Path(__file__).resolve().parents[3]
PERSONAS = ("sable", "jolt")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--site", required=True, help="X,Y,Z of home site")
    parser.add_argument("--out", default=str(REPO / "integrations/mindcraft/mcft_intent.json"))
    args = parser.parse_args()
    x, y, z = (int(v) for v in args.site.split(","))

    personas: dict[str, dict[str, float]] = {}
    for pid in PERSONAS:
        cfg = yaml.safe_load((REPO / "configs" / "personas" / f"{pid}.yaml").read_text())
        personas[pid] = {k: float(v) for k, v in (cfg.get("values") or {}).items()}
        assert personas[pid], f"{pid}.yaml has no values block"

    graph = seed_homestead((x, y, z), personas)
    graph.save(args.out)
    print(f"wrote {args.out}")
    print(f"deploy: scp {args.out} tim@tim4:Desktop/mindcraft/mcft_intent.json")


if __name__ == "__main__":
    main()
