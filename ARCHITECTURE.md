# Architecture

This document explains *why* `figma2flutter-agent` is built the way it is. For
usage see [README.md](README.md); for the chronological build log see
[CLAUDE.md](CLAUDE.md).

## Design philosophy

**Deterministic first; the LLM only where rules can't reach.** A Figma node is
structured data, so most of the conversion is a deterministic compiler, not a
prompt. The same input always produces the same output, the whole core is unit
-testable without a network, and the generated Dart is reviewable. The LLM is an
*opt-in* assistant for the two jobs that genuinely need judgment — recovering
layout intent from raw geometry, and fixing analyzer errors — never a black box
the whole pipeline depends on.

This buys three things that matter for a code-generation tool: **reproducibility**
(byte-identical output, snapshot-tested), **trust** (you can read and diff the
result), and **testability** (259 tests, zero network, Flutter mocked).

## Pipeline

```
Figma JSON ─► Design IR ─► Component Plan ─► Flutter code ─► validate ─► repair
   parse        plan          codegen          (analyze /      (close
                                                geometry /       the loop)
                                                visual)
```

Each stage has one job and a clean contract with the next:

| Stage | Module | Input → Output |
| --- | --- | --- |
| Fetch | `figma_client` | Figma URL → node JSON (REST API) |
| Parse | `ir_parser` | Figma JSON → **Design IR** |
| Plan | `planner` | IR → **Component Plan** (lift + dedupe components) |
| Generate | `codegen`, `tokens` | Plan → Dart (+ design tokens) |
| Validate | `validator`, `geometry`, `visual` | Dart → signals (analyze log / rect diff / pixel diff) |
| Repair | `repair`, `geometry_repair`, `layout_infer` | signal → adjusted code |

Supporting modules: `images` (image-fill + icon rasterization), `screenshot`
(golden + rect-dump test generation), `run_logger` (`--save-run` archive),
`metrics` (aggregate evaluation over saved runs), `llm` (provider client).

## The Design IR — the contract

The IR is the seam between "understanding Figma" and "emitting Flutter". Keeping
it small and explicit is what makes both sides independently testable.

- **Nodes:** `screen` (root), `frame`, `text`, `rectangle`, `ellipse`, `image`,
  `icon`; the planner adds `component` references. Anything else in the source
  Figma tree is skipped (with a warning) rather than half-rendered.
- **Layout:** every container has a `direction` — `vertical` / `horizontal`
  (Figma auto-layout → `Column`/`Row` with `spacing`, `padding`, `alignment`,
  `justify`) or `stack` (a frame with *no* auto-layout → `Stack`+`Positioned`,
  children carrying a relative `position`).
- **Per-child sizing:** `layoutAlign: "stretch"` marks a child that fills the
  counter axis, so codegen stretches only those (not hug-content text).
- **Style:** flat hex colors, borders, corner radius, image fills, font family /
  size / weight / line-height.

Schemas: [`schemas/design_ir.schema.json`](schemas/design_ir.schema.json),
[`schemas/component_plan.schema.json`](schemas/component_plan.schema.json).

## Key decisions

**Absolute-positioning fallback.** Real Figma files are full of frames without
auto-layout. Rather than guess a flow (and risk `RenderFlex` overflow), the
parser lowers them to a `Stack` of `Positioned` children — always correct,
never overflows. Recovering idiomatic flow from that is a *separate, optional*
step (see LLM layout inference below).

**Component lifting + dedupe.** The planner promotes each named frame to its own
`StatelessWidget` and collapses structurally-identical instances into one
reusable widget (to a fixed point). One real screen went from 22 → 19 component
classes with a card reused 4×. The result reads like hand-written Flutter, not
one giant `build`.

**Design tokens, value-derived by default.** Repeated style literals are interned
into `AppColors` / `AppSpacing` / `AppTextStyles` constants. Names are
value-derived (`c3366e6`) so *any* file maps cleanly, and upgraded to the
designer's semantic name when the Figma file publishes a Style (`greenPrimary`).

**Geometry over pixels — the load-bearing insight.** The obvious way to score
fidelity is a screenshot SSIM/pixel diff. We built that (`--visual-validate`),
then found it can't *reward* fine-grained fixes: placeholder-font noise swamps
local changes, and a single global scalar isn't attributable to any element. So
the primary fidelity signal is instead a **font-independent, per-node, signed
geometry diff** (`--geometry-validate`): wrap every node in a keyed subtree,
render it, dump each rect, and compare to Figma's `absoluteBoundingBox`. That
yields actionable deltas (`dx/dy/dw/dh` per node) — which is what a repair loop
actually needs. Bundling the real Inter font then collapsed text deltas from
272px → 7px max, making all four axes trustworthy. The pixel score is kept only
as a coarse regression gate.

## Validation & repair: the Repair Agent

Each validation layer emits a *signal*; a **Repair Agent** consumes a signal and
emits adjusted code. Three branches by signal type:

- **Code Repair** — *implemented* (`--repair`). analyze log + Dart → fixed Dart
  via the LLM (whole-file). Live-verified against DeepSeek.
- **Layout Repair** — *partial*. Geometry diff → deterministic position/size
  nudges (`--repair-geometry`, conservative: never distorts intrinsic content).
  Overflow-log consumption and LLM-driven *structural* fixes are future work.
- **Visual Repair** — *planned*. The screenshot/region diff signal exists; the
  consumer is blocked on a vision-capable model (or reducing the diff to text).

Complementary to repair, **LLM layout inference** (`--llm`) is a *generation*-time
helper: it reads a `stack` frame's child rectangles and re-flows them into an
idiomatic `Row`/`Column`. It is per-frame (no token-ceiling truncation),
validated (the returned order must be a permutation of the children), and
non-fatal (an unclear frame stays a `Stack`).

See the [Repair Agent roadmap](README.md#roadmap-repair-agent) for status.

## Testing strategy

- **No network, no Flutter, in the unit suite.** The LLM client is a protocol;
  tests inject a fake. Figma fetches are mocked. 259 tests run in <1s.
- **Snapshot tests** pin the generated Dart byte-for-byte, so any codegen change
  is a visible diff and new features must prove backward compatibility.
- **Geometry diff as a font-independent gate** catches gross layout/color
  regressions that the pixel score can't attribute.
- **CI** runs the suite on Python 3.10–3.12 on every push/PR.

## Known limits & roadmap

Single mobile-portrait viewport, static layout, no interactions. Diagonal/path
vectors are skipped; icon rasterization needs a live source. The biggest open
items are Visual Repair (needs a vision model) and broader real-file validation.
Full detail in [README — Limitations](README.md#limitations) and the
[development log](CLAUDE.md).
