from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from mcft.personas import (
    ACTION_CONTRACT,
    assemble_system_prompt,
    load_all_personas,
    load_persona,
)


def test_persona_loader_valid(persona_dir: Path) -> None:
    personas = load_all_personas(persona_dir)
    assert set(personas) == {"sable", "jolt", "herald"}
    for pid, persona in personas.items():
        assert persona.id == pid


def test_persona_loader_rejects_missing_field(persona_dir: Path, tmp_path: Path) -> None:
    lines = (persona_dir / "sable.yaml").read_text(encoding="utf-8").splitlines(keepends=True)
    # Drop the folded `voice: >` scalar (its key line and indented continuation lines).
    out: list[str] = []
    in_voice = False
    for line in lines:
        if line.startswith("voice:"):
            in_voice = True
            continue
        if in_voice and line.startswith("  "):
            continue
        in_voice = False
        out.append(line)
    broken = tmp_path / "broken.yaml"
    broken.write_text("".join(out), encoding="utf-8")
    with pytest.raises(ValidationError):
        load_persona(broken)


def test_contract_block_identical_across_personas(persona_dir: Path) -> None:
    personas = load_all_personas(persona_dir)
    for persona in personas.values():
        prompt = assemble_system_prompt(persona, "gather wood")
        assert prompt.count(ACTION_CONTRACT) == 1


def test_personas_differ_outside_contract(persona_dir: Path) -> None:
    personas = load_all_personas(persona_dir)
    sable = assemble_system_prompt(personas["sable"], "gather wood")
    jolt = assemble_system_prompt(personas["jolt"], "gather wood")
    assert sable.replace(ACTION_CONTRACT, "") != jolt.replace(ACTION_CONTRACT, "")


def test_task_context_appears_verbatim(persona_dir: Path) -> None:
    personas = load_all_personas(persona_dir)
    prompt = assemble_system_prompt(personas["sable"], "find the river")
    task_section = prompt.split("# Current task")[1]
    assert "find the river" in task_section
