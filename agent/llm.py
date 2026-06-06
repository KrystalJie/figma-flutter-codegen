from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
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


class DeepSeekLLMClient:
    """LLMClient backed by the DeepSeek API (OpenAI-compatible chat endpoint).

    Talks to ``POST {base_url}/chat/completions`` with a Bearer token, using
    only the standard library (same style as ``figma_client``) — no extra
    dependency. DeepSeek caches repeated prompt prefixes server-side, so there
    is no client-side caching to configure. Tests inject ``transport`` to
    avoid any network call.

    Configuration falls back to the environment:
    ``DEEPSEEK_API_KEY`` (required), ``DEEPSEEK_MODEL``, ``DEEPSEEK_BASE_URL``.
    """

    DEFAULT_MODEL = "deepseek-v4-flash"
    DEFAULT_BASE_URL = "https://api.deepseek.com"

    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        max_tokens: int = 8192,
        transport=None,
    ) -> None:
        self._model = model or os.environ.get("DEEPSEEK_MODEL") or self.DEFAULT_MODEL
        self._api_key = api_key or os.environ.get("DEEPSEEK_API_KEY")
        self._base_url = (
            base_url or os.environ.get("DEEPSEEK_BASE_URL") or self.DEFAULT_BASE_URL
        ).rstrip("/")
        self._max_tokens = max_tokens
        # transport(url, headers, body) -> parsed JSON dict; defaults to urllib.
        self._transport = transport or _post_json

    def complete(self, prompt: str) -> str:
        if not self._api_key:
            raise ValueError("DEEPSEEK_API_KEY is not set")
        body = {
            "model": self._model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": self._max_tokens,
            "stream": False,
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        data = self._transport(f"{self._base_url}/chat/completions", headers, body)
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ValueError(f"unexpected DeepSeek response shape: {data!r}") from exc


def _post_json(url: str, headers: dict, body: dict) -> dict:
    """POST a JSON body and return the parsed JSON response (stdlib only)."""
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        raise ValueError(f"DeepSeek API error {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise ValueError(f"DeepSeek API unreachable: {exc.reason}") from exc


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
