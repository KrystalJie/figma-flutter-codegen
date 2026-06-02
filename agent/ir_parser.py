from __future__ import annotations

from typing import Any

IR_VERSION = "0.1"

_LAYOUT_DIRECTION = {"VERTICAL": "vertical", "HORIZONTAL": "horizontal"}
_PRIMARY_ALIGN = {
    "MIN": "start",
    "CENTER": "center",
    "MAX": "end",
    "SPACE_BETWEEN": "spaceBetween",
}
_COUNTER_ALIGN = {
    "MIN": "start",
    "CENTER": "center",
    "MAX": "end",
    "STRETCH": "stretch",
}
_TEXT_ALIGN = {"LEFT": "left", "CENTER": "center", "RIGHT": "right"}
_IMAGE_FIT = {"FILL": "cover", "FIT": "contain", "STRETCH": "fill", "TILE": "cover"}


def parse(figma_json: dict) -> dict:
    """Convert a simplified Figma node tree into Design IR v0.1.

    The root node must be a FRAME and becomes the IR `screen`. Supported
    child types: FRAME, TEXT, RECTANGLE, IMAGE.
    """
    if figma_json.get("type") != "FRAME":
        raise ValueError(f"root must be a FRAME, got {figma_json.get('type')!r}")
    return {"version": IR_VERSION, "root": _parse_screen(figma_json)}


def _parse_screen(node: dict) -> dict:
    out: dict[str, Any] = {"id": node["id"], "type": "screen"}
    _set_optional(out, "name", node.get("name"))
    _set_optional(out, "size", _size(node))
    _set_optional(out, "background", _solid_fill(node))
    out["layout"] = _layout(node)
    out["children"] = [_parse_child(c) for c in node.get("children", [])]
    return out


def _parse_child(node: dict) -> dict:
    t = node.get("type")
    if t == "FRAME":
        return _parse_frame(node)
    if t == "TEXT":
        return _parse_text(node)
    if t == "RECTANGLE":
        return _parse_rectangle(node)
    if t == "IMAGE":
        return _parse_image(node)
    raise ValueError(f"unsupported node type: {t!r}")


def _parse_frame(node: dict) -> dict:
    out: dict[str, Any] = {"id": node["id"], "type": "frame"}
    _set_optional(out, "name", node.get("name"))
    _set_optional(out, "size", _size(node))
    _set_optional(out, "background", _solid_fill(node))
    _set_optional(out, "cornerRadius", node.get("cornerRadius"))
    out["layout"] = _layout(node)
    out["children"] = [_parse_child(c) for c in node.get("children", [])]
    return out


def _parse_text(node: dict) -> dict:
    style = node.get("style") or {}
    out: dict[str, Any] = {
        "id": node["id"],
        "type": "text",
        "text": node.get("characters", ""),
    }
    _set_optional(out, "name", node.get("name"))
    _set_optional(out, "size", _size(node))
    _set_optional(out, "fontSize", style.get("fontSize"))
    _set_optional(out, "fontWeight", style.get("fontWeight"))
    _set_optional(out, "color", _solid_fill(node))
    _set_optional(out, "textAlign", _TEXT_ALIGN.get(style.get("textAlignHorizontal")))
    return out


def _parse_rectangle(node: dict) -> dict:
    out: dict[str, Any] = {"id": node["id"], "type": "rectangle"}
    _set_optional(out, "name", node.get("name"))
    _set_optional(out, "size", _size(node))
    _set_optional(out, "fill", _solid_fill(node))
    _set_optional(out, "cornerRadius", node.get("cornerRadius"))
    return out


def _parse_image(node: dict) -> dict:
    if "src" not in node:
        raise ValueError(f"IMAGE node {node.get('id')!r} missing 'src'")
    out: dict[str, Any] = {"id": node["id"], "type": "image", "src": node["src"]}
    _set_optional(out, "name", node.get("name"))
    _set_optional(out, "size", _size(node))
    _set_optional(out, "fit", _IMAGE_FIT.get(node.get("scaleMode")))
    _set_optional(out, "cornerRadius", node.get("cornerRadius"))
    return out


def _set_optional(target: dict, key: str, value: Any) -> None:
    if value is not None:
        target[key] = value


def _size(node: dict) -> dict | None:
    box = node.get("absoluteBoundingBox")
    if not box:
        return None
    out: dict[str, float] = {}
    if "width" in box:
        out["width"] = box["width"]
    if "height" in box:
        out["height"] = box["height"]
    return out or None


def _layout(node: dict) -> dict:
    mode = node.get("layoutMode")
    if mode not in _LAYOUT_DIRECTION:
        raise ValueError(
            f"frame {node.get('id')!r} requires layoutMode VERTICAL or HORIZONTAL, got {mode!r}"
        )
    out: dict[str, Any] = {"direction": _LAYOUT_DIRECTION[mode]}
    _set_optional(out, "spacing", node.get("itemSpacing"))
    _set_optional(out, "alignment", _COUNTER_ALIGN.get(node.get("counterAxisAlignItems")))
    _set_optional(out, "justify", _PRIMARY_ALIGN.get(node.get("primaryAxisAlignItems")))
    _set_optional(out, "padding", _padding(node))
    return out


def _padding(node: dict) -> dict | None:
    keys = ("paddingTop", "paddingRight", "paddingBottom", "paddingLeft")
    if not any(k in node for k in keys):
        return None
    return {
        "top": node.get("paddingTop", 0),
        "right": node.get("paddingRight", 0),
        "bottom": node.get("paddingBottom", 0),
        "left": node.get("paddingLeft", 0),
    }


def _solid_fill(node: dict) -> str | None:
    for f in node.get("fills") or []:
        if f.get("type") == "SOLID" and f.get("visible", True) is not False:
            return _color_to_hex(f.get("color", {}))
    return None


def _color_to_hex(c: dict) -> str:
    r = round(c.get("r", 0) * 255)
    g = round(c.get("g", 0) * 255)
    b = round(c.get("b", 0) * 255)
    a = c.get("a", 1)
    if a >= 1:
        return f"#{r:02X}{g:02X}{b:02X}"
    return f"#{r:02X}{g:02X}{b:02X}{round(a * 255):02X}"
