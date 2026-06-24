from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest

from agent import codegen, planner
from agent.codegen import _class_name, _color, _edge_insets

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOTS = Path(__file__).resolve().parent / "snapshots"


def _check_snapshot(name: str, actual: str) -> None:
    path = SNAPSHOTS / name
    if os.environ.get("UPDATE_SNAPSHOTS"):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(actual)
        return
    if not path.exists():
        pytest.fail(
            f"snapshot file missing: {path.relative_to(ROOT)}. "
            "Run with UPDATE_SNAPSHOTS=1 to create."
        )
    expected = path.read_text()
    assert actual == expected, f"snapshot mismatch: {name}"


def _gen(ir: dict) -> str:
    """Render IR end-to-end through the deterministic planner + codegen."""
    return codegen.generate(planner.plan(ir))


def _screen(children: list[dict], **screen_overrides: Any) -> dict:
    root: dict[str, Any] = {
        "id": "s",
        "name": screen_overrides.pop("name", "TestScreen"),
        "type": "screen",
        "layout": screen_overrides.pop("layout", {"direction": "vertical"}),
        "children": children,
    }
    root.update(screen_overrides)
    return {"version": "0.1", "root": root}


# ---------------------------------------------------------------------------
# Snapshot tests (IR -> plan -> Dart)
# ---------------------------------------------------------------------------


def test_snapshot_minimal_screen() -> None:
    _check_snapshot("minimal_screen.dart", _gen(_screen([])))


def test_snapshot_text_styled() -> None:
    ir = _screen(
        [
            {
                "id": "t",
                "type": "text",
                "text": "Hello",
                "fontSize": 24,
                "fontWeight": 700,
                "color": "#111111",
                "textAlign": "center",
            }
        ]
    )
    _check_snapshot("text_styled.dart", _gen(ir))


def test_snapshot_rectangle_rounded() -> None:
    ir = _screen(
        [
            {
                "id": "r",
                "type": "rectangle",
                "fill": "#0A84FF",
                "cornerRadius": 8,
                "size": {"width": 100, "height": 40},
            }
        ]
    )
    _check_snapshot("rectangle_rounded.dart", _gen(ir))


def test_rectangle_border_renders_box_decoration() -> None:
    ir = _screen(
        [
            {
                "id": "r",
                "type": "rectangle",
                "fill": "#FFFFFF",
                "border": {"color": "#E5E5EA", "width": 1},
                "size": {"width": 100, "height": 40},
            }
        ]
    )
    dart = _gen(ir)
    assert "decoration: BoxDecoration(" in dart
    assert "border: Border.all(" in dart
    assert "color: AppColors.ce5e5ea" in dart
    assert "static const Color ce5e5ea = Color(0xFFE5E5EA);" in dart
    assert "width: 1" in dart


def test_frame_border_without_radius_uses_decoration() -> None:
    ir = _screen(
        [
            {
                "id": "f",
                "type": "frame",
                "border": {"color": "#000000"},
                "layout": {"direction": "vertical"},
                "children": [],
            }
        ]
    )
    dart = _gen(ir)
    assert "decoration: BoxDecoration(" in dart
    assert "border: Border.all(" in dart
    assert "color: AppColors.c000000" in dart
    assert "static const Color c000000 = Color(0xFF000000);" in dart
    # width is optional; omitted here, so no width arg should appear
    assert "width:" not in dart


def test_stack_layout_emits_positioned_children() -> None:
    ir = _screen(
        [
            {
                "id": "t",
                "type": "text",
                "text": "Hi",
                "position": {"x": 16, "y": 32},
            }
        ],
        layout={"direction": "stack"},
    )
    dart = _gen(ir)
    assert "Stack(" in dart
    assert "Positioned(" in dart
    assert "left: 16" in dart
    assert "top: 32" in dart
    assert "Column(" not in dart


def test_stack_child_without_position_is_not_wrapped() -> None:
    ir = _screen(
        [{"id": "t", "type": "text", "text": "Hi"}],
        layout={"direction": "stack"},
    )
    dart = _gen(ir)
    assert "Stack(" in dart
    assert "Positioned(" not in dart


def test_icon_with_asset_renders_image_asset() -> None:
    ir = _screen(
        [
            {
                "id": "ic",
                "type": "icon",
                "size": {"width": 15, "height": 5},
                "iconAsset": "assets/images/icon_ic.png",
            }
        ]
    )
    dart = _gen(ir)
    assert "Image.asset(" in dart
    assert "assets/images/icon_ic.png" in dart
    assert "width: 15" in dart


