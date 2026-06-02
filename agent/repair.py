from __future__ import annotations

from typing import Protocol

from agent.validator import ValidationResult


class LLMClient(Protocol):
    """Minimal LLM interface used by the repair loop.

    Implementations take a single prompt string and return the model's
    completion. Tests substitute a fake client so no network calls happen.
    """

    def complete(self, prompt: str) -> str: ...


class StubLLMClient:
    """Default LLMClient placeholder used until a real provider is wired up.

    Implements the protocol but refuses to do work, so `--repair` fails
    loudly with a clear message instead of silently doing nothing.
    """

    def complete(self, prompt: str) -> str:
        raise NotImplementedError(
            "no LLM client is configured; --repair requires a real "
            "LLMClient implementation"
        )


_PROMPT_TEMPLATE = """\
You are fixing a Flutter (Dart) source file that fails `flutter analyze`.

Return ONLY the full corrected contents of the Dart file. Do not include
explanations, commentary, or markdown code fences. The response must be a
complete, valid Dart file that compiles cleanly.

--- flutter analyze output ---
{log}
--- end flutter analyze output ---

--- current Dart source ---
{source}
--- end current Dart source ---
"""


def build_prompt(dart_source: str, result: ValidationResult) -> str:
    """Build the repair prompt sent to the LLM."""
    return _PROMPT_TEMPLATE.format(
        log=result.raw_log.strip() or "(no log output)",
        source=dart_source,
    )


def repair(
    dart_source: str,
    result: ValidationResult,
    client: LLMClient,
) -> str:
    """Ask the LLM to return a corrected Dart file.

    If `result.success` is True, the original source is returned unchanged
    and the client is not called. Otherwise the model response is stripped
    of surrounding whitespace and any wrapping markdown code fence.
    """
    if result.success:
        return dart_source

    prompt = build_prompt(dart_source, result)
    response = client.complete(prompt)
    repaired = _strip_code_fence(response).strip()
    if not repaired:
        raise ValueError("LLM returned empty repair response")
    if not repaired.endswith("\n"):
        repaired += "\n"
    return repaired


def _strip_code_fence(text: str) -> str:
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
