# figma2flutter-agent

AI-assisted pipeline that converts a Figma mobile screen into maintainable Flutter UI code.

See [claudecode.md](claudecode.md) for the full spec, MVP scope, and development order.

## Layout

```
agent/      pipeline modules (cli, figma_client, ir_parser, planner, codegen, validator, repair, llm)
schemas/    Design IR + Component Plan JSON schemas
examples/   sample Figma JSON, sample Design IR, sample generated Dart
flutter_app/ Flutter app shell (target for generated code)
tests/      pytest suite
```

## Pipeline

```
Figma JSON → Design IR → Component Plan → Flutter code → validate → repair
```

The **planner** turns Design IR into a Component Plan: each named frame is lifted
into its own component so codegen emits one small `StatelessWidget` per component
instead of one giant `build`. Every run writes `component_plan.generated.json`
next to `--output`.

By default the planner is **deterministic** (rule-based). Pass `--llm` to use an
LLM planner instead — this requires a real `LLMClient` (see `agent/llm.py`); the
default `StubLLMClient` fails loudly and tests use a fake client, so the LLM path
is fully optional and never runs in CI.

## Quickstart

```bash
pip install -e .
pytest
```

Target CLI (not yet implemented):

```bash
python -m agent.cli --input examples/figma_sample.json --output flutter_app/lib/generated_screen.dart
```

## Design IR v0.1

The IR is the contract between parser and codegen. See [schemas/design_ir.schema.json](schemas/design_ir.schema.json) and the worked example in [examples/design_ir_sample.json](examples/design_ir_sample.json).

Node types: `screen` (root only), `frame`, `text`, `rectangle`, `image`, `button`.

### Tradeoffs

The schema is deliberately narrow. Each decision below trades expressiveness for a smaller, more deterministic codegen surface.

- **Flat hex colors (`#RRGGBB` / `#RRGGBBAA`).** No gradients, no opacity tokens, no theme references. Designs that depend on gradients or design tokens won't round-trip — fold them into solid colors in the parser.
- **Six concrete node types, no generic vector or component instance.** Anything more exotic in the source Figma file must be flattened or rejected by the parser.
- **`button` is a first-class node, not a tagged frame.** Figma has no native button — the parser is expected to recognize the "button-like frame" pattern (frame + single text child + fill + corner radius) and lift it. Cleaner codegen, but loses fidelity if the source button has icons or multiple children.
- **Flow layout only.** Every container has a `direction` (`vertical` | `horizontal`), `spacing`, `alignment`, `justify`, and `padding`. No absolute positioning, no constraints, no z-index. Free-form designs must be re-laid out as auto-layout before parsing.
- **Fixed-pixel sizing.** `size` is `{ width, height }` in logical pixels — no "fill parent" or "hug contents". Deterministic but rigid; no responsive resizing yet.
- **Padding is an explicit 4-tuple.** No shorthand (`8` or `[8, 16]`). One canonical form, no parsing ambiguity, slightly more verbose.
- **`image.src` is an opaque string.** Asset path or URL — the codegen layer decides how to resolve it. Defers the asset-pipeline decision.
- **No interactions, no state, no variants.** Static rendering only — matches MVP scope.
- **Single mobile-portrait viewport.** No breakpoints, no device targets beyond a single `screen.size`.

These constraints will be revisited once the rule-based codegen path works end-to-end.
