from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from agent import codegen, planner
from agent.llm import LLMClient

ROOT = Path(__file__).resolve().parent.parent


class FakeLLM:
    """Records the prompt it received and returns a canned response."""

    def __init__(self, response: str) -> None:
        self.response = response
        self.calls: list[str] = []

    def complete(self, prompt: str) -> str:
        self.calls.append(prompt)
        return self.response


def _screen(children: list[dict], **overrides: Any) -> dict:
    root: dict[str, Any] = {
        "id": "s",
        "name": overrides.pop("name", "Home"),
        "type": "screen",
        "layout": {"direction": "vertical"},
        "children": children,
    }
    root.update(overrides)
    return {"version": "0.1", "root": root}


def _frame(id_: str, children: list[dict], **extra: Any) -> dict:
    node: dict[str, Any] = {
        "id": id_,
        "type": "frame",
        "layout": {"direction": "vertical"},
        "children": children,
    }
    node.update(extra)
    return node


# ---------------------------------------------------------------------------
# Deterministic planner
# ---------------------------------------------------------------------------


def test_root_screen_becomes_root_component() -> None:
    plan = planner.plan(_screen([], name="Home"))
    assert plan["version"] == "0.1"
    assert plan["rootComponent"] == "Home"
    assert [c["name"] for c in plan["components"]] == ["Home"]


def test_named_frame_is_extracted_and_referenced() -> None:
    ir = _screen([_frame("card", [{"id": "t", "type": "text", "text": "x"}], name="InfoCard")])
    plan = planner.plan(ir)

    names = [c["name"] for c in plan["components"]]
    assert names == ["Home", "InfoCard"]

    root = next(c for c in plan["components"] if c["name"] == "Home")["root"]
    assert root["children"] == [{"type": "component", "ref": "InfoCard"}]

    info = next(c for c in plan["components"] if c["name"] == "InfoCard")["root"]
    assert info["type"] == "frame"
    assert info["children"][0]["text"] == "x"


def test_component_ref_preserves_position() -> None:
    card = _frame(
        "card", [{"id": "t", "type": "text", "text": "x"}], name="InfoCard"
    )
    card["position"] = {"x": 12, "y": 34}
    ir = _screen([card], layout={"direction": "stack"})
    plan = planner.plan(ir)
    root = next(c for c in plan["components"] if c["name"] == "Home")["root"]
    assert root["children"] == [
        {"type": "component", "ref": "InfoCard", "position": {"x": 12, "y": 34}}
    ]


def test_unnamed_frame_stays_inline() -> None:
    ir = _screen([_frame("card", [{"id": "t", "type": "text", "text": "x"}])])
    plan = planner.plan(ir)
    assert [c["name"] for c in plan["components"]] == ["Home"]
    assert plan["components"][0]["root"]["children"][0]["type"] == "frame"


def test_nested_named_frames_are_all_extracted() -> None:
    inner = _frame("inner", [{"id": "t", "type": "text", "text": "x"}], name="Inner")
    outer = _frame("outer", [inner], name="Outer")
    plan = planner.plan(_screen([outer]))
    assert sorted(c["name"] for c in plan["components"]) == ["Home", "Inner", "Outer"]
    outer_comp = next(c for c in plan["components"] if c["name"] == "Outer")["root"]
    assert outer_comp["children"] == [{"type": "component", "ref": "Inner"}]


def test_duplicate_names_get_numeric_suffix() -> None:
    ir = _screen(
        [
            _frame("a", [{"id": "t1", "type": "text", "text": "1"}], name="Card"),
            _frame("b", [{"id": "t2", "type": "text", "text": "2"}], name="Card"),
        ]
    )
    plan = planner.plan(ir)
    names = [c["name"] for c in plan["components"]]
    assert names == ["Home", "Card", "Card2"]
    refs = [ch["ref"] for ch in plan["components"][0]["root"]["children"]]
    assert refs == ["Card", "Card2"]


