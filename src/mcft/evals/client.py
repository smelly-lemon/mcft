"""Chat clients for the eval harness.

All model access goes through the OpenAI-compatible chat-completions
abstraction (core principle 4). MockClient is the only client exercised in
dry runs and tests.
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import Protocol

import httpx

from mcft.schemas import Message


@dataclass
class ChatResponse:
    content: str
    thinking: str | None
    latency_ms: float


class ChatClient(Protocol):
    def chat(self, messages: list[Message], *, model: str) -> ChatResponse: ...


class OpenAICompatClient:
    """Minimal OpenAI-compatible chat client. Not exercised in dry runs or
    tests beyond construction."""

    def __init__(self, base_url: str, timeout_s: float = 60.0) -> None:
        self.base_url = base_url.rstrip("/")
        self._client = httpx.Client(timeout=timeout_s)

    def chat(self, messages: list[Message], *, model: str) -> ChatResponse:
        payload = {
            "model": model,
            "messages": [m.model_dump() for m in messages],
            "stream": False,
        }
        start = time.perf_counter()
        response = self._client.post(f"{self.base_url}/chat/completions", json=payload)
        latency_ms = (time.perf_counter() - start) * 1000.0
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        return ChatResponse(content=content, thinking=None, latency_ms=latency_ms)


_MOCK_CYCLE = [
    "Scoping the area.",
    '!collectBlocks("oak_log", 10)',
    "Progress is acceptable.",
    '!craftRecipe("crafting_table", 1)',
]


class MockClient:
    """Deterministic mock: same seed => identical sequence of responses and
    latencies. The runner constructs a fresh MockClient(seed=seed) per
    episode so every episode's second step is the !collectBlocks command."""

    def __init__(self, seed: int = 0) -> None:
        self._rng = random.Random(seed)
        self._calls = 0

    def chat(self, messages: list[Message], *, model: str) -> ChatResponse:
        content = _MOCK_CYCLE[self._calls % len(_MOCK_CYCLE)]
        self._calls += 1
        latency_ms = max(50.0, self._rng.gauss(400.0, 150.0))
        return ChatResponse(content=content, thinking=None, latency_ms=latency_ms)
