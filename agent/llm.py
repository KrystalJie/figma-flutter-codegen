from __future__ import annotations

from typing import Protocol


class LLMClient(Protocol):
    """Minimal LLM interface shared by the planner and repair loops.

    Implementations take a single prompt string and return the model's
    completion. Tests substitute a fake client so no network calls happen.
    """

    def complete(self, prompt: str) -> str: ...


class StubLLMClient:
    """Default LLMClient placeholder used until a real provider is wired up.

    Implements the protocol but refuses to do work, so LLM-backed features
    (`--llm`, `--repair`) fail loudly with a clear message instead of
    silently doing nothing.
    """

    def complete(self, prompt: str) -> str:
        raise NotImplementedError(
            "no LLM client is configured; this feature requires a real "
            "LLMClient implementation"
        )


def strip_code_fence(text: str) -> str:
    """Remove a single wrapping ```...``` fence if present."""
    stripped = text.strip()
    if not stripped.startswith("```"):
        return text
    first_newline = stripped.find("\n")
    if first_newline == -1:
        return text
    body = stripped[first_newline + 1 :]
    if body.endswith("```"):
        body = body[: -len("```")]
    return body
