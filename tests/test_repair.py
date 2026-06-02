from __future__ import annotations

import pytest

from agent import repair
from agent.repair import LLMClient, build_prompt
from agent.validator import ValidationResult


class FakeLLM:
    """Records the prompt it received and returns a canned response."""

    def __init__(self, response: str) -> None:
        self.response = response
        self.calls: list[str] = []

    def complete(self, prompt: str) -> str:
        self.calls.append(prompt)
        return self.response


BROKEN = "import 'package:flutter/material.dart'\n\nclass S {}\n"
FIXED = "import 'package:flutter/material.dart';\n\nclass S {}\n"
FAIL_LOG = "lib/generated_screen.dart:1:42: error: expected ';' after this.\n"


def _failure(log: str = FAIL_LOG) -> ValidationResult:
    return ValidationResult(success=False, raw_log=log)


def _success(log: str = "No issues found!\n") -> ValidationResult:
    return ValidationResult(success=True, raw_log=log)


def test_returns_source_unchanged_when_validation_succeeded() -> None:
    client = FakeLLM(response="should not be used")
    out = repair.repair(BROKEN, _success(), client)
    assert out == BROKEN
    assert client.calls == []


def test_calls_llm_and_returns_repaired_source() -> None:
    client = FakeLLM(response=FIXED)
    out = repair.repair(BROKEN, _failure(), client)
    assert out == FIXED
    assert len(client.calls) == 1


def test_prompt_includes_source_and_analyze_log() -> None:
    client = FakeLLM(response=FIXED)
    repair.repair(BROKEN, _failure("ERR: missing semicolon"), client)
    prompt = client.calls[0]
    assert BROKEN in prompt
    assert "ERR: missing semicolon" in prompt


def test_prompt_asks_for_full_corrected_file_only() -> None:
    client = FakeLLM(response=FIXED)
    repair.repair(BROKEN, _failure(), client)
    prompt = client.calls[0].lower()
    assert "only" in prompt
    assert "full" in prompt or "complete" in prompt
    assert "dart" in prompt


def test_strips_markdown_code_fence_with_language() -> None:
    fenced = "```dart\n" + FIXED.rstrip("\n") + "\n```"
    client = FakeLLM(response=fenced)
    out = repair.repair(BROKEN, _failure(), client)
    assert out == FIXED


def test_strips_markdown_code_fence_without_language() -> None:
    fenced = "```\n" + FIXED.rstrip("\n") + "\n```"
    client = FakeLLM(response=fenced)
    out = repair.repair(BROKEN, _failure(), client)
    assert out == FIXED


def test_trailing_whitespace_is_normalized() -> None:
    client = FakeLLM(response="   " + FIXED.rstrip("\n") + "   \n\n")
    out = repair.repair(BROKEN, _failure(), client)
    assert out == FIXED


def test_response_without_trailing_newline_gets_one() -> None:
    client = FakeLLM(response=FIXED.rstrip("\n"))
    out = repair.repair(BROKEN, _failure(), client)
    assert out.endswith("\n")
    assert out == FIXED


def test_empty_response_raises() -> None:
    client = FakeLLM(response="   \n  ")
    with pytest.raises(ValueError, match="empty"):
        repair.repair(BROKEN, _failure(), client)


def test_empty_log_is_handled() -> None:
    client = FakeLLM(response=FIXED)
    out = repair.repair(BROKEN, ValidationResult(success=False, raw_log=""), client)
    assert out == FIXED
    assert "no log output" in client.calls[0]


def test_build_prompt_is_deterministic() -> None:
    p1 = build_prompt(BROKEN, _failure())
    p2 = build_prompt(BROKEN, _failure())
    assert p1 == p2


def test_fake_llm_satisfies_protocol() -> None:
    client: LLMClient = FakeLLM(response=FIXED)
    assert client.complete("ping") == FIXED
