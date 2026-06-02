from __future__ import annotations

from typing import Any

HEADER = "import 'package:flutter/material.dart';"


def generate(ir: dict) -> str:
    """Convert Design IR v0.1 into a Flutter StatelessWidget source file.

    Notes:
      - All images render as Image.network regardless of src origin. The
        codegen will not distinguish asset paths from URLs in this version.
      - Container.color and Container.decoration are mutually exclusive in
        Flutter, so cornerRadius forces a BoxDecoration even when only the
        radius is set.
    """
    if ir.get("version") != "0.1":
        raise ValueError(f"unsupported IR version: {ir.get('version')!r}")
    root = ir["root"]
    if root.get("type") != "screen":
        raise ValueError(f"root must be a screen, got {root.get('type')!r}")
    class_name = _class_name(root.get("name"))
    body = _emit_screen(root)
    body_inline = _embed(body, 4)
    return (
        f"{HEADER}\n"
        "\n"
        f"class {class_name} extends StatelessWidget {{\n"
        f"  const {class_name}({{super.key}});\n"
        "\n"
        "  @override\n"
        "  Widget build(BuildContext context) {\n"
        f"    return {body_inline};\n"
        "  }\n"
        "}\n"
    )


def _emit_screen(node: dict) -> str:
    inner = _emit_layout(node)
    safe_area = _call("SafeArea", [f"child: {inner}"])
    args: list[str] = []
    bg = node.get("background")
    if bg:
        args.append(f"backgroundColor: {_color(bg)}")
    args.append(f"body: {safe_area}")
    return _call("Scaffold", args)


def _emit_node(node: dict) -> str:
    t = node["type"]
    if t == "frame":
        return _emit_frame(node)
    if t == "text":
        return _emit_text(node)
    if t == "rectangle":
        return _emit_rectangle(node)
    if t == "image":
        return _emit_image(node)
    if t == "button":
        return _emit_button(node)
    raise ValueError(f"unsupported IR node type: {t!r}")


def _emit_layout(node: dict) -> str:
    layout = node["layout"]
    widget = "Column" if layout["direction"] == "vertical" else "Row"
    args: list[str] = []
    if "alignment" in layout:
        args.append(f"crossAxisAlignment: CrossAxisAlignment.{layout['alignment']}")
    if "justify" in layout:
        args.append(f"mainAxisAlignment: MainAxisAlignment.{layout['justify']}")
    if layout.get("spacing"):
        args.append(f"spacing: {_num(layout['spacing'])}")

    children = node.get("children", [])
    if children:
        items = ",\n".join("  " + _embed(_emit_node(c), 2) for c in children)
        args.append(f"children: [\n{items},\n]")
    else:
        args.append("children: <Widget>[]")

    column_or_row = _call(widget, args)
    pad = layout.get("padding")
    if pad and any(pad.get(k) for k in ("top", "right", "bottom", "left")):
        return _wrap_padding(column_or_row, pad)
    return column_or_row


def _emit_frame(node: dict) -> str:
    inner = _emit_layout(node)
    size = node.get("size") or {}
    bg = node.get("background")
    radius = node.get("cornerRadius")
    has_w = size.get("width") is not None
    has_h = size.get("height") is not None
    if not (bg or radius or has_w or has_h):
        return inner
    args: list[str] = []
    if has_w:
        args.append(f"width: {_num(size['width'])}")
    if has_h:
        args.append(f"height: {_num(size['height'])}")
    if bg and not radius:
        args.append(f"color: {_color(bg)}")
    if radius:
        deco_args: list[str] = []
        if bg:
            deco_args.append(f"color: {_color(bg)}")
        deco_args.append(f"borderRadius: BorderRadius.circular({_num(radius)})")
        args.append("decoration: " + _call("BoxDecoration", deco_args))
    args.append(f"child: {inner}")
    return _call("Container", args)


def _emit_text(node: dict) -> str:
    args: list[str] = [_dart_str(node["text"])]
    style_args: list[str] = []
    if "fontSize" in node:
        style_args.append(f"fontSize: {_num(node['fontSize'])}")
    if "fontWeight" in node:
        style_args.append(f"fontWeight: FontWeight.w{int(node['fontWeight'])}")
    if "color" in node:
        style_args.append(f"color: {_color(node['color'])}")
    if style_args:
        args.append("style: " + _call("TextStyle", style_args))
    if "textAlign" in node:
        args.append(f"textAlign: TextAlign.{node['textAlign']}")
    return _call("Text", args)


