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
18. VECTOR heuristic: a VECTOR with a cornerRadius + solid fill is treated as a rounded rectangle (`_parse_vector`), recovering decorative pill/track/card backgrounds (e.g. the segmented control). True icon vectors (no cornerRadius) are still skipped — proper icon support needs the image-render API (deferred). On the real node this restored the segmented-control pills (VECTOR skips 8 → 4), `flutter analyze` → 0 issues.
19. Design tokens (`agent/tokens.py`, route A — deterministic dedup, no semantic names): codegen interns each distinct style literal into a value-derived constant, turning repeated literals into one definition referenced many times. A `Tokens` registry is active during `generate()`; leaf emitters route through it (`_color` → `AppColors.c<hex>`, `_space` → `AppSpacing.s<n>`, text fontSize/fontWeight → `AppTextStyles.s<size>w<weight>` with per-use color via `.copyWith`). Only auto-layout spacing + padding become spacing tokens — widths, positions, radii and font sizes stay literal via `_num`. Recorded tokens render into `abstract final class AppColors/AppSpacing/AppTextStyles` constant blocks prepended to the file (omitted when empty). Identifiers stay lowerCamelCase-safe (lowercase hex, `p` for the decimal point) to satisfy `flutter_lints`. Names are value-derived (not `primary`/`title`) so any Figma file maps cleanly; semantic naming + real `ThemeData`/`TextTheme` slots are deferred to a future route B that reads published Figma Styles/Variables. Visual output is unchanged (same values, just referenced). On the real ProfilePosts node: 8 colors / 4 text styles defined once and reused 2–8× each, `flutter analyze` → 0 issues; 171 Python tests pass.
20. Design tokens (route B — semantic color names from published Figma Styles): when the Figma response carries a top-level Style map, color tokens prefer the designer's published fill-Style name over the value-derived `c<hex>`. `figma_client.extract_styles` pulls the styleId→meta map (sibling of `document` in a `/nodes` response); `ir_parser` walks node `styles` refs (`fill`/`fills`/`stroke`/`strokes`), resolves each FILL Style to its name, and attaches `ir["tokens"]["colors"]` (hex → name, first occurrence wins). The planner carries `tokens` onto the plan; codegen seeds the `Tokens` registry with it, so `_color` emits `AppColors.<camelCasedStyleName>` (`Green/Primary` → `greenPrimary`, `Gray/03` → `gray03`) and falls back to `c<hex>` for colors with no published Style. `_sanitize_ident` keeps names lowerCamelCase-safe (drops names starting with a digit) and collisions get a numeric suffix. CLI `--input` now also accepts a saved full `/nodes` response (e.g. `figma_raw.json`) so its Styles are reused. Spacing/typography stay value-derived; real `ThemeData`/`TextTheme` slot mapping is still deferred. On the real ProfilePosts node: 6 of 8 colors got semantic names (white/black/gray01–03/greenPrimary), 2 un-styled colors kept `c<hex>`, `flutter analyze` → 0 issues; 180 Python tests pass.
21. Visual validation / screenshot diff (`--visual-validate`, core 9.1–9.4; deps: Pillow + numpy). **9.1 Reference PNG:** `figma_client.fetch_node_image_url` renders the node via `GET /v1/images/<key>?ids=&format=png&scale=` (the node-render endpoint, distinct from the image-*fills* one) and downloads it; `--reference-image <path>` supplies one manually instead. **9.2 Flutter screenshot:** `agent/screenshot.py` writes a golden test (`flutter_app/test/visual_golden_test.dart`, pure builder `build_golden_test`) that pumps the screen at the root frame's size and `flutter test --update-goldens` rasterizes it to `test/visual_golden/actual.png` (artifacts gitignored). **9.3 Diff:** `agent/visual.py` resizes the candidate to the reference, then computes pixel MAE, windowed SSIM (numpy integral-image box filter, no scipy), and the raw size ratio → `VisualReport`. **9.4 CLI:** `--visual-validate` prints a 0–100 `visual_score` (0.6·SSIM + 0.4·(1−MAE)) plus the reference-image, Flutter-screenshot and report paths, and writes `visual_report.json` next to the output; non-fatal (warns + continues on any failure). With `--save-run` the report and both PNGs are also copied into the run dir (`visual_report.json`, `visual_reference.png`, `visual_screenshot.png`) via `RunLogger.save_visual_report`/`save_visual_image`. The golden test drains network-image load exceptions (`flutter_test` returns HTTP 400 for `Image.network`) so capture still succeeds with un-loadable images rendered blank. Caveat: `flutter test` renders text with a placeholder font (glyphs show as boxes), so the score is most reliable for layout/spacing/color/alignment and only approximate over text regions. Verified end-to-end: golden capture renders the real ProfilePosts screen faithfully; 193 Python tests pass. **Deferred — 9.5:** repair agent consuming diff feedback (font-size/spacing/alignment deviations).

22. Real LLM provider wired (DeepSeek) + per-stage experiment. **Provider:** `DeepSeekLLMClient` (`agent/llm.py`) calls the OpenAI-compatible `POST {base_url}/chat/completions` with a Bearer token using only the stdlib (same style as `figma_client`) — no new dependency. DeepSeek caches prompt prefixes server-side, so there is no client-side caching to wire. `cli._make_llm_client()` returns the real client when `DEEPSEEK_API_KEY` is set, else the stub (deterministic runs need no key). Config via env: `DEEPSEEK_API_KEY` (required), `DEEPSEEK_MODEL` (default `deepseek-v4-flash`, confirmed against the `/models` endpoint; `deepseek-v4-pro` also available), `DEEPSEEK_BASE_URL` (default `https://api.deepseek.com`). Tests inject a fake transport (no network). **Experiment — effect of LLM at each stage:** (a) **Repair (`--repair`) = primary LLM capability, kept.** End-to-end verified: injected a `Tex(...)` typo → `flutter analyze` error → DeepSeek returned the corrected file (`Text(...)`) → re-analyze clean. This fixes analyze errors the deterministic path can't, and is the recommended LLM use. (b) **Planner (`--llm`) = experimental, do not use for now.** On the simple sample the LLM plan is byte-identical to the deterministic one (the deterministic planner already emits idiomatic `Column/Padding` for clean auto-layout) → zero gain. On the complex ProfilePosts node it is flaky: the plan JSON runs right at the 8192-token ceiling (~7462 completion tokens), so generation intermittently truncates into invalid JSON and hard-fails (`LLM returned invalid JSON`); and even when it succeeds it echoes the IR's absolute `x/y` positions rather than inferring `Row/Column`, so there is no layout-quality gain. Conclusion: with the current minimal prompt + non-streaming + 8192-token cap, the LLM planner adds no value and regresses robustness on large pages. `--llm` help marked `(experimental)`; planner tuning (bigger token budget + streaming + a prompt that infers layout from positions) is **deferred** by decision. Also in this phase: `flutter_app` became a multi-demo gallery (`main.dart` → `DemoGallery` list → push into each screen; demos under `lib/demos/`, prefixed imports to avoid per-file `AppColors`/root-class collisions).

## Definition of Done for MVP

The MVP is done when this command works:

python -m agent.cli --input examples/figma_sample.json --output flutter_app/lib/generated_screen.dart

And the generated Flutter app can pass:

flutter analyze