def test_icon_without_asset_reserves_space_with_sized_box() -> None:
    ir = _screen(
        [{"id": "ic", "type": "icon", "size": {"width": 15, "height": 5}}]
    )
    dart = _gen(ir)
    assert "Image.asset(" not in dart
    assert "SizedBox(" in dart
    assert "width: 15" in dart


def test_wrap_text_constrains_width_with_sized_box() -> None:
    ir = _screen(
        [
            {
                "id": "t",
                "type": "text",
                "text": "Long body that should wrap",
                "size": {"width": 269, "height": 40},
                "wrap": True,
            }
        ]
    )
    dart = _gen(ir)
    assert "SizedBox(" in dart
    assert "width: 269" in dart
    assert "child: Text(" in dart


def test_text_without_wrap_flag_stays_bare() -> None:
    ir = _screen(
        [
            {
                "id": "t",
                "type": "text",
                "text": "Single line title",
                "size": {"width": 272, "height": 30},
            }
        ]
    )
    dart = _gen(ir)
    assert "Text(" in dart
    # No width constraint when the text hugs its content (no wrap flag).
    assert "SizedBox(" not in dart


def test_ellipse_with_image_renders_decoration_image() -> None:
    ir = _screen(
        [
            {
                "id": "e",
                "type": "ellipse",
                "size": {"width": 80, "height": 80},
                "imageAsset": "assets/images/abc.png",
                "imageFit": "cover",
            }
        ]
    )
    dart = _gen(ir)
    assert "shape: BoxShape.circle" in dart
    assert "image: DecorationImage(" in dart
    assert "image: AssetImage('assets/images/abc.png')" in dart
    assert "fit: BoxFit.cover" in dart


def test_rectangle_with_image_renders_decoration_image() -> None:
    ir = _screen(
        [
            {
                "id": "r",
                "type": "rectangle",
                "size": {"width": 100, "height": 100},
                "imageAsset": "assets/images/x.png",
                "imageFit": "contain",
            }
        ]
    )
    dart = _gen(ir)
    assert "decoration: BoxDecoration(" in dart
    assert "AssetImage('assets/images/x.png')" in dart
    assert "fit: BoxFit.contain" in dart


def test_ellipse_renders_circle_container() -> None:
    ir = _screen(
        [
            {
                "id": "e",
                "type": "ellipse",
                "size": {"width": 80, "height": 80},
                "fill": "#FF0000",
                "border": {"color": "#FFFFFF", "width": 4},
            }
        ]
    )
    dart = _gen(ir)
    assert "shape: BoxShape.circle" in dart
    assert "color: AppColors.cff0000" in dart
    assert "static const Color cff0000 = Color(0xFFFF0000);" in dart
    assert "border: Border.all(" in dart
    assert "width: 80" in dart


def test_snapshot_image_rounded() -> None:
    ir = _screen(
        [
            {
                "id": "i",
                "type": "image",
                "src": "https://example.com/avatar.png",
                "size": {"width": 80, "height": 80},
                "fit": "cover",
                "cornerRadius": 40,
            }
        ]
    )
    _check_snapshot("image_rounded.dart", _gen(ir))


def test_snapshot_button_styled() -> None:
    ir = _screen(
        [
            {
                "id": "b",
                "type": "button",
                "label": "Continue",
                "background": "#0A84FF",
                "color": "#FFFFFF",
                "cornerRadius": 12,
                "padding": {"top": 12, "right": 16, "bottom": 12, "left": 16},
            }
        ]
    )
    _check_snapshot("button_styled.dart", _gen(ir))


def test_snapshot_nested_frame() -> None:
    ir = _screen(
        [
            {
                "id": "card",
                "type": "frame",
                "background": "#F0F0F0",
                "cornerRadius": 8,
                "layout": {
                    "direction": "vertical",
                    "spacing": 4,
                    "padding": {"top": 8, "right": 8, "bottom": 8, "left": 8},
                },
                "children": [
                    {"id": "t", "type": "text", "text": "Inner"}
                ],
            }
        ]
    )
    _check_snapshot("nested_frame.dart", _gen(ir))


