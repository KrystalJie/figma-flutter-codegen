from __future__ import annotations

import json
from typing import Any

from agent.codegen import _class_name
from agent.llm import LLMClient, strip_code_fence

PLAN_VERSION = "0.1"


def plan(ir: dict) -> dict:
    """Deterministically turn Design IR v0.1 into a Component Plan v0.1.

    Every frame that carries a `name` is lifted into its own component, and
    its original position is replaced by a component reference node. Unnamed
    frames stay inline. The root screen becomes `rootComponent`. The result
    is what codegen renders into one StatelessWidget per component.

    Pure and deterministic: no IO, stable ordering (root first, then
    extracted components in depth-first order of appearance).
    """
    if ir.get("version") != "0.1":
        raise ValueError(f"unsupported IR version: {ir.get('version')!r}")
    root = ir.get("root")
    if not isinstance(root, dict) or root.get("type") != "screen":
        got = root.get("type") if isinstance(root, dict) else root
        raise ValueError(f"root must be a screen, got {got!r}")

    components: list[dict] = []
    taken: set[str] = set()

    def claim(raw_name: str | None, fallback: str) -> str:
        base = _class_name(raw_name) if raw_name else fallback
        name = base
        n = 2
        while name in taken:
            name = f"{base}{n}"
            n += 1
        taken.add(name)
        return name

    def extract(node: dict) -> dict:
        """Return a copy of a container node with named-frame children
        replaced by component references; recurse into all frames."""
        new_children: list[dict] = []
        for child in node.get("children", []):
            if child.get("type") == "frame" and child.get("name"):
                comp_name = claim(child.get("name"), "Component")
                components.append({"name": comp_name, "root": extract(child)})
                ref: dict = {"type": "component", "ref": comp_name}
                # Preserve absolute position so a Stack parent can place the
                # referenced component with a Positioned wrapper, and the
                # counter-axis fill flag so a flex parent still stretches it.
                if "position" in child:
                    ref["position"] = child["position"]
                if "layoutAlign" in child:
                    ref["layoutAlign"] = child["layoutAlign"]
                new_children.append(ref)
            elif child.get("type") == "frame":
                new_children.append(extract(child))
            else:
                new_children.append(child)
        out = dict(node)
        out["children"] = new_children
        return out

    root_name = claim(root.get("name"), "GeneratedScreen")
    root_component = {"name": root_name, "root": extract(root)}
    components.insert(0, root_component)
    components = _dedupe(components, root_name)
    out: dict[str, Any] = {
        "version": PLAN_VERSION,
        "rootComponent": root_name,
        "components": components,
    }
    # Carry design tokens (e.g. semantic color names) through to codegen.
    if ir.get("tokens"):
        out["tokens"] = ir["tokens"]
    return out


def _dedupe(components: list[dict], root_name: str) -> list[dict]:
    """Merge structurally-identical components into one reusable widget.

    Figma instances of the same component produce identical subtrees (they
    differ only by id/position). Collapsing them removes duplicate classes
    like Card2/Card3 and rewrites every reference to the canonical name.
    Runs to a fixed point so nested duplicates collapse too.
    """
    while True:
        seen: dict[str, str] = {}
        alias: dict[str, str] = {}
        for comp in components:
            key = _struct_key(comp["root"])
            if key in seen and comp["name"] != root_name:
                alias[comp["name"]] = seen[key]
            else:
                seen.setdefault(key, comp["name"])
        if not alias:
            return components
        components = [c for c in components if c["name"] not in alias]
        for comp in components:
            _rewrite_refs(comp["root"], alias)


def _struct_key(node: dict) -> str:
    """Canonical signature of a node ignoring identity/placement fields."""
    return json.dumps(_canonical(node), sort_keys=True)


def _canonical(node: dict) -> dict:
    out: dict[str, Any] = {}
    for k, v in node.items():
        if k in ("id", "position"):
            continue
        out[k] = [_canonical(c) for c in v] if k == "children" else v
    return out


def _rewrite_refs(node: dict, alias: dict[str, str]) -> None:
    for child in node.get("children", []):
        if child.get("type") == "component":
            if child.get("ref") in alias:
                child["ref"] = alias[child["ref"]]
        else:
            _rewrite_refs(child, alias)


# ---------------------------------------------------------------------------
# Optional LLM planner
# ---------------------------------------------------------------------------

_PROMPT_TEMPLATE = """\
You are turning a mobile UI Design IR into a Component Plan for Flutter codegen.

A Component Plan groups the screen into named, reusable Flutter components so
the generated code stays maintainable. Return ONLY a JSON object, with no
explanations, commentary, or markdown code fences.

The Component Plan v0.1 schema is:
- "version": the string "0.1"
- "rootComponent": the name of the entry component (the screen)
- "components": a list of {{ "name": <PascalCase>, "root": <node> }}

Each component's "root" is a screen or frame node reused verbatim from the
Design IR node shapes (frame/text/rectangle/image/button + layout). To
reference one component from inside another, use a node of the form
{{ "type": "component", "ref": <component name> }}. Lift meaningful, named or
repeated groups into their own components; keep trivial wrappers inline.

--- Design IR ---
{ir}
--- end Design IR ---
"""


def build_prompt(ir: dict) -> str:
    """Build the deterministic prompt sent to the LLM planner."""
    return _PROMPT_TEMPLATE.format(ir=json.dumps(ir, indent=2, ensure_ascii=False))


def plan_with_llm(ir: dict, client: LLMClient) -> dict:
    """Ask the LLM to produce a Component Plan from Design IR.

    The response is stripped of any wrapping code fence, parsed as JSON, and
    lightly validated. Deeper structural validity is enforced downstream by
    codegen.
    """
    prompt = build_prompt(ir)
    response = client.complete(prompt)
    text = strip_code_fence(response).strip()
    if not text:
        raise ValueError("LLM returned empty plan response")
    try:
        result: Any = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"LLM returned invalid JSON: {exc}") from exc
    _validate_plan_shape(result)
    if ir.get("tokens") and "tokens" not in result:
        result["tokens"] = ir["tokens"]
    return result


def _validate_plan_shape(plan_obj: Any) -> None:
    if not isinstance(plan_obj, dict):
        raise ValueError("plan must be a JSON object")
    if plan_obj.get("version") != PLAN_VERSION:
        raise ValueError(f"unsupported plan version: {plan_obj.get('version')!r}")
    if not plan_obj.get("rootComponent"):
        raise ValueError("plan missing 'rootComponent'")
    components = plan_obj.get("components")
    if not isinstance(components, list) or not components:
        raise ValueError("plan must have a non-empty 'components' list")
