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


def parse(
    figma_json: dict,
    warnings: list[str] | None = None,
    styles: dict | None = None,
) -> dict:
    """Convert a simplified Figma node tree into Design IR v0.1.

    The root node must be a FRAME and becomes the IR `screen`. Supported
    child types: FRAME, TEXT, RECTANGLE, IMAGE. Unsupported node types are
    skipped (real Figma trees contain VECTOR, GROUP, etc.), and frames
    without auto-layout fall back to a vertical stack. Both cases append a
    human-readable message to `warnings` when one is provided.

    `styles` is the Figma response's top-level Style map (styleId -> meta).
    When given, published fill Styles are resolved to semantic color names and
    attached as `ir["tokens"]["colors"]` (hex -> name) for codegen (route B).
    """
    sink = warnings if warnings is not None else []
    if figma_json.get("type") != "FRAME":
        raise ValueError(f"root must be a FRAME, got {figma_json.get('type')!r}")
    ir: dict[str, Any] = {"version": IR_VERSION, "root": _parse_screen(figma_json, sink)}
    if styles:
        colors = _collect_color_styles(figma_json, styles)
        if colors:
            ir["tokens"] = {"colors": colors}
    return ir


_FILL_STYLE_KEYS = ("fill", "fills")
_STROKE_STYLE_KEYS = ("stroke", "strokes")


def _collect_color_styles(node: dict, styles: dict) -> dict[str, str]:
    """Walk the tree, mapping each solid color to its published Style name.

    A node links a fill/stroke Style via `node["styles"]` (key -> styleId);
    the styleId resolves in the top-level map to a FILL Style with a name. The
    node's own solid fill/stroke gives the hex, so the result is hex -> name.
    First occurrence wins, keeping the mapping stable and deterministic.
    """
    out: dict[str, str] = {}
    _walk_color_styles(node, styles, out)
    return out


def _walk_color_styles(node: dict, styles: dict, out: dict[str, str]) -> None:
    refs = node.get("styles") or {}
    for key in _FILL_STYLE_KEYS:
        _record_style(refs.get(key), styles, _solid_fill(node), out)
    for key in _STROKE_STYLE_KEYS:
        _record_style(refs.get(key), styles, _solid_stroke(node), out)
    for child in node.get("children") or []:
        _walk_color_styles(child, styles, out)


def _record_style(
    style_id: Any, styles: dict, hex_str: str | None, out: dict[str, str]
) -> None:
    if not style_id or not hex_str:
        return
    meta = styles.get(style_id)
    if isinstance(meta, dict) and meta.get("styleType") == "FILL":
        name = meta.get("name")
        if name:
            out.setdefault(hex_str, name)


def _parse_screen(node: dict, warnings: list[str]) -> dict:
    out: dict[str, Any] = {"id": node["id"], "type": "screen"}
    _set_optional(out, "name", node.get("name"))
    _set_optional(out, "size", _size(node))
    _set_optional(out, "background", _solid_fill(node))
    out["layout"] = _layout(node, warnings)
    out["children"] = _parse_children(node, out["layout"], warnings)
    return out


def _parse_children(node: dict, layout: dict, warnings: list[str]) -> list[dict]:
    """Parse child nodes, dropping unsupported ones.

    When the parent uses `stack` (absolute) layout, each child is annotated
    with a `position` relative to the parent's top-left, so codegen can place
    it with a `Positioned`.
    """
    origin = _stack_origin(node, layout)
    out: list[dict] = []
    for c in node.get("children", []):
        parsed = _parse_child(c, warnings)
        if parsed is None:
            continue
        if origin is not None:
            _set_optional(parsed, "position", _relative_position(c, origin))
        out.append(parsed)
    return out


def _stack_origin(node: dict, layout: dict) -> dict | None:
    if layout.get("direction") != "stack":
        return None
    box = node.get("absoluteBoundingBox")
    if box and "x" in box and "y" in box:
        return box
    return None


def _relative_position(child: dict, origin: dict) -> dict | None:
    box = child.get("absoluteBoundingBox")
    if not box or "x" not in box or "y" not in box:
        return None
    return {"x": box["x"] - origin["x"], "y": box["y"] - origin["y"]}


def _parse_child(node: dict, warnings: list[str]) -> dict | None:
    t = node.get("type")
    # INSTANCE/GROUP/COMPONENT(_SET) are frame-like containers in real Figma
    # files: they carry a `children` array, so we recurse into them as frames.
    if t in ("FRAME", "INSTANCE", "GROUP", "COMPONENT", "COMPONENT_SET"):
        return _parse_frame(node, warnings)
    if t == "TEXT":
        return _parse_text(node)
    if t == "RECTANGLE":
        return _parse_rectangle(node)
    if t == "ELLIPSE":
        return _parse_ellipse(node)
    if t == "IMAGE":
        return _parse_image(node)
    if t == "VECTOR":
        return _parse_vector(node, warnings)
    if t == "LINE":
        return _parse_line(node, warnings)
    warnings.append(f"skipped unsupported node {node.get('id')!r} of type {t!r}")
    return None