def test_snapshot_full_sample() -> None:
    with open(ROOT / "examples" / "design_ir_sample.json") as f:
        ir = json.load(f)
    _check_snapshot("profile_screen.dart", _gen(ir))


def test_snapshot_named_frame_extracted_into_component() -> None:
    """A named frame becomes its own widget; the screen references it."""
    out = _gen(
        _screen(
            [
                {
                    "id": "card",
                    "name": "InfoCard",
                    "type": "frame",
                    "layout": {"direction": "vertical"},
                    "children": [{"id": "t", "type": "text", "text": "Hi"}],
                }
            ]
        )
    )
    assert "class TestScreen extends StatelessWidget" in out
    assert "class InfoCard extends StatelessWidget" in out
    assert "const InfoCard()" in out


def test_snapshot_handwritten_multi_component_plan() -> None:
    """codegen renders a Component Plan with a reference node directly."""
    plan = {
        "version": "0.1",
        "rootComponent": "HomeScreen",
        "components": [
            {
                "name": "HomeScreen",
                "root": {
                    "id": "s",
                    "type": "screen",
                    "layout": {"direction": "vertical", "spacing": 8},
                    "children": [
                        {"id": "t", "type": "text", "text": "Home"},
                        {"type": "component", "ref": "Card"},
                    ],
                },
            },
            {
                "name": "Card",
                "root": {
                    "id": "c",
                    "type": "frame",
                    "background": "#EEEEEE",
                    "layout": {"direction": "vertical"},
                    "children": [{"id": "ct", "type": "text", "text": "Card body"}],
                },
            },
        ],
    }
    _check_snapshot("two_components.dart", codegen.generate(plan))


# ---------------------------------------------------------------------------
# Class name handling
# ---------------------------------------------------------------------------


def test_class_name_uses_screen_name() -> None:
    out = _gen(_screen([], name="MyScreen"))
    assert "class MyScreen extends StatelessWidget" in out


def test_class_name_capitalizes_lowercase() -> None:
    out = _gen(_screen([], name="login"))
    assert "class Login extends StatelessWidget" in out


def test_class_name_strips_invalid_chars() -> None:
    out = _gen(_screen([], name="Login Screen!"))
    assert "class LoginScreen extends StatelessWidget" in out


def test_class_name_falls_back_when_invalid() -> None:
    out = _gen(_screen([], name="123-bad"))
    assert "class GeneratedScreen extends StatelessWidget" in out


# ---------------------------------------------------------------------------
# Error handling (codegen consumes a Component Plan)
# ---------------------------------------------------------------------------


def test_unsupported_plan_version_raises() -> None:
    with pytest.raises(ValueError, match="unsupported plan version"):
        codegen.generate({"version": "0.2", "components": []})


def test_empty_components_raises() -> None:
    with pytest.raises(ValueError, match="no components"):
        codegen.generate({"version": "0.1", "rootComponent": "X", "components": []})


def test_unsupported_child_type_raises() -> None:
    plan = planner.plan(_screen([]))
    plan["components"][0]["root"]["children"] = [{"id": "x", "type": "vector"}]
    with pytest.raises(ValueError, match="unsupported IR node type"):
        codegen.generate(plan)


# ---------------------------------------------------------------------------
# Helper unit tests
# ---------------------------------------------------------------------------


def test_color_6_char_hex() -> None:
    assert _color("#FFFFFF") == "Color(0xFFFFFFFF)"


def test_color_8_char_hex_reorders_to_argb() -> None:
    assert _color("#00000080") == "Color(0x80000000)"


def test_color_lowercase_input_is_normalized() -> None:
    assert _color("#abc123") == "Color(0xFFABC123)"


def test_edge_insets_all_equal_uses_all() -> None:
    assert _edge_insets({"top": 8, "right": 8, "bottom": 8, "left": 8}) == "EdgeInsets.all(8)"


def test_edge_insets_symmetric() -> None:
    pad = {"top": 8, "right": 16, "bottom": 8, "left": 16}
    assert _edge_insets(pad) == "EdgeInsets.symmetric(horizontal: 16, vertical: 8)"


def test_edge_insets_generic_uses_fromLTRB() -> None:
    pad = {"top": 1, "right": 2, "bottom": 3, "left": 4}
    assert _edge_insets(pad) == "EdgeInsets.fromLTRB(4, 1, 2, 3)"


def test_class_name_none() -> None:
    assert _class_name(None) == "GeneratedScreen"


