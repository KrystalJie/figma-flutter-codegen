from __future__ import annotations

import json
from typing import Any

from agent.llm import LLMClient, strip_code_fence

"""LLM semantic color naming (token route C).

Routes A/B (see ``agent.tokens``) name colors either value-derived (`c<hex>`)
or from a published Figma fill Style. Many real files publish no Styles, so
their colors stay opaque (`AppColors.c3366e6`). This module asks an LLM to
propose human-meaningful lowerCamelCase names (`brandPrimary`, `textMuted`,
`divider`) for those un-styled colors, returning the *same* `hex -> name` map
shape route B produces — so codegen consumes it through the existing
``Tokens(color_names=...)`` path with no new downstream surface.

Deterministic by default: this only runs when the CLI is given ``--llm-names``
and a real LLM client. Tests inject a fake client, so no network call happens.
"""

_COLOR_KEYS = ("background", "fill", "color")


def collect_colors(ir: dict) -> list[str]:
    """Distinct solid colors used in the IR, in first-seen (stable) order."""
    seen: dict[str, None] = {}
    root = ir.get("root")
    if isinstance(root, dict):
        _walk_colors(root, seen)
    return list(seen)


def _walk_colors(node: dict, seen: dict[str, None]) -> None:
    for key in _COLOR_KEYS:
        value = node.get(key)
        if isinstance(value, str):
            seen.setdefault(value, None)
    border = node.get("border")
    if isinstance(border, dict) and isinstance(border.get("color"), str):
        seen.setdefault(border["color"], None)
    for child in node.get("children") or []:
        if isinstance(child, dict):
            _walk_colors(child, seen)


_PROMPT_TEMPLATE = """\
You are naming colors for a Flutter design-token file generated from a mobile UI.

Given the hex colors below (each used somewhere in one screen), return ONLY a
JSON object mapping each hex string to a short, semantic, lowerCamelCase name
describing the role the color most likely plays — e.g. "background", "surface",
"textPrimary", "textMuted", "brandPrimary", "divider", "danger". Use distinct
names. Do not invent extra keys, add commentary, or wrap the JSON in a code
fence.

Colors:
{colors}
"""


def build_color_naming_prompt(colors: list[str]) -> str:
    """Build the prompt asking the LLM to name a list of hex colors."""
    listing = "\n".join(f"- {c}" for c in colors)
    return _PROMPT_TEMPLATE.format(colors=listing)


def propose_color_names(colors: list[str], client: LLMClient) -> dict[str, str]:
    """Ask the LLM for `hex -> semantic name`, keeping only valid entries.

    Robust to a messy response: unknown hexes and non-string names are dropped,
    a wrapping code fence is stripped, and an empty input short-circuits without
    calling the client. Downstream (`tokens._sanitize_ident`) camelCases the
    names and resolves any collisions, so light validation here is enough.
    """
    if not colors:
        return {}
    text = strip_code_fence(client.complete(build_color_naming_prompt(colors))).strip()
    if not text:
        raise ValueError("LLM returned an empty color-naming response")
    try:
        data: Any = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"LLM returned invalid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("color-naming response must be a JSON object")
    out: dict[str, str] = {}
    for hex_str in colors:
        name = data.get(hex_str)
        if isinstance(name, str) and name.strip():
            out[hex_str] = name.strip()
    return out


def attach_color_names(ir: dict, client: LLMClient) -> dict[str, str]:
    """Propose names for IR colors with no published Style and merge them in.

    Route B names (already on ``ir["tokens"]["colors"]``) win over LLM names.
    Returns the LLM-proposed subset that was added (for logging/tests).
    """
    existing = (ir.get("tokens") or {}).get("colors") or {}
    unnamed = [c for c in collect_colors(ir) if c not in existing]
    proposed = propose_color_names(unnamed, client)
    if proposed:
        merged = {**proposed, **existing}  # published Styles take precedence
        ir.setdefault("tokens", {})["colors"] = merged
    return proposed
