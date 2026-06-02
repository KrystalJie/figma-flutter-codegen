from __future__ import annotations

from agent.llm import LLMClient, StubLLMClient, strip_code_fence
from agent.validator import ValidationResult

__all__ = ["LLMClient", "StubLLMClient", "build_prompt", "repair"]


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
    repaired = strip_code_fence(response).strip()
    if not repaired:
        raise ValueError("LLM returned empty repair response")
    if not repaired.endswith("\n"):
        repaired += "\n"
    return repaired
