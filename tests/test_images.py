from __future__ import annotations

from pathlib import Path

import pytest

from agent import images


def _ir(*nodes: dict) -> dict:
    return {
        "version": "0.1",
        "root": {
            "id": "s",
            "type": "screen",
            "layout": {"direction": "stack"},
            "children": list(nodes),
        },
    }


def test_collect_image_refs_walks_tree() -> None:
    ir = _ir(
        {"id": "a", "type": "ellipse", "imageRef": "r1"},
        {
            "id": "f",
            "type": "frame",
            "layout": {"direction": "stack"},
            "children": [
                {"id": "b", "type": "rectangle", "imageRef": "r2"},
                {"id": "c", "type": "text", "text": "no image"},
            ],
        },
    )
    assert images.collect_image_refs(ir) == {"r1", "r2"}


def test_attach_image_assets_sets_paths() -> None:
    ir = _ir(
        {"id": "a", "type": "ellipse", "imageRef": "r1"},
        {"id": "b", "type": "rectangle", "imageRef": "missing"},
    )
    images.attach_image_assets(ir, {"r1": "assets/images/r1.png"})
    kids = ir["root"]["children"]
    assert kids[0]["imageAsset"] == "assets/images/r1.png"
    assert "imageAsset" not in kids[1]


def test_download_image_fills(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        images.figma_client,
        "fetch_image_fills",
        lambda *a, **k: {"r1": "https://x/r1", "r2": None},
    )
    saved: list[str] = []
    monkeypatch.setattr(
        images.figma_client,
        "download_file",
        lambda url, dest: saved.append(dest) or Path(dest).write_bytes(b"x"),
    )
    asset_map = images.download_image_fills("key", "tok", {"r1", "r2"}, tmp_path)
    assert asset_map == {"r1": "assets/images/r1.png"}
    assert (tmp_path / "assets" / "images" / "r1.png").exists()


def test_ensure_pubspec_assets_inserts_block(tmp_path: Path) -> None:
    pubspec = tmp_path / "pubspec.yaml"
    pubspec.write_text("flutter:\n  uses-material-design: true\n")
    images.ensure_pubspec_assets(pubspec)
    text = pubspec.read_text()
    assert "assets:" in text
    assert "- assets/images/" in text


def test_ensure_pubspec_assets_idempotent(tmp_path: Path) -> None:
    pubspec = tmp_path / "pubspec.yaml"
    pubspec.write_text("flutter:\n  uses-material-design: true\n")
    images.ensure_pubspec_assets(pubspec)
    once = pubspec.read_text()
    images.ensure_pubspec_assets(pubspec)
    assert pubspec.read_text() == once
