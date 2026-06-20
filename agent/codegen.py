from __future__ import annotations

from typing import Any

from agent.tokens import Tokens

HEADER = "import 'package:flutter/material.dart';"

# Active token registry during a `generate()` call. When set, leaf emitters
# intern style literals into named constants instead of inlining them; when
# None (e.g. helpers called directly in tests) they emit plain literals.
_active: Tokens | None = None

# When True (opt-in via generate(keyed=True)), every id-bearing node is wrapped
# in a KeyedSubtree(ValueKey(<figma id>)) so a render-time rect dump can map
# each widget back to its Figma node. Off by default so normal output and the
# codegen snapshot tests are unchanged.
_keyed: bool = False


def generate(plan: dict, *, keyed: bool = False) -> str:
    """Convert a Component Plan v0.1 into a Flutter source file.

    Each component becomes its own StatelessWidget class in a single file.
    A component reference node (`{"type": "component", "ref": <name>}`)
    renders as `const <Name>()`, so the screen stays small and the extracted
    components are reusable.

    Notes:
      - All images render as Image.network regardless of src origin. The
        codegen will not distinguish asset paths from URLs in this version.
      - Container.color and Container.decoration are mutually exclusive in
        Flutter, so cornerRadius or a border forces a BoxDecoration even when
        only one of them is set.
    """
    if plan.get("version") != "0.1":
        raise ValueError(f"unsupported plan version: {plan.get('version')!r}")
    components = plan.get("components")
    if not components:
        raise ValueError("plan has no components")
    global _active, _keyed
    color_names = (plan.get("tokens") or {}).get("colors") or {}
    _active = Tokens(color_names)
    _keyed = keyed
    try:
        blocks = [_emit_component(c) for c in components]
        theme = _render_theme(_active)
    finally:
        _active = None
        _keyed = False
    head = f"{HEADER}\n\n"
    if theme:
        head += theme + "\n\n"
    return head + "\n".join(blocks)