def test_identical_instances_are_deduped_into_one_component() -> None:
    # Same structure (text/size), differing only by id + position — like four
    # Figma instances of one component placed at different y offsets.
    def block(id_: str, y: int) -> dict:
        f = _frame(id_, [{"id": id_ + "t", "type": "text", "text": "Header"}], name="Card")
        f["position"] = {"x": 0, "y": y}
        return f

    ir = _screen(
        [block("a", 0), block("b", 100), block("c", 200)],
        layout={"direction": "stack"},
    )
    plan = planner.plan(ir)
    # Only one Card component remains (plus the Home root).
    assert [c["name"] for c in plan["components"]] == ["Home", "Card"]
    # All three references point to the same canonical component.
    refs = [ch["ref"] for ch in plan["components"][0]["root"]["children"]]
    assert refs == ["Card", "Card", "Card"]
    # Positions are preserved on the references.
    ys = [ch["position"]["y"] for ch in plan["components"][0]["root"]["children"]]
    assert ys == [0, 100, 200]


def test_plan_output_feeds_codegen() -> None:
    with open(ROOT / "examples" / "design_ir_sample.json") as f:
        ir = json.load(f)
    plan = planner.plan(ir)
    dart = codegen.generate(plan)
    assert "class ProfileScreen extends StatelessWidget" in dart
    assert "class InfoCard extends StatelessWidget" in dart
    assert "const InfoCard()" in dart


def test_plan_is_deterministic() -> None:
    ir = _screen([_frame("card", [{"id": "t", "type": "text", "text": "x"}], name="InfoCard")])
    assert planner.plan(ir) == planner.plan(ir)


def test_unsupported_ir_version_raises() -> None:
    with pytest.raises(ValueError, match="unsupported IR version"):
        planner.plan({"version": "0.2", "root": {"type": "screen"}})


def test_non_screen_root_raises() -> None:
    with pytest.raises(ValueError, match="screen"):
        planner.plan({"version": "0.1", "root": {"type": "frame"}})


# ---------------------------------------------------------------------------
# Optional LLM planner
# ---------------------------------------------------------------------------

_VALID_PLAN = {
    "version": "0.1",
    "rootComponent": "Home",
    "components": [
        {
            "name": "Home",
            "root": {
                "id": "s",
                "type": "screen",
                "layout": {"direction": "vertical"},
                "children": [],
            },
        }
    ],
}


def test_plan_with_llm_parses_json_response() -> None:
    client = FakeLLM(json.dumps(_VALID_PLAN))
    out = planner.plan_with_llm(_screen([]), client)
    assert out == _VALID_PLAN
    assert len(client.calls) == 1


def test_plan_with_llm_strips_code_fence() -> None:
    fenced = "```json\n" + json.dumps(_VALID_PLAN) + "\n```"
    out = planner.plan_with_llm(_screen([]), FakeLLM(fenced))
    assert out == _VALID_PLAN


def test_prompt_includes_ir_and_asks_for_json() -> None:
    client = FakeLLM(json.dumps(_VALID_PLAN))
    planner.plan_with_llm(_screen([], name="Profile"), client)
    prompt = client.calls[0]
    assert "Profile" in prompt
    assert "JSON" in prompt
    assert "Component Plan" in prompt


def test_plan_with_llm_empty_response_raises() -> None:
    with pytest.raises(ValueError, match="empty"):
        planner.plan_with_llm(_screen([]), FakeLLM("   \n  "))


def test_plan_with_llm_invalid_json_raises() -> None:
    with pytest.raises(ValueError, match="invalid JSON"):
        planner.plan_with_llm(_screen([]), FakeLLM("{not json"))


def test_plan_with_llm_wrong_version_raises() -> None:
    bad = dict(_VALID_PLAN, version="0.9")
    with pytest.raises(ValueError, match="unsupported plan version"):
        planner.plan_with_llm(_screen([]), FakeLLM(json.dumps(bad)))


def test_plan_with_llm_missing_components_raises() -> None:
    bad = {"version": "0.1", "rootComponent": "Home"}
    with pytest.raises(ValueError, match="components"):
        planner.plan_with_llm(_screen([]), FakeLLM(json.dumps(bad)))


def test_plan_with_llm_missing_root_component_raises() -> None:
    bad = {"version": "0.1", "components": _VALID_PLAN["components"]}
    with pytest.raises(ValueError, match="rootComponent"):
        planner.plan_with_llm(_screen([]), FakeLLM(json.dumps(bad)))


def test_fake_llm_satisfies_protocol() -> None:
    client: LLMClient = FakeLLM("x")
    assert client.complete("ping") == "x"
