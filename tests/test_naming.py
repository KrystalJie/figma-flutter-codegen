from __future__ import annotations

import pytest

from agent import codegen, naming, planner


class FakeLLM:
    """Records the prompt it received and returns a canned response."""

    def __init__(self, response: str) -> None:
        self.response = response
        self.calls: list[str] = []

    def complete(self, prompt: str) -> str:
        self.calls.append(prompt)
        return self.response


class ExplodingLLM:
    """Stand-in for the stub client when no API key is configured."""

    def complete(self, prompt: str) -> str:
        raise NotImplementedError("no LLM client configured")


def _ir(children: list[dict], **root: object) -> dict:
    base = {"id": "s", "type": "screen", "layout": {"direction": "vertical"}, "children": children}
    base.update(root)
    return {"version": "0.1", "root": base}


# ---------------------------------------------------------------------------
# collect_colors
# ---------------------------------------------------------------------------


def test_collect_colors_walks_all_color_slots_in_order() -> None:
    ir = _ir(
        [
            {"id": "t", "type": "text", "text": "Hi", "color": "#111111"},
            {"id": "r", "type": "rectangle", "fill": "#FF0000", "border": {"color": "#00FF00"}},
            {"id": "dup", "type": "text", "text": "again", "color": "#111111"},
        ],
        background="#FFFFFF",
    )
    assert naming.collect_colors(ir) == ["#FFFFFF", "#111111", "#FF0000", "#00FF00"]


# ---------------------------------------------------------------------------
# propose_color_names
# ---------------------------------------------------------------------------


def test_empty_colors_does_not_call_client() -> None:
    client = FakeLLM("{}")
    assert naming.propose_color_names([], client) == {}
    assert client.calls == []


def test_proposes_names_and_drops_unknown_or_nonstring() -> None:
    client = FakeLLM('{"#FFFFFF": "background", "#111111": "textPrimary", "#999999": 42, "#BADHEX": "x"}')
    out = naming.propose_color_names(["#FFFFFF", "#111111", "#999999"], client)
    assert out == {"#FFFFFF": "background", "#111111": "textPrimary"}


def test_strips_code_fence() -> None:
    client = FakeLLM('```json\n{"#FFFFFF": "surface"}\n```')
    assert naming.propose_color_names(["#FFFFFF"], client) == {"#FFFFFF": "surface"}


def test_invalid_json_raises() -> None:
    with pytest.raises(ValueError, match="invalid JSON"):
        naming.propose_color_names(["#FFFFFF"], FakeLLM("not json"))


def test_non_object_response_raises() -> None:
    with pytest.raises(ValueError, match="must be a JSON object"):
        naming.propose_color_names(["#FFFFFF"], FakeLLM('["a", "b"]'))


# ---------------------------------------------------------------------------
# attach_color_names (merge semantics + end-to-end into codegen)
# ---------------------------------------------------------------------------


def test_published_style_names_win_over_llm() -> None:
    ir = _ir([{"id": "t", "type": "text", "text": "Hi", "color": "#111111"}], background="#FFFFFF")
    ir["tokens"] = {"colors": {"#FFFFFF": "white"}}  # route B already named white
    client = FakeLLM('{"#111111": "textPrimary"}')
    added = naming.attach_color_names(ir, client)
    assert added == {"#111111": "textPrimary"}
    assert ir["tokens"]["colors"] == {"#FFFFFF": "white", "#111111": "textPrimary"}
    # the already-styled color is never sent to the LLM
    assert "#FFFFFF" not in client.calls[0]


def test_llm_names_flow_into_appcolors_constants() -> None:
    ir = _ir([{"id": "t", "type": "text", "text": "Hi", "color": "#3366E6"}], background="#FFFFFF")
    client = FakeLLM('{"#FFFFFF": "background", "#3366E6": "brandPrimary"}')
    naming.attach_color_names(ir, client)
    dart = codegen.generate(planner.plan(ir))
    assert "AppColors.brandPrimary" in dart
    assert "AppColors.background" in dart


def test_attach_is_noop_when_nothing_added() -> None:
    ir = _ir([{"id": "t", "type": "text", "text": "Hi", "color": "#111111"}])
    client = FakeLLM("{}")  # model proposes nothing usable
    assert naming.attach_color_names(ir, client) == {}
    assert "tokens" not in ir  # no empty token table created


def test_failure_propagates_for_caller_to_handle() -> None:
    ir = _ir([{"id": "t", "type": "text", "text": "Hi", "color": "#111111"}])
    with pytest.raises(NotImplementedError):
        naming.attach_color_names(ir, ExplodingLLM())