def _emit_component(component: dict) -> str:
    class_name = _class_name(component.get("name"))
    root = component["root"]
    if root.get("type") == "screen":
        body = _emit_screen(root)
    else:
        body = _emit_node(root)
    body_inline = _embed(body, 4)
    return (
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
    return _maybe_key(node, _dispatch_node(node))


def _maybe_key(node: dict, body: str) -> str:
    """Wrap an emitted node in KeyedSubtree(ValueKey(id)) when keying is on.

    Component references are left unkeyed: a deduped component is rendered at
    several sites, so its id is not unique in the tree. Reused components still
    carry keys on the screen-side reference's own nodes elsewhere.
    """
    nid = node.get("id")
    if not _keyed or not nid or node.get("type") == "component":
        return body
    return _call("KeyedSubtree", [f"key: ValueKey({_dart_str(nid)})", f"child: {body}"])


def _dispatch_node(node: dict) -> str:
    t = node["type"]
    if t == "frame":
        return _emit_frame(node)
    if t == "text":
        return _emit_text(node)
    if t == "rectangle":
        return _emit_rectangle(node)
    if t == "ellipse":
        return _emit_ellipse(node)
    if t == "image":
        return _emit_image(node)
    if t == "icon":
        return _emit_icon(node)
    if t == "button":
        return _emit_button(node)
    if t == "component":
        return f"const {_class_name(node['ref'])}()"
    raise ValueError(f"unsupported IR node type: {t!r}")


def _emit_layout(node: dict) -> str:
    layout = node["layout"]
    children = node.get("children", [])
    if layout["direction"] == "stack":
        body = _emit_stack(children)
    else:
        body = _emit_flex(layout, children)
    pad = layout.get("padding")
    if pad and any(pad.get(k) for k in ("top", "right", "bottom", "left")):
        return _wrap_padding(body, pad)
    return body


def _emit_flex(layout: dict, children: list[dict]) -> str:
    widget = "Column" if layout["direction"] == "vertical" else "Row"
    args: list[str] = []
    if "alignment" in layout:
        args.append(f"crossAxisAlignment: CrossAxisAlignment.{layout['alignment']}")
    if "justify" in layout:
        args.append(f"mainAxisAlignment: MainAxisAlignment.{layout['justify']}")
    if layout.get("spacing"):
        args.append(f"spacing: {_space(layout['spacing'])}")
    args.append(_children_arg(children))
    return _call(widget, args)


def _emit_stack(children: list[dict]) -> str:
    """Render absolutely-positioned children inside a Stack.

    Children carrying a `position` are wrapped in `Positioned`; any without
    fall back to the Stack's default top-left placement.
    """
    items = [_emit_stack_child(c) for c in children]
    return _call("Stack", [_children_arg(children, items)])


def _emit_stack_child(node: dict) -> str:
    inner = _emit_node(node)
    pos = node.get("position")
    if not pos:
        return inner
    args: list[str] = []
    if pos.get("x") is not None:
        args.append(f"left: {_num(pos['x'])}")
    if pos.get("y") is not None:
        args.append(f"top: {_num(pos['y'])}")
    args.append(f"child: {inner}")
    return _call("Positioned", args)


def _children_arg(children: list[dict], rendered: list[str] | None = None) -> str:
    if not children:
        return "children: <Widget>[]"
    items = rendered if rendered is not None else [_emit_node(c) for c in children]
    body = ",\n".join("  " + _embed(item, 2) for item in items)
    return f"children: [\n{body},\n]"


def _emit_frame(node: dict) -> str:
    inner = _emit_layout(node)
    size = node.get("size") or {}
    has_w = size.get("width") is not None
    has_h = size.get("height") is not None
    fill_args = _box_fill_args(
        node.get("background"),
        node.get("cornerRadius"),
        node.get("border"),
        _image_of(node),
    )
    if not (fill_args or has_w or has_h):
        return inner
    args: list[str] = []
    if has_w:
        args.append(f"width: {_num(size['width'])}")
    if has_h:
        args.append(f"height: {_num(size['height'])}")
    args.append(f"child: {inner}")
    # A Container with only width/height triggers the sized_box_for_whitespace
    # lint; use a SizedBox when there is no fill/decoration to apply.
    if not fill_args:
        return _call("SizedBox", args)
    args[-1:-1] = fill_args
    return _call("Container", args)


def _emit_text(node: dict) -> str:
    args: list[str] = [_dart_str(node["text"])]
    style = _text_style_expr(
        node.get("fontSize"),
        node.get("fontWeight"),
        node.get("color"),
        node.get("fontFamily"),
        node.get("lineHeight"),
    )
    if style:
        args.append("style: " + style)
    if "textAlign" in node:
        args.append(f"textAlign: TextAlign.{node['textAlign']}")
    text = _call("Text", args)
    # Fixed-width text wraps to its Figma box width; without this constraint a
    # Text inside a Stack/Positioned is unbounded and clips to one line.
    size = node.get("size") or {}
    if node.get("wrap") and size.get("width") is not None:
        return _call("SizedBox", [f"width: {_num(size['width'])}", f"child: {text}"])
    return text


def _emit_icon(node: dict) -> str:
    """An icon vector: render the rasterized asset, or reserve its space.

    When the CLI rendered the vector (live --figma-url + token), `iconAsset`
    holds the downloaded PNG path. Without it (e.g. a saved --input file), we
    emit a same-size SizedBox so positions/layout stay correct.
    """
    size = node.get("size") or {}
    w = size.get("width")
    h = size.get("height")
    asset = node.get("iconAsset")
    if asset:
        args = [_dart_str(asset)]
        if w is not None:
            args.append(f"width: {_num(w)}")
        if h is not None:
            args.append(f"height: {_num(h)}")
        args.append("fit: BoxFit.contain")
        return _call("Image.asset", args)
    args = []
    if w is not None:
        args.append(f"width: {_num(w)}")
    if h is not None:
        args.append(f"height: {_num(h)}")
    return _call("SizedBox", args) if args else "const SizedBox.shrink()"


def _text_style_expr(
    size: Any,
    weight: Any,
    color: str | None,
    family: str | None = None,
    line_height: Any = None,
) -> str | None:
    """Text style as a typography token (+ `copyWith` overrides) when active.

    fontFamily/fontSize/fontWeight form a reusable `AppTextStyles` constant; the
    per-use color and line-height are layered on with `copyWith` so one type
    ramp serves many colors/leadings. A text with only overrides (no
    family/size/weight) stays an inline `TextStyle`.
    """
    overrides: list[str] = []
    if color is not None:
        overrides.append(f"color: {_color(color)}")
    if line_height is not None:
        overrides.append(f"height: {_num(line_height)}")
    has_type = size is not None or weight is not None or family is not None
    if _active is not None and has_type:
        base = _active.text_style(size, weight, family)
        if overrides:
            return f"{base}.copyWith({', '.join(overrides)})"
        return base
    style_args: list[str] = []
    if family is not None:
        style_args.append(f"fontFamily: {_dart_str(family)}")
    if size is not None:
        style_args.append(f"fontSize: {_num(size)}")
    if weight is not None:
        style_args.append(f"fontWeight: FontWeight.w{int(weight)}")
    style_args.extend(overrides)
    if not style_args:
        return None
    return _call("TextStyle", style_args)


def _emit_rectangle(node: dict) -> str:
    size = node.get("size") or {}
    args: list[str] = []
    if size.get("width") is not None:
        args.append(f"width: {_num(size['width'])}")
    if size.get("height") is not None:
        args.append(f"height: {_num(size['height'])}")
    args.extend(
        _box_fill_args(
            node.get("fill"),
            node.get("cornerRadius"),
            node.get("border"),
            _image_of(node),
        )
    )
    if not args:
        args.append("color: Color(0x00000000)")
    return _call("Container", args)


def _emit_ellipse(node: dict) -> str:
    size = node.get("size") or {}
    args: list[str] = []
    if size.get("width") is not None:
        args.append(f"width: {_num(size['width'])}")
    if size.get("height") is not None:
        args.append(f"height: {_num(size['height'])}")
    deco_args: list[str] = ["shape: BoxShape.circle"]
    fill = node.get("fill")
    if fill:
        deco_args.append(f"color: {_color(fill)}")
    image = _image_of(node)
    if image:
        deco_args.append(f"image: {_decoration_image(image)}")
    border = node.get("border")
    if border:
        deco_args.append(f"border: {_border(border)}")
    args.append("decoration: " + _call("BoxDecoration", deco_args))
    return _call("Container", args)


def _box_fill_args(
    fill: str | None, radius: Any, border: dict | None, image: dict | None = None
) -> list[str]:
    """Container args for a flat fill / corner radius / border / image fill.

    A plain `color:` is used when only a flat fill is present; otherwise a
    BoxDecoration carries the fill, image, radius, and border together (color
    and decoration cannot both be set on a Container).
    """
    if not radius and not border and not image:
        return [f"color: {_color(fill)}"] if fill else []
    deco_args: list[str] = []
    if fill:
        deco_args.append(f"color: {_color(fill)}")
    if image:
        deco_args.append(f"image: {_decoration_image(image)}")
    if radius:
        deco_args.append(f"borderRadius: BorderRadius.circular({_num(radius)})")
    if border:
        deco_args.append(f"border: {_border(border)}")
    return ["decoration: " + _call("BoxDecoration", deco_args)]


def _image_of(node: dict) -> dict | None:
    asset = node.get("imageAsset")
    if not asset:
        return None
    return {"asset": asset, "fit": node.get("imageFit", "cover")}


def _decoration_image(image: dict) -> str:
    return _call(
        "DecorationImage",
        [
            f"image: AssetImage({_dart_str(image['asset'])})",
            f"fit: BoxFit.{image['fit']}",
        ],
    )


def _border(border: dict) -> str:
    args = [f"color: {_color(border['color'])}"]
    if border.get("width") is not None:
        args.append(f"width: {_num(border['width'])}")
    return _call("Border.all", args)


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


def _render_theme(t: Tokens) -> str:
    """Render the interned tokens into constant classes (empty -> "").

    Entries are sorted by name so the theme block is stable regardless of the
    order values were first encountered during emission.
    """
    sections: list[str] = []
    if t.colors:
        lines = [
            f"  static const Color {n} = {_color_literal(hx)};"
            for n, hx in sorted(t.colors.items())
        ]
        sections.append(_const_class("AppColors", lines))
    if t.spacings:
        lines = [
            f"  static const double {n} = {_num(v)};"
            for n, v in sorted(t.spacings.items())
        ]
        sections.append(_const_class("AppSpacing", lines))
    if t.text_styles:
        lines = [
            f"  static const TextStyle {n} = {_text_style_literal(sz, w, fam)};"
            for n, (sz, w, fam) in sorted(t.text_styles.items())
        ]
        sections.append(_const_class("AppTextStyles", lines))
    return "\n\n".join(sections)


def _const_class(name: str, lines: list[str]) -> str:
    body = "\n".join(lines)
    return f"abstract final class {name} {{\n{body}\n}}"


def _text_style_literal(size: Any, weight: Any, family: str | None = None) -> str:
    parts: list[str] = []
    if family is not None:
        parts.append(f"fontFamily: {_dart_str(family)}")
    if size is not None:
        parts.append(f"fontSize: {_num(size)}")
    if weight is not None:
        parts.append(f"fontWeight: FontWeight.w{int(weight)}")
    return "TextStyle(" + ", ".join(parts) + ")"


def _wrap_padding(inner: str, pad: dict) -> str:
    return _call("Padding", [f"padding: {_edge_insets(pad)}", f"child: {inner}"])


def _edge_insets(pad: dict) -> str:
    t, r, b, l = pad["top"], pad["right"], pad["bottom"], pad["left"]
    if t == r == b == l:
        return f"EdgeInsets.all({_space(t)})"
    if t == b and l == r:
        return f"EdgeInsets.symmetric(horizontal: {_space(l)}, vertical: {_space(t)})"
    return f"EdgeInsets.fromLTRB({_space(l)}, {_space(t)}, {_space(r)}, {_space(b)})"


def _color(hex_str: str) -> str:
    if _active is not None:
        return _active.color(hex_str)
    return _color_literal(hex_str)


def _color_literal(hex_str: str) -> str:
    h = hex_str.lstrip("#").upper()
    if len(h) == 6:
        return f"Color(0xFF{h})"
    rrggbb, aa = h[:6], h[6:]
    return f"Color(0x{aa}{rrggbb})"


def _space(n: Any) -> str:
    """Emit a layout spacing/padding value, interned as a token when active.

    Only gaps (auto-layout spacing and padding edges) route through here —
    widths, positions, radii and font sizes stay literal via `_num`.
    """
    if _active is not None:
        return _active.spacing(n)
    return _num(n)


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
