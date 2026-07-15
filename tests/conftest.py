from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
PERSONA_DIR = REPO_ROOT / "configs" / "personas"


@pytest.fixture
def persona_dir() -> Path:
    return PERSONA_DIR
