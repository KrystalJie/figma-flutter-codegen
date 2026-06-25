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

figma-flutter-codegen/
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

The project was built incrementally, **deterministic-first** (rule-based codegen
before any LLM). The full numbered build log — every step with its rationale,
per-phase test counts, real-node visual/geometry scores, model/token
confirmations, full bug investigations, per-version visual-score movements, and
the features that were *prototyped then removed* — lives in
[docs/CHANGELOG.md](docs/CHANGELOG.md).

The intended build order was: repo structure → Design IR schema → sample Figma
JSON → parser → rule-based codegen → CLI → Flutter shell → `flutter analyze`
validator → planner/Component Plan → repair loop. Everything after that
(real Figma source, node coverage, design tokens, visual/geometry validation,
real LLM provider, fidelity fixes, evaluation, CI, one-command demo) is logged
in the changelog.

## Definition of Done for MVP

The MVP is done when this command works:

python -m agent.cli --input examples/figma_sample.json --output flutter_app/lib/generated_screen.dart

And the generated Flutter app can pass:

flutter analyze
