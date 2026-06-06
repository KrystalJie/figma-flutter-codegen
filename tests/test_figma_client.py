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


def test_extract_styles_returns_top_level_style_map() -> None:
    raw = {
        "nodes": {
            "1:2": {
                "document": {"id": "1:2", "type": "FRAME"},
                "styles": {
                    "144:616": {"name": "Green/Primary", "styleType": "FILL"}
                },
            }
        }
    }
    styles = figma_client.extract_styles(raw, "1:2")
    assert styles["144:616"]["name"] == "Green/Primary"


def test_extract_styles_falls_back_to_first_entry() -> None:
    raw = {"nodes": {"9:9": {"document": {}, "styles": {"s": {"name": "X"}}}}}
    assert figma_client.extract_styles(raw) == {"s": {"name": "X"}}


def test_extract_styles_missing_returns_empty() -> None:
    assert figma_client.extract_styles({"nodes": {}}) == {}
    assert figma_client.extract_styles({}) == {}


class _FakeResp:
    def __init__(self, payload: dict) -> None:
        import json as _json

        self._data = _json.dumps(payload).encode("utf-8")

    def __enter__(self) -> "_FakeResp":
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def read(self) -> bytes:
        return self._data


def _patch_urlopen(monkeypatch: pytest.MonkeyPatch, payload: dict) -> None:
    import urllib.request

    monkeypatch.setattr(
        urllib.request, "urlopen", lambda *a, **k: _FakeResp(payload)
    )


def test_fetch_node_image_url_returns_render_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_urlopen(monkeypatch, {"images": {"1:2": "https://s3/render.png"}, "err": None})
    url = figma_client.fetch_node_image_url("key", "1:2", "tok")
    assert url == "https://s3/render.png"


def test_fetch_node_image_url_raises_on_err(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_urlopen(monkeypatch, {"images": {}, "err": "boom"})
    with pytest.raises(FigmaError, match="render failed"):
        figma_client.fetch_node_image_url("key", "1:2", "tok")


def test_fetch_node_image_url_none_when_no_image(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_urlopen(monkeypatch, {"images": {"1:2": None}, "err": None})
    assert figma_client.fetch_node_image_url("key", "1:2", "tok") is None


def test_fetch_node_images_returns_url_map(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_urlopen(
        monkeypatch,
        {"images": {"a": "https://s3/a.png", "b": None}, "err": None},
    )
    out = figma_client.fetch_node_images("key", ["a", "b"], "tok")
    assert out == {"a": "https://s3/a.png"}


def test_fetch_node_images_empty_without_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # No ids -> no network call at all.
    import urllib.request

    monkeypatch.setattr(
        urllib.request,
        "urlopen",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("should not call")),
    )
    assert figma_client.fetch_node_images("key", [], "tok") == {}
