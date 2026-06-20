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

23. Deterministic fidelity fixes for the real visual-diff gaps (after deciding 9.5's LLM-visual-repair is blocked — DeepSeek v4 is text-only, so it can't consume the reference/screenshot; pivoted to fixing the gaps in the deterministic codegen instead). **① Text wrap:** Figma TEXT with `textAutoResize != WIDTH_AND_HEIGHT` (HEIGHT/NONE/TRUNCATE) is a fixed-width box meant to wrap; `ir_parser` flags it `wrap: True` (width already in `size`) and codegen wraps it in `SizedBox(width: <box width>, child: Text(...))`. Previously such text inside a Stack/Positioned was unbounded and clipped to one line (the ProfilePosts post body showed "…I don't wa"); now it wraps to the correct two lines. **② LINE dividers:** axis-aligned LINE nodes (the "Divider Line" rules between posts) were skipped; `ir_parser._parse_line` now renders a horizontal rule (height ~0) as a `width × strokeWeight` rectangle and a vertical rule (width ~0) as `strokeWeight × height`, coloured by the stroke. On the real node 4 dividers render (gray `#E8E8E8`, 277×1); the 2 diagonal lines keep path geometry we can't reproduce and stay skipped. Both verified: `flutter analyze` → No issues; 205 Python tests pass; real-font render matches the reference's two-line bodies + separators. **Meta-finding:** the global SSIM/MAE `visual_score` cannot *reward* these fixes — with a placeholder test font it even penalizes the (correct) wrap, and with a real font the change is within noise (86.4 vs 87.3), because font-stroke mismatch makes correct text no closer pixel-wise than whitespace. Treat `visual_score` as a coarse regression gate (catches gross layout/color breakage), not a fine-grained reward signal — which also reinforces that a naive score-optimizing repair loop would be misguided. **Still deferred:** true icon vectors (status-bar 9:41/signal/battery, the X chevron) need the per-node Figma image-render API to rasterize each VECTOR to a PNG asset.

24. Icon-vector rendering via the Figma node-render API (lifts the "true icon vectors deferred" caveat from step 23). True icon VECTORs (no cornerRadius) are no longer dropped: `ir_parser` keeps each as an `icon` node carrying the Figma node id + size. `figma_client.fetch_node_images` batch-renders many node ids in one `GET /v1/images/<key>?ids=...&format=png&scale=` call; `images.collect_icon_ids`/`download_icons`/`attach_icon_assets` rasterize them into `assets/images/icon_<id>.png` and wire `iconAsset` onto the IR; `cli._maybe_download_icons` runs only on a live `--figma-url` source (needs file key + token), non-fatal, mirroring the image-fill flow (step 16). `codegen._emit_icon` emits `Image.asset(...)` when an asset exists, else a same-size `SizedBox` placeholder so positions stay correct (so a saved-file `--input` run without a token still lays out correctly). Verified end-to-end on the live ProfilePosts node (file `CjqVljuG65EUroiUFhSwxT`): avatar auto-downloaded + 4 status-bar icons rendered (9:41 / battery / notch); the 6 tiny degenerate signal/wifi bars (width 1–3px) return no render URL and fall back to placeholders. `flutter analyze` → No issues; 212 Python tests pass (network mocked via fake transport / monkeypatched urlopen). Remaining un-reproduced: the 2 diagonal LINE chevrons (path geometry) stay skipped.

25. Geometry validation / layout fidelity diff (`--geometry-validate`; "route B" diagnostic). Motivated by step 23's meta-finding that the pixel `visual_score` cannot reward fine-grained layout fixes (placeholder-font noise swamps local changes, and the global scalar is unattributable). This adds a **font-independent, per-node, attributable** layout check that compares the rendered geometry against Figma's exact `absoluteBoundingBox` ground-truth instead of pixels. **① Target rects:** `agent/geometry.py:collect_target_rects` walks the raw Figma tree → `{node id -> (x,y,w,h)}` normalized to the root's top-left; `collect_names` gives id→name for readable output. **② Node keying:** `codegen.generate(plan, keyed=True)` wraps every id-bearing node in `KeyedSubtree(ValueKey('<figma id>'))` at the `_emit_node` chokepoint (component references stay unkeyed — a deduped instance's id is not unique). Default `keyed=False` keeps the shipped output and all snapshot tests byte-identical. **③ Rect dump:** `agent/screenshot.py:build_rect_dump_test`/`capture_rects` render the keyed screen and dump each `KeyedSubtree`'s global rect (`localToGlobal` + `size`) to `test/visual_rects/rects.json` (`putIfAbsent` → first occurrence wins, so reused components don't create ambiguity). **④ Diff:** `geometry.diff_rects(target, actual, tolerance)` computes signed dx/dy/dw/dh per shared id, flags nodes past the tolerance (tagging which of x/y/w/h drifted), ranks worst-first, and summarizes max/mean offset → `GeometryReport`. **⑤ CLI:** `--geometry-validate` (+ `--geometry-tolerance`, `--geometry-top`) generates a throwaway `<out>_keyed.dart`, captures, diffs, prints per-node deviations, and writes `geometry_report.json` (also via `RunLogger.save_geometry_report` under `--save-run`); non-fatal, mirroring `--visual-validate`. The keyed variant + rect artifacts are gitignored and the temp file is unlinked after. Verified end-to-end on the sample (`flutter` golden run produces real rects; size match is exact where the synthetic sample has a real box, e.g. node `1:6` 100×1; large position deltas there are expected because the hand-authored sample puts child boxes at origin). 225 Python tests pass (+13: geometry diff, codegen keying, rect-dump builder). **Why this over `visual_score`:** geometry deltas are signed, per-element, and font-independent — i.e. exactly the actionable signal a repair loop needs. **Deferred (next step):** feed the deviations into `repair.py` (dw → SizedBox width, dy drift → padding/spacing) to close the loop — kept as a diagnostic first to observe real-node deltas before automating fixes.

## Definition of Done for MVP

The MVP is done when this command works:

python -m agent.cli --input examples/figma_sample.json --output flutter_app/lib/generated_screen.dart

And the generated Flutter app can pass:

flutter analyze
