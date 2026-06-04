from __future__ import annotations

import pytest

from agent import figma_client
from agent.figma_client import FigmaError


def test_parse_url_file_form_normalizes_node_id() -> None:
    url = "https://www.figma.com/file/abc123/Title?node-id=1-2&t=x"
    assert figma_client.parse_figma_url(url) == ("abc123", "1:2")


def test_parse_url_design_form() -> None:
    url = "https://www.figma.com/design/KEY9/My-App?node-id=10-20"
    assert figma_client.parse_figma_url(url) == ("KEY9", "10:20")


def test_parse_url_percent_encoded_node_id() -> None:
    url = "https://www.figma.com/file/abc/Title?node-id=1%3A2"
    assert figma_client.parse_figma_url(url) == ("abc", "1:2")


def test_parse_url_without_node_id() -> None:
    assert figma_client.parse_figma_url("https://figma.com/file/abc/Title") == (
        "abc",
        None,
    )


def test_parse_url_malformed_raises() -> None:
    with pytest.raises(FigmaError, match="file key"):
        figma_client.parse_figma_url("https://example.com/not-figma")


def test_resolve_token_prefers_argument() -> None:
    assert figma_client.resolve_token("tok") == "tok"


def test_resolve_token_falls_back_to_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FIGMA_TOKEN", "env-tok")
    assert figma_client.resolve_token() == "env-tok"


def test_resolve_token_missing_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FIGMA_TOKEN", raising=False)
    with pytest.raises(FigmaError, match="FIGMA_TOKEN"):
        figma_client.resolve_token()


def test_fetch_node_unwraps_document(monkeypatch: pytest.MonkeyPatch) -> None:
    raw = {"nodes": {"1:2": {"document": {"id": "1:2", "type": "FRAME"}}}}
    monkeypatch.setattr(figma_client, "fetch_nodes", lambda *a, **k: raw)
    doc, got_raw = figma_client.fetch_node("key", "1:2", "tok")
    assert doc == {"id": "1:2", "type": "FRAME"}
    assert got_raw is raw


def test_fetch_node_missing_node_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(figma_client, "fetch_nodes", lambda *a, **k: {"nodes": {}})
    with pytest.raises(FigmaError, match="not found"):
        figma_client.fetch_node("key", "1:2", "tok")


def test_fetch_node_requires_node_id() -> None:
    with pytest.raises(FigmaError, match="node id is required"):
        figma_client.fetch_node("key", "", "tok")
