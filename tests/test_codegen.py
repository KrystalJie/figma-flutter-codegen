from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest

from agent import codegen
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
# Snapshot tests
# ---------------------------------------------------------------------------


def test_snapshot_minimal_screen() -> None:
    _check_snapshot("minimal_screen.dart", codegen.generate(_screen([])))


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
    _check_snapshot("text_styled.dart", codegen.generate(ir))


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
    _check_snapshot("rectangle_rounded.dart", codegen.generate(ir))


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
    _check_snapshot("image_rounded.dart", codegen.generate(ir))


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
    _check_snapshot("button_styled.dart", codegen.generate(ir))


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
    _check_snapshot("nested_frame.dart", codegen.generate(ir))


def test_snapshot_full_sample() -> None:
    with open(ROOT / "examples" / "design_ir_sample.json") as f:
        ir = json.load(f)
    _check_snapshot("profile_screen.dart", codegen.generate(ir))


# ---------------------------------------------------------------------------
# Class name handling
# ---------------------------------------------------------------------------


def test_class_name_uses_screen_name() -> None:
    out = codegen.generate(_screen([], name="MyScreen"))
    assert "class MyScreen extends StatelessWidget" in out


def test_class_name_capitalizes_lowercase() -> None:
    out = codegen.generate(_screen([], name="login"))
    assert "class Login extends StatelessWidget" in out


def test_class_name_strips_invalid_chars() -> None:
    out = codegen.generate(_screen([], name="Login Screen!"))
    assert "class LoginScreen extends StatelessWidget" in out


def test_class_name_falls_back_when_invalid() -> None:
    out = codegen.generate(_screen([], name="123-bad"))
    assert "class GeneratedScreen extends StatelessWidget" in out


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


def test_unsupported_version_raises() -> None:
    with pytest.raises(ValueError, match="unsupported IR version"):
        codegen.generate({"version": "0.2", "root": {"type": "screen"}})


def test_non_screen_root_raises() -> None:
    with pytest.raises(ValueError, match="screen"):
        codegen.generate({"version": "0.1", "root": {"type": "frame"}})


def test_unsupported_child_type_raises() -> None:
    ir = _screen([{"id": "x", "type": "vector"}])
    with pytest.raises(ValueError, match="unsupported IR node type"):
        codegen.generate(ir)


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