def _emit_rectangle(node: dict) -> str:
    size = node.get("size") or {}
    fill = node.get("fill")
    radius = node.get("cornerRadius")
    args: list[str] = []
    if size.get("width") is not None:
        args.append(f"width: {_num(size['width'])}")
    if size.get("height") is not None:
        args.append(f"height: {_num(size['height'])}")
    if fill and not radius:
        args.append(f"color: {_color(fill)}")
    if radius:
        deco_args: list[str] = []
        if fill:
            deco_args.append(f"color: {_color(fill)}")
        deco_args.append(f"borderRadius: BorderRadius.circular({_num(radius)})")
        args.append("decoration: " + _call("BoxDecoration", deco_args))
    if not args:
        args.append("color: Color(0x00000000)")
    return _call("Container", args)


def _emit_image(node: dict) -> str:
    size = node.get("size") or {}
    args: list[str] = [_dart_str(node["src"])]
    if size.get("width") is not None:
        args.append(f"width: {_num(size['width'])}")
    if size.get("height") is not None:
        args.append(f"height: {_num(size['height'])}")
    if "fit" in node:
        args.append(f"fit: BoxFit.{node['fit']}")
    img = _call("Image.network", args)
    radius = node.get("cornerRadius")
    if radius:
        return _call("ClipRRect", [
            f"borderRadius: BorderRadius.circular({_num(radius)})",
            f"child: {img}",
        ])
    return img


def _emit_button(node: dict) -> str:
    args: list[str] = ["onPressed: () {}"]
    style_args: list[str] = []
    if "background" in node:
        style_args.append(f"backgroundColor: {_color(node['background'])}")
    if "color" in node:
        style_args.append(f"foregroundColor: {_color(node['color'])}")
    if "padding" in node:
        style_args.append(f"padding: {_edge_insets(node['padding'])}")
    if "cornerRadius" in node:
        shape = _call("RoundedRectangleBorder", [
            f"borderRadius: BorderRadius.circular({_num(node['cornerRadius'])})"
        ])
        style_args.append(f"shape: {shape}")
    if style_args:
        args.append("style: " + _call("ElevatedButton.styleFrom", style_args))
    args.append("child: " + _call("Text", [_dart_str(node["label"])]))
    return _call("ElevatedButton", args)


def _wrap_padding(inner: str, pad: dict) -> str:
    return _call("Padding", [f"padding: {_edge_insets(pad)}", f"child: {inner}"])


def _edge_insets(pad: dict) -> str:
    t, r, b, l = pad["top"], pad["right"], pad["bottom"], pad["left"]
    if t == r == b == l:
        return f"EdgeInsets.all({_num(t)})"
    if t == b and l == r:
        return f"EdgeInsets.symmetric(horizontal: {_num(l)}, vertical: {_num(t)})"
    return f"EdgeInsets.fromLTRB({_num(l)}, {_num(t)}, {_num(r)}, {_num(b)})"


def _color(hex_str: str) -> str:
    h = hex_str.lstrip("#").upper()
    if len(h) == 6:
        return f"Color(0xFF{h})"
    rrggbb, aa = h[:6], h[6:]
    return f"Color(0x{aa}{rrggbb})"


def _class_name(name: str | None) -> str:
    fallback = "GeneratedScreen"
    if not name:
        return fallback
    cleaned = "".join(ch for ch in name if ch.isalnum() or ch == "_")
    if not cleaned or cleaned[0].isdigit():
        return fallback
    return cleaned[0].upper() + cleaned[1:]


def _num(n: Any) -> str:
    if isinstance(n, bool):
        raise TypeError("expected number, got bool")
    if isinstance(n, int):
        return str(n)
    if isinstance(n, float):
        if n.is_integer():
            return str(int(n))
        return repr(n)
    raise TypeError(f"expected number, got {type(n).__name__}")


def _dart_str(s: str) -> str:
    escaped = s.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n")
    return f"'{escaped}'"


def _call(name: str, args: list[str]) -> str:
    if not args:
        return f"{name}()"
    body = ",\n".join("  " + _embed(a, 2) for a in args)
    return f"{name}(\n{body},\n)"


def _embed(s: str, n: int) -> str:
    return s.replace("\n", "\n" + " " * n)
