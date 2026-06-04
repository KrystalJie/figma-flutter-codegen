# Figma2Flutter Agent

## Project Goal

Build an AI-assisted pipeline that converts a Figma mobile screen into maintainable Flutter UI code.

The MVP scope is intentionally small:
- Input: one Figma node JSON file or Figma node URL.
- Output: one runnable Flutter screen.
- Target: Flutter only.
- Platform: mobile portrait.
- UI scope: static layout only.
- Supported elements: frame, text, rectangle, image, button-like frame.
- Supported layout: vertical / horizontal auto layout, padding, spacing, alignment.

## Architecture

The pipeline is:

Figma JSON
→ Design IR
→ Component Plan
→ Flutter Code
→ Validation
→ Repair

Core modules:

- `figma_client`: fetches Figma node JSON.
- `ir_parser`: converts raw Figma JSON into Design IR.
- `planner`: creates a component/layout plan from Design IR.
- `codegen`: generates Dart / Flutter code from the plan.
- `validator`: runs `flutter analyze` and collects errors.
- `repair`: patches generated code based on validation errors.

## Current MVP Rules

Do not build a full product UI.
Do not build a Figma plugin.
Do not support React Native yet.
Do not implement complex interactions.
Do not over-engineer multi-agent orchestration.

Prefer simple files, clear boundaries, and testable functions.

## Tech Stack

- Python for the agent pipeline.
- Flutter/Dart for generated output.
- JSON Schema or Pydantic for Design IR.
- CLI entry point for running the pipeline.

## Expected Repository Structure

figma2flutter-agent/
├── agent/
│   ├── cli.py
│   ├── figma_client.py
│   ├── ir_parser.py
│   ├── planner.py
│   ├── codegen.py
│   ├── validator.py
│   └── repair.py
├── schemas/
│   └── design_ir.schema.json
├── examples/
│   ├── figma_sample.json
│   ├── design_ir_sample.json
│   └── generated_screen.dart
├── flutter_app/
├── tests/
└── README.md

## Coding Rules

- Keep functions small.
- Add type hints.
- Add unit tests for parser and codegen.
- Do not hide errors.
- Do not call external APIs in tests.
- Keep generated Flutter code readable.
- Prefer deterministic code generation before adding LLM generation.

## Development Order

1. Create repo structure.
2. Define Design IR schema.
3. Add sample Figma JSON.
4. Implement Figma JSON → Design IR parser.
5. Implement rule-based Flutter code generator.
6. Add CLI.
7. Add Flutter app shell.
8. Add `flutter analyze` validator.
9. Add deterministic planner + Component Plan layer (IR → Plan → codegen). Done: `schemas/component_plan.schema.json`, `agent/planner.py`.
10. Add repair loop.
11. Add optional LLM planner (`--llm`, interface via `agent/llm.py`). Real provider not wired yet; default stays deterministic.
12. Wire real Figma source (`agent/figma_client.py`): fetch a node via the Figma REST API (`FIGMA_TOKEN`), CLI `--figma-url`/`--figma-token`, save raw response (`figma_raw.json`) for debug. Parser now skips unsupported node types and falls back to vertical layout for non-auto-layout frames, collecting warnings printed to stderr.
13. Add border support: `strokes`/`strokeWeight` → IR `border` ({color, width?}) on frame/rectangle (schema + parser), rendered via `BoxDecoration(border: Border.all(...))` in codegen.
14. Broaden real-Figma node coverage: INSTANCE/GROUP parsed as frames (recurse into children); ELLIPSE → IR `ellipse` type rendered as a circular Container (`BoxShape.circle`). Size-only frames emit `SizedBox` (not `Container`) to keep `flutter analyze` clean. Verified end-to-end on a real Community UI-kit node.
15. Add deterministic absolute-positioning fallback: frames without auto-layout now map to IR `layout.direction = "stack"` and children get a `position` ({x, y}) relative to the parent (from `absoluteBoundingBox`). Codegen emits `Stack` + `Positioned`. Auto-layout frames still use `Column`/`Row`. The planner copies `position` onto component-reference nodes so lifted components are still placed by a `Positioned` in a Stack parent. This eliminates `RenderFlex` overflows for absolutely-positioned designs. Verified end-to-end on the real UI-kit node (`flutter analyze` → 0 issues, app runs on macOS with 0 overflow errors). Note: vector icons (VECTOR/LINE) are still skipped.
16. Add image-fill download (`agent/images.py`): parser records IMAGE fills as `imageRef`/`imageFit` on frame/rectangle/ellipse; CLI fetches fill URLs (`figma_client.fetch_image_fills` → `GET /v1/files/<key>/images`), downloads them to `<flutter_root>/assets/images/<ref>.png`, wires `pubspec.yaml` assets, and attaches `imageAsset` paths to the IR (`images.attach_image_assets`). Codegen renders them as `BoxDecoration(image: DecorationImage(AssetImage(...), fit: ...))` (circular for ellipse avatars). Image download is non-fatal (warns and continues on failure). Verified on the real UI-kit node: avatar PNG downloaded and rendered, `flutter analyze` → 0 issues, app runs with 0 errors.
17. Improve component support: parser now treats COMPONENT/COMPONENT_SET as frames (alongside INSTANCE/GROUP). Planner deduplicates structurally-identical components (`_dedupe`): instances of the same Figma component that differ only by id/position collapse into one reusable widget, with all references rewritten to the canonical name (runs to a fixed point for nested dups). On the real UI-kit node this merged 4 duplicate content-block classes into 1 (22 → 19 components, referenced 4×). `flutter analyze` → 0 issues, app unchanged visually.

## Definition of Done for MVP

The MVP is done when this command works:

python -m agent.cli --input examples/figma_sample.json --output flutter_app/lib/generated_screen.dart

And the generated Flutter app can pass:

flutter analyze
