from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent import ir_parser

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "examples"


def _frame(id_: str = "1", **overrides) -> dict:
    base = {"id": id_, "type": "FRAME", "layoutMode": "VERTICAL", "children": []}
    base.update(overrides)
    return base


def test_root_must_be_frame() -> None:
    with pytest.raises(ValueError, match="root must be a FRAME"):
        ir_parser.parse({"id": "1", "type": "TEXT", "characters": "x"})


def test_screen_basic_shape() -> None:
    out = ir_parser.parse(_frame("scr", name="S"))
    assert out["version"] == "0.1"
    assert out["root"]["type"] == "screen"
    assert out["root"]["id"] == "scr"
    assert out["root"]["name"] == "S"
    assert out["root"]["layout"] == {"direction": "vertical"}
    assert out["root"]["children"] == []


def test_layout_fields_mapped() -> None:
    fig = _frame(
        layoutMode="HORIZONTAL",
        itemSpacing=8,
        primaryAxisAlignItems="SPACE_BETWEEN",
        counterAxisAlignItems="CENTER",
        paddingTop=10,
        paddingRight=12,
        paddingBottom=10,
        paddingLeft=12,
    )
    assert ir_parser.parse(fig)["root"]["layout"] == {
        "direction": "horizontal",
        "spacing": 8,
        "alignment": "center",
        "justify": "spaceBetween",
        "padding": {"top": 10, "right": 12, "bottom": 10, "left": 12},
    }


def test_solid_fill_to_hex() -> None:
    fig = _frame(fills=[{"type": "SOLID", "color": {"r": 1, "g": 1, "b": 1, "a": 1}}])
    assert ir_parser.parse(fig)["root"]["background"] == "#FFFFFF"


def test_color_with_alpha_emits_8_char_hex() -> None:
    fig = _frame(fills=[{"type": "SOLID", "color": {"r": 0, "g": 0, "b": 0, "a": 0.5}}])
    assert ir_parser.parse(fig)["root"]["background"] == "#00000080"


def test_size_from_bounding_box() -> None:
    fig = _frame(absoluteBoundingBox={"x": 0, "y": 0, "width": 390, "height": 844})
    assert ir_parser.parse(fig)["root"]["size"] == {"width": 390, "height": 844}


def test_parse_text_child() -> None:
    fig = _frame(
        children=[
            {
                "id": "t1",
                "type": "TEXT",
                "characters": "Hello",
                "style": {
                    "fontSize": 20,
                    "fontWeight": 700,
                    "textAlignHorizontal": "CENTER",
                },
                "fills": [{"type": "SOLID", "color": {"r": 0, "g": 0, "b": 0, "a": 1}}],
            }
        ]
    )
    [child] = ir_parser.parse(fig)["root"]["children"]
    assert child == {
        "id": "t1",
        "type": "text",
        "text": "Hello",
        "fontSize": 20,
        "fontWeight": 700,
        "color": "#000000",
        "textAlign": "center",
    }


def test_parse_rectangle_child() -> None:
    fig = _frame(
        children=[
            {
                "id": "r1",
                "type": "RECTANGLE",
                "absoluteBoundingBox": {"width": 100, "height": 1},
                "fills": [{"type": "SOLID", "color": {"r": 0.5, "g": 0.5, "b": 0.5, "a": 1}}],
                "cornerRadius": 4,
            }
        ]
    )
    [child] = ir_parser.parse(fig)["root"]["children"]
    assert child == {
        "id": "r1",
        "type": "rectangle",
        "size": {"width": 100, "height": 1},
        "fill": "#808080",
        "cornerRadius": 4,
    }


def test_parse_image_child() -> None:
    fig = _frame(
        children=[
            {
                "id": "i1",
                "type": "IMAGE",
                "src": "assets/x.png",
                "scaleMode": "FILL",
                "cornerRadius": 8,
            }
        ]
    )
    [child] = ir_parser.parse(fig)["root"]["children"]
    assert child == {
        "id": "i1",
        "type": "image",
        "src": "assets/x.png",
        "fit": "cover",
        "cornerRadius": 8,
    }


def test_image_missing_src_raises() -> None:
    fig = _frame(children=[{"id": "i1", "type": "IMAGE"}])
    with pytest.raises(ValueError, match="missing 'src'"):
        ir_parser.parse(fig)


def test_unsupported_type_raises() -> None:
    fig = _frame(children=[{"id": "v1", "type": "VECTOR"}])
    with pytest.raises(ValueError, match="unsupported"):
        ir_parser.parse(fig)


def test_frame_without_layout_mode_raises() -> None:
    with pytest.raises(ValueError, match="layoutMode"):
        ir_parser.parse({"id": "1", "type": "FRAME", "children": []})


def test_nested_frame_recurses() -> None:
    fig = _frame(
        children=[
            {
                "id": "card",
                "type": "FRAME",
                "layoutMode": "VERTICAL",
                "itemSpacing": 4,
                "children": [{"id": "t", "type": "TEXT", "characters": "Hi"}],
            }
        ]
    )
    [card] = ir_parser.parse(fig)["root"]["children"]
    assert card["type"] == "frame"
    assert card["layout"] == {"direction": "vertical", "spacing": 4}
    assert card["children"][0] == {"id": "t", "type": "text", "text": "Hi"}


def test_full_sample_file_round_trip() -> None:
    with open(SAMPLE_DIR / "figma_sample.json") as f:
        figma = json.load(f)
    out = ir_parser.parse(figma)
    root = out["root"]
    assert out["version"] == "0.1"
    assert root["type"] == "screen"
    assert root["id"] == "1:1"
    assert root["name"] == "ProfileScreen"
    assert root["size"] == {"width": 390, "height": 844}
    assert root["background"] == "#FFFFFF"
    assert root["layout"]["alignment"] == "stretch"
    assert [c["type"] for c in root["children"]] == ["text", "image", "frame"]
    card = root["children"][2]
    assert card["name"] == "InfoCard"
    assert card["background"] == "#F5F5F7"
    assert card["cornerRadius"] == 12
    assert [c["type"] for c in card["children"]] == ["text", "rectangle"]
    assert card["children"][1]["fill"] == "#E5E5EA"