def _parse_vector(node: dict, warnings: list[str]) -> dict | None:
    """Best-effort VECTOR handling.

    A VECTOR with a cornerRadius and a solid fill is almost always a
    decorative rounded-rect background (a pill/track/card), so we render it
    as a rectangle. True icon vectors (no cornerRadius) carry arbitrary path
    geometry we cannot reproduce, so they are still skipped.
    """
    if node.get("cornerRadius") is not None and _solid_fill(node) is not None:
        return _parse_rectangle(node)
    warnings.append(f"skipped unsupported node {node.get('id')!r} of type 'VECTOR'")
    return None


def _parse_frame(node: dict, warnings: list[str]) -> dict:
    out: dict[str, Any] = {"id": node["id"], "type": "frame"}
    _set_optional(out, "name", node.get("name"))
    _set_optional(out, "size", _size(node))
    _set_optional(out, "background", _solid_fill(node))
    _set_optional(out, "cornerRadius", node.get("cornerRadius"))
    _set_optional(out, "border", _border(node))
    _apply_image_fill(out, node)
    out["layout"] = _layout(node, warnings)
    out["children"] = _parse_children(node, out["layout"], warnings)
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
    # Fixed-width Figma text (textAutoResize != WIDTH_AND_HEIGHT) is meant to
    # wrap inside its box. Flag it so codegen constrains the width; auto-width
    # ("WIDTH_AND_HEIGHT") text keeps hugging its content on a single line.
    if (style.get("textAutoResize") or "").upper() in ("HEIGHT", "NONE", "TRUNCATE"):
        out["wrap"] = True
    return out


def _parse_rectangle(node: dict) -> dict:
    out: dict[str, Any] = {"id": node["id"], "type": "rectangle"}
    _set_optional(out, "name", node.get("name"))
    _set_optional(out, "size", _size(node))
    _set_optional(out, "fill", _solid_fill(node))
    _set_optional(out, "cornerRadius", node.get("cornerRadius"))
    _set_optional(out, "border", _border(node))
    _apply_image_fill(out, node)
    return out


def _parse_line(node: dict, warnings: list[str]) -> dict | None:
    """An axis-aligned LINE (a divider/rule) -> a thin filled rectangle.

    Figma LINEs carry a stroke (not a fill). A horizontal rule has height ~0
    and a vertical rule has width ~0; we render it as a 1-thick rectangle the
    length of the line, coloured by the stroke. Diagonal lines carry path
    geometry we cannot reproduce, so they are still skipped.
    """
    color = _solid_stroke(node)
    box = node.get("absoluteBoundingBox") or {}
    w, h = box.get("width"), box.get("height")
    weight = node.get("strokeWeight") or 1
    if color is not None and w is not None and h is not None:
        if h < 2 <= w:  # horizontal rule
            size = {"width": w, "height": weight}
        elif w < 2 <= h:  # vertical rule
            size = {"width": weight, "height": h}
        else:
            size = None
        if size is not None:
            out: dict[str, Any] = {"id": node["id"], "type": "rectangle", "fill": color, "size": size}
            _set_optional(out, "name", node.get("name"))
            return out
    warnings.append(f"skipped unsupported node {node.get('id')!r} of type 'LINE'")
    return None


def _parse_ellipse(node: dict) -> dict:
    out: dict[str, Any] = {"id": node["id"], "type": "ellipse"}
    _set_optional(out, "name", node.get("name"))
    _set_optional(out, "size", _size(node))
    _set_optional(out, "fill", _solid_fill(node))
    _set_optional(out, "border", _border(node))
    _apply_image_fill(out, node)
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


def _layout(node: dict, warnings: list[str]) -> dict:
    mode = node.get("layoutMode")
    if mode not in _LAYOUT_DIRECTION:
        warnings.append(
            f"frame {node.get('id')!r} has no auto-layout (layoutMode={mode!r}); "
            "using absolute Stack positioning"
        )
        return {"direction": "stack"}
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


def _apply_image_fill(out: dict, node: dict) -> None:
    """Record an IMAGE fill's `imageRef` (+ `imageFit`) onto an IR node.

    The ref is resolved to a downloaded asset path later (see agent.images).
    """
    for f in node.get("fills") or []:
        if f.get("type") == "IMAGE" and f.get("visible", True) is not False:
            ref = f.get("imageRef")
            if ref:
                out["imageRef"] = ref
                _set_optional(out, "imageFit", _IMAGE_FIT.get(f.get("scaleMode")))
                return


def _border(node: dict) -> dict | None:
    color = _solid_stroke(node)
    if color is None:
        return None
    out: dict[str, Any] = {"color": color}
    _set_optional(out, "width", node.get("strokeWeight"))
    return out


def _solid_stroke(node: dict) -> str | None:
    for s in node.get("strokes") or []:
        if s.get("type") == "SOLID" and s.get("visible", True) is not False:
            return _color_to_hex(s.get("color", {}))
    return None


def _color_to_hex(c: dict) -> str:
    r = round(c.get("r", 0) * 255)
    g = round(c.get("g", 0) * 255)
    b = round(c.get("b", 0) * 255)
    a = c.get("a", 1)
    if a >= 1:
        return f"#{r:02X}{g:02X}{b:02X}"
    return f"#{r:02X}{g:02X}{b:02X}{round(a * 255):02X}"