def test_class_name_empty() -> None:
    assert _class_name("") == "GeneratedScreen"


def test_class_name_unicode_stripped_to_empty_falls_back() -> None:
    assert _class_name("___") == "___"  # underscores are valid identifier chars
    assert _class_name("...") == "GeneratedScreen"


# ---------------------------------------------------------------------------
# Opt-in node keying (for geometry rect capture)
# ---------------------------------------------------------------------------


def test_keyed_wraps_id_bearing_nodes() -> None:
    ir = _screen([{"id": "1:1", "type": "text", "text": "Hi"}])
    dart = codegen.generate(planner.plan(ir), keyed=True)
    assert "KeyedSubtree(" in dart
    assert "key: ValueKey('1:1')" in dart


def test_keying_is_off_by_default() -> None:
    ir = _screen([{"id": "1:1", "type": "text", "text": "Hi"}])
    assert "KeyedSubtree(" not in codegen.generate(planner.plan(ir))


def test_keyed_skips_component_references() -> None:
    # A component reference renders as `const X()`; its id is not unique across
    # deduped instances, so it must not be keyed.
    plan = {
        "version": "0.1",
        "rootComponent": "Screen",
        "components": [
            {
                "name": "Screen",
                "root": {
                    "id": "s",
                    "type": "screen",
                    "layout": {"direction": "vertical"},
                    "children": [{"id": "ref", "type": "component", "ref": "Card"}],
                },
            },
            {
                "name": "Card",
                "root": {"id": "c", "type": "rectangle", "size": {"width": 10, "height": 10}},
            },
        ],
    }
    dart = codegen.generate(plan, keyed=True)
    assert "ValueKey('ref')" not in dart


def test_text_emits_font_family() -> None:
    ir = _screen(
        [{"id": "t", "type": "text", "text": "Hi", "fontFamily": "Inter", "fontSize": 14, "fontWeight": 400}]
    )
    dart = codegen.generate(planner.plan(ir))
    assert "fontFamily: 'Inter'" in dart


def test_text_line_height_emitted_via_copywith() -> None:
    ir = _screen(
        [{"id": "t", "type": "text", "text": "Hi", "fontSize": 16, "fontWeight": 400, "lineHeight": 1.21}]
    )
    dart = codegen.generate(planner.plan(ir))
    assert "height: 1.21" in dart


# ---------------------------------------------------------------------------
# Per-child counter-axis fill (layoutAlign)
# ---------------------------------------------------------------------------


def test_stretch_kept_when_no_layout_align() -> None:
    # Backward compat: a stretch frame with no per-child info stretches all
    # children via CrossAxisAlignment.stretch and never wraps in a SizedBox.
    ir = _screen(
        [
            {"id": "a", "type": "text", "text": "A"},
            {"id": "b", "type": "text", "text": "B"},
        ],
        layout={"direction": "vertical", "alignment": "stretch"},
    )
    dart = _gen(ir)
    assert "CrossAxisAlignment.stretch" in dart
    assert "double.infinity" not in dart


def test_stretch_demoted_when_a_child_hugs() -> None:
    # A stretch frame with a hug-content text + a fill child must NOT stretch
    # the text: demote to start and expand only the opted-in child.
    ir = _screen(
        [
            {"id": "t", "type": "text", "text": "Title", "fontSize": 20},
            {
                "id": "r",
                "type": "rectangle",
                "layoutAlign": "stretch",
                "size": {"width": 100, "height": 10},
                "fill": "#FF0000",
            },
        ],
        layout={"direction": "vertical", "alignment": "stretch"},
    )
    dart = _gen(ir)
    assert "CrossAxisAlignment.start" in dart
    assert "CrossAxisAlignment.stretch" not in dart
    assert "width: double.infinity" in dart


def test_row_does_not_expand_fill_child() -> None:
    # A Row's counter axis is height (usually unbounded), so a fill child must
    # not be wrapped in double.infinity even when it opts in.
    ir = _screen(
        [
            {"id": "t", "type": "text", "text": "X"},
            {
                "id": "r",
                "type": "rectangle",
                "layoutAlign": "stretch",
                "size": {"width": 10, "height": 10},
                "fill": "#FF0000",
            },
        ],
        layout={"direction": "horizontal", "alignment": "stretch"},
    )
    dart = _gen(ir)
    assert "double.infinity" not in dart
