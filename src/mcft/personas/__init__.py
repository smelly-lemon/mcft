"""Persona loading and system-prompt assembly.

The action contract is stored once (action_contract.txt) and appended at
assembly time; it is never duplicated into persona files.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import yaml

from mcft.schemas import StrictModel

# Stripped at load so the module constant is byte-identical to the contract
# block inside assembled prompts (test 5 relies on this).
ACTION_CONTRACT: str = (Path(__file__).parent / "action_contract.txt").read_text(
    encoding="utf-8"
).strip()


class Persona(StrictModel):
    id: str
    display_name: str
    voice: str
    chat_style: list[str]
    boundaries: list[str]


def load_persona(path: Path) -> Persona:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return Persona.model_validate(data)


def load_all_personas(dir: Path) -> dict[str, Persona]:  # noqa: A002
    personas = [load_persona(p) for p in sorted(dir.glob("*.yaml"))]
    return {p.id: p for p in personas}


def assemble_system_prompt(persona: Persona, task_context: str) -> str:
    style = "\n".join(f"- {rule}" for rule in persona.chat_style)
    boundaries = "\n".join(f"- {rule}" for rule in persona.boundaries)
    blocks = [
        f"# Identity\nYou are {persona.display_name}. {persona.voice}",
        f"## Style\n{style}",
        f"## Boundaries\n{boundaries}",
        f"# Current task\n{task_context}",
        f"# Action contract (do not deviate)\n{ACTION_CONTRACT}",
    ]
    return "\n\n".join(block.rstrip() for block in blocks) + "\n"


def system_prompt_hash(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()
