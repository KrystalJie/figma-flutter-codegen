from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from agent import figma_client

ASSET_DIR = "assets/images"


def collect_image_refs(ir: dict) -> set[str]:
    """Return every `imageRef` used anywhere in the Design IR tree."""
    refs: set[str] = set()
    root = ir.get("root")
    if isinstance(root, dict):
        _walk(root, lambda n: refs.add(n["imageRef"]) if n.get("imageRef") else None)
    return refs


def attach_image_assets(ir: dict, asset_map: dict[str, str]) -> None:
    """Set `imageAsset` (a Flutter asset path) on nodes whose ref was downloaded."""
    root = ir.get("root")
    if isinstance(root, dict):
        _walk(root, lambda n: _set_asset(n, asset_map))


def download_image_fills(
    file_key: str,
    token: str | None,
    refs: set[str],
    flutter_root: str | Path,
) -> dict[str, str]:
    """Download the given image refs into `<flutter_root>/assets/images/`.

    Returns a map of imageRef -> Flutter asset path (e.g. assets/images/<ref>.png)
    for the refs that were successfully resolved and downloaded.
    """
    if not refs:
        return {}
    url_map = figma_client.fetch_image_fills(file_key, token)
    dest_dir = Path(flutter_root) / ASSET_DIR
    dest_dir.mkdir(parents=True, exist_ok=True)
    asset_map: dict[str, str] = {}
    for ref in sorted(refs):
        url = url_map.get(ref)
        if not url:
            continue
        filename = f"{ref}.png"
        figma_client.download_file(url, str(dest_dir / filename))
        asset_map[ref] = f"{ASSET_DIR}/{filename}"
    return asset_map


def collect_icon_ids(ir: dict) -> list[str]:
    """Return the Figma node ids of every `icon` node in the IR (in order)."""
    ids: list[str] = []
    root = ir.get("root")
    if isinstance(root, dict):
        _walk(
            root,
            lambda n: ids.append(n["id"])
            if n.get("type") == "icon" and n.get("id")
            else None,
        )
    return ids


def attach_icon_assets(ir: dict, asset_map: dict[str, str]) -> None:
    """Set `iconAsset` on `icon` nodes whose node id was rendered + downloaded."""
    root = ir.get("root")
    if isinstance(root, dict):
        _walk(root, lambda n: _set_icon_asset(n, asset_map))


def download_icons(
    file_key: str,
    token: str | None,
    node_ids: list[str],
    flutter_root: str | Path,
    scale: float = 2.0,
) -> dict[str, str]:
    """Rasterize the given icon node ids (node-render API) into the assets dir.

    Returns {node_id: asset_path} for the ids Figma rendered + we downloaded.
    """
    if not node_ids:
        return {}
    url_map = figma_client.fetch_node_images(file_key, node_ids, token, scale=scale)
    dest_dir = Path(flutter_root) / ASSET_DIR
    dest_dir.mkdir(parents=True, exist_ok=True)
    asset_map: dict[str, str] = {}
    for nid in node_ids:
        url = url_map.get(nid)
        if not url:
            continue
        filename = f"icon_{_safe_name(nid)}.png"
        figma_client.download_file(url, str(dest_dir / filename))
        asset_map[nid] = f"{ASSET_DIR}/{filename}"
    return asset_map


def ensure_pubspec_assets(pubspec_path: str | Path) -> None:
    """Make sure pubspec.yaml lists the generated assets directory."""
    path = Path(pubspec_path)
    text = path.read_text()
    entry = f"- {ASSET_DIR}/"
    if entry in text:
        return
    lines = text.splitlines()
    # Insert an assets block right after `uses-material-design: true`.
    for i, line in enumerate(lines):
        if line.strip() == "uses-material-design: true":
            lines[i + 1 : i + 1] = ["", "  assets:", f"    {entry}"]
            path.write_text("\n".join(lines) + "\n")
            return
    raise ValueError("could not find the flutter section in pubspec.yaml")


def _walk(node: dict, fn: Any) -> None:
    fn(node)
    for child in node.get("children", []):
        if isinstance(child, dict):
            _walk(child, fn)


def _set_asset(node: dict, asset_map: dict[str, str]) -> None:
    ref = node.get("imageRef")
    if ref and ref in asset_map:
        node["imageAsset"] = asset_map[ref]


def _set_icon_asset(node: dict, asset_map: dict[str, str]) -> None:
    nid = node.get("id")
    if node.get("type") == "icon" and nid in asset_map:
        node["iconAsset"] = asset_map[nid]


def _safe_name(node_id: str) -> str:
    """Filesystem-safe slug for a Figma node id (which has ':' and ';')."""
    return re.sub(r"[^0-9A-Za-z]+", "_", node_id).strip("_")
