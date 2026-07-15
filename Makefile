.PHONY: setup test lint fmt eval-dry

setup:
	uv sync

test:
	uv run pytest

lint:
	uv run ruff format --check .
	uv run ruff check .

fmt:
	uv run ruff format .
	uv run ruff check --fix .

eval-dry:
	uv run python -m mcft.evals.runner --dry-run --personas sable,jolt
