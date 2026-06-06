from __future__ import annotations

import pytest

from agent.llm import DeepSeekLLMClient, StubLLMClient


def test_stub_client_raises():
    with pytest.raises(NotImplementedError):
        StubLLMClient().complete("anything")


def test_deepseek_complete_builds_request_and_extracts_content():
    captured = {}

    def fake_transport(url, headers, body):
        captured["url"] = url
        captured["headers"] = headers
        captured["body"] = body
        return {"choices": [{"message": {"content": "hello world"}}]}

    client = DeepSeekLLMClient(
        model="deepseek-test",
        api_key="sk-test",
        base_url="https://example.com/",
        transport=fake_transport,
    )
    assert client.complete("ping") == "hello world"

    assert captured["url"] == "https://example.com/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer sk-test"
    assert captured["body"]["model"] == "deepseek-test"
    assert captured["body"]["messages"] == [{"role": "user", "content": "ping"}]
    assert captured["body"]["stream"] is False


def test_deepseek_requires_api_key(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    client = DeepSeekLLMClient(api_key=None, transport=lambda *a: {})
    with pytest.raises(ValueError, match="DEEPSEEK_API_KEY"):
        client.complete("ping")


def test_deepseek_rejects_unexpected_response():
    client = DeepSeekLLMClient(api_key="sk-test", transport=lambda *a: {"oops": 1})
    with pytest.raises(ValueError, match="unexpected DeepSeek response"):
        client.complete("ping")


def test_deepseek_reads_env(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-env")
    monkeypatch.setenv("DEEPSEEK_MODEL", "model-env")
    monkeypatch.setenv("DEEPSEEK_BASE_URL", "https://env.example")
    client = DeepSeekLLMClient(transport=lambda *a: {"choices": [{"message": {"content": "ok"}}]})
    assert client._model == "model-env"
    assert client._api_key == "sk-env"
    assert client._base_url == "https://env.example"
