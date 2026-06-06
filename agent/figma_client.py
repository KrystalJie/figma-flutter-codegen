from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request

FIGMA_API = "https://api.figma.com/v1"

# Matches the file key in both /file/<key>/ and /design/<key>/ URLs.
_FILE_KEY_RE = re.compile(r"figma\.com/(?:file|design)/([0-9A-Za-z]+)")
_NODE_ID_RE = re.compile(r"[?&]node-id=([^&]+)")


class FigmaError(RuntimeError):
    """Raised when a Figma URL is malformed or the API request fails."""


def parse_figma_url(url: str) -> tuple[str, str | None]:
    """Extract (file_key, node_id) from a Figma file/design URL.

    Figma URLs encode the node id with '-' (e.g. node-id=1-2), while the
    REST API expects ':' (e.g. 1:2), so it is normalized here. node_id is
    None when the URL has no node-id query parameter.
    """
    m = _FILE_KEY_RE.search(url)
    if not m:
        raise FigmaError(f"could not parse Figma file key from URL: {url!r}")
    file_key = m.group(1)

    node_id: str | None = None
    nm = _NODE_ID_RE.search(url)
    if nm:
        raw = urllib.parse.unquote(nm.group(1))
        node_id = raw.replace("-", ":")
    return file_key, node_id


def resolve_token(token: str | None = None) -> str:
    """Return the Figma access token, falling back to the FIGMA_TOKEN env var."""
    token = token or os.environ.get("FIGMA_TOKEN")
    if not token:
        raise FigmaError(
            "no Figma token: pass --figma-token or set the FIGMA_TOKEN env var"
        )
    return token


def fetch_nodes(file_key: str, node_id: str, token: str | None = None) -> dict:
    """Fetch the raw Figma response for one node.

    Calls GET /v1/files/<key>/nodes?ids=<id> and returns the parsed JSON
    unchanged, so callers can persist it for debugging (see CLI --save-run).
    """
    auth = resolve_token(token)
    ids = urllib.parse.quote(node_id, safe="")
    url = f"{FIGMA_API}/files/{file_key}/nodes?ids={ids}"
    req = urllib.request.Request(url, headers={"X-Figma-Token": auth})
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise FigmaError(f"Figma API returned HTTP {exc.code}: {exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise FigmaError(f"Figma API request failed: {exc.reason}") from exc


def fetch_node(
    file_key: str, node_id: str, token: str | None = None
) -> tuple[dict, dict]:
    """Return (document_node, raw_response) for a single Figma node.

    The /nodes endpoint wraps each node as
    {"nodes": {"<id>": {"document": {...}}}}; this unwraps the document so
    it can be handed straight to ir_parser.parse, while also returning the
    full raw response for debugging.
    """
    if not node_id:
        raise FigmaError("a node id is required (URL must include node-id=...)")
    raw = fetch_nodes(file_key, node_id, token)
    nodes = raw.get("nodes") or {}
    entry = nodes.get(node_id) or next(iter(nodes.values()), None)
    if not isinstance(entry, dict) or "document" not in entry:
        raise FigmaError(f"node {node_id!r} not found in Figma response")
    return entry["document"], raw


def extract_styles(raw: dict, node_id: str | None = None) -> dict:
    """Return the top-level Style map (styleId -> meta) from a /nodes response.

    The map (a sibling of "document" in each node entry) names published
    fill/text Styles, e.g. {"144:616": {"name": "Green/Primary", "styleType":
    "FILL"}}. Returns {} when absent. Used by ir_parser for semantic naming.
    """
    nodes = raw.get("nodes") or {}
    entry = nodes.get(node_id) if node_id else None
    if not isinstance(entry, dict):
        entry = next((e for e in nodes.values() if isinstance(e, dict)), None)
    if not isinstance(entry, dict):
        return {}
    return entry.get("styles") or {}


def fetch_image_fills(file_key: str, token: str | None = None) -> dict[str, str]:
    """Return a map of imageRef -> download URL for the file's image fills.

    Calls GET /v1/files/<key>/images, whose response is
    {"meta": {"images": {"<imageRef>": "<url>"}}}. URLs are temporary S3
    links, so callers should download the bytes promptly.
    """
    auth = resolve_token(token)
    url = f"{FIGMA_API}/files/{file_key}/images"
    req = urllib.request.Request(url, headers={"X-Figma-Token": auth})
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise FigmaError(f"Figma API returned HTTP {exc.code}: {exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise FigmaError(f"Figma API request failed: {exc.reason}") from exc
    images = (data.get("meta") or {}).get("images") or {}
    return {ref: url for ref, url in images.items() if url}


def fetch_node_image_url(
    file_key: str,
    node_id: str,
    token: str | None = None,
    scale: float = 2.0,
    fmt: str = "png",
) -> str | None:
    """Return a render URL for a node via GET /v1/images/<key>.

    This is the node *render* endpoint (the whole node rasterized as it
    looks in Figma), distinct from fetch_image_fills (raw fill bitmaps).
    The response is {"images": {"<id>": "<url>"}, "err": null}. Returns
    None when Figma produced no image for the node.
    """
    auth = resolve_token(token)
    ids = urllib.parse.quote(node_id, safe="")
    url = (
        f"{FIGMA_API}/images/{file_key}"
        f"?ids={ids}&format={fmt}&scale={scale}"
    )
    req = urllib.request.Request(url, headers={"X-Figma-Token": auth})
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise FigmaError(f"Figma API returned HTTP {exc.code}: {exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise FigmaError(f"Figma API request failed: {exc.reason}") from exc
    if data.get("err"):
        raise FigmaError(f"Figma image render failed: {data['err']}")
    images = data.get("images") or {}
    return images.get(node_id) or next((u for u in images.values() if u), None)


def fetch_node_images(
    file_key: str,
    node_ids: list[str],
    token: str | None = None,
    scale: float = 2.0,
    fmt: str = "png",
) -> dict[str, str]:
    """Render several nodes at once via GET /v1/images/<key>.

    Returns {node_id: url} for the ids Figma produced an image for. Same
    endpoint as fetch_node_image_url, batched (one call for many ids).
    """
    ids = [i for i in node_ids if i]
    if not ids:
        return {}
    auth = resolve_token(token)
    joined = urllib.parse.quote(",".join(ids), safe=",")
    url = f"{FIGMA_API}/images/{file_key}?ids={joined}&format={fmt}&scale={scale}"
    req = urllib.request.Request(url, headers={"X-Figma-Token": auth})
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise FigmaError(f"Figma API returned HTTP {exc.code}: {exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise FigmaError(f"Figma API request failed: {exc.reason}") from exc
    if data.get("err"):
        raise FigmaError(f"Figma image render failed: {data['err']}")
    return {nid: u for nid, u in (data.get("images") or {}).items() if u}


def download_file(url: str, dest: str) -> None:
    """Download a URL to a local path (used for image-fill S3 links)."""
    try:
        with urllib.request.urlopen(url) as resp:
            data = resp.read()
    except urllib.error.URLError as exc:
        raise FigmaError(f"failed to download image {url!r}: {exc.reason}") from exc
    with open(dest, "wb") as f:
        f.write(data)
