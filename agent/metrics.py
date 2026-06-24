"""Aggregate evaluation metrics across saved runs (``runs/`` directory).

Reads the artifacts written by :class:`agent.run_logger.RunLogger` and reports
the project's headline metrics: compile success rate, repair success rate,
visual similarity, generated LOC, and component reuse ratio.

Pure functions + a small ``python -m agent.metrics`` entry point. No network,
no Flutter calls; it only summarizes what previous runs already produced.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text())
    except (ValueError, OSError):
        return None


def _loc(path: Path) -> int | None:
    """Count source lines (ignoring blank lines) in a generated Dart file."""
    if not path.is_file():
        return None
    return sum(1 for line in path.read_text().splitlines() if line.strip())


def collect_component_refs(plan: dict) -> tuple[int, int, int]:
    """Walk a component plan and count component references.

    Returns ``(defined, total_refs, distinct_refs)`` where a reference is a
    ``{"type": "component", "ref": <name>}`` node. ``defined`` is the number of
    component classes the plan declares.
    """
    refs: list[str] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            if node.get("type") == "component" and isinstance(node.get("ref"), str):
                refs.append(node["ref"])
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    components = plan.get("components") or []
    for component in components:
        walk(component.get("root"))
    walk(plan.get("rootComponent"))

    defined = len(components)
    return defined, len(refs), len(set(refs))


@dataclass
class RunMetrics:
    """Per-run signals extracted from a single ``runs/<...>/`` directory."""

    name: str
    validated: bool = False
    repaired: bool = False
    repair_attempts: int = 0
    success: bool = False
    visual_score: float | None = None
    ssim: float | None = None
    pixel_mae: float | None = None
    loc: int | None = None
    components_defined: int | None = None
    component_refs: int | None = None
    distinct_refs: int | None = None

    @property
    def reuse_ratio(self) -> float | None:
        if not self.distinct_refs:
            return None
        return round(self.component_refs / self.distinct_refs, 3)


def load_run(run_dir: Path) -> RunMetrics | None:
    """Build :class:`RunMetrics` from one run directory, or ``None`` if empty."""
    summary = _read_json(run_dir / "summary.json")
    if summary is None:
        return None

    run = RunMetrics(
        name=run_dir.name,
        validated=bool(summary.get("validated")),
        repaired=bool(summary.get("repaired")),
        repair_attempts=int(summary.get("repair_attempts") or 0),
        success=bool(summary.get("success")),
    )

    visual = _read_json(run_dir / "visual_report.json")
    if visual:
        run.visual_score = visual.get("visual_score")
        run.ssim = visual.get("ssim")
        run.pixel_mae = visual.get("pixel_mae")

    after = run_dir / "generated_after.dart"
    before = run_dir / "generated_before.dart"
    run.loc = _loc(after) if after.is_file() else _loc(before)

    plan = _read_json(run_dir / "component_plan.json")
    if plan:
        defined, total, distinct = collect_component_refs(plan)
        run.components_defined = defined
        run.component_refs = total
        run.distinct_refs = distinct

    return run


def _mean(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 3) if values else None


def _rate(passed: int, total: int) -> float | None:
    return round(passed / total, 3) if total else None


@dataclass
class Aggregate:
    """Project-level metrics aggregated over all runs."""

    runs: int = 0
    # compile
    validated_runs: int = 0
    compile_passed: int = 0
    compile_success_rate: float | None = None
    # repair
    repaired_runs: int = 0
    repair_passed: int = 0
    repair_success_rate: float | None = None
    # visual
    visual_runs: int = 0
    mean_visual_score: float | None = None
    mean_ssim: float | None = None
    mean_pixel_mae: float | None = None
    # codegen
    mean_loc: float | None = None
    # reuse
    mean_reuse_ratio: float | None = None
    per_run: list[dict[str, Any]] = field(default_factory=list)


def aggregate(runs: list[RunMetrics]) -> Aggregate:
    agg = Aggregate(runs=len(runs))

    validated = [r for r in runs if r.validated]
    agg.validated_runs = len(validated)
    agg.compile_passed = sum(1 for r in validated if r.success)
    agg.compile_success_rate = _rate(agg.compile_passed, agg.validated_runs)

    repaired = [r for r in runs if r.repaired and r.repair_attempts > 0]
    agg.repaired_runs = len(repaired)
    agg.repair_passed = sum(1 for r in repaired if r.success)
    agg.repair_success_rate = _rate(agg.repair_passed, agg.repaired_runs)

    scores = [r.visual_score for r in runs if r.visual_score is not None]
    agg.visual_runs = len(scores)
    agg.mean_visual_score = _mean(scores)
    agg.mean_ssim = _mean([r.ssim for r in runs if r.ssim is not None])
    agg.mean_pixel_mae = _mean([r.pixel_mae for r in runs if r.pixel_mae is not None])

    agg.mean_loc = _mean([r.loc for r in runs if r.loc is not None])
    agg.mean_reuse_ratio = _mean(
        [r.reuse_ratio for r in runs if r.reuse_ratio is not None]
    )

    agg.per_run = [asdict(r) | {"reuse_ratio": r.reuse_ratio} for r in runs]
    return agg


def load_runs(runs_dir: Path) -> list[RunMetrics]:
    if not runs_dir.is_dir():
        return []
    runs = [load_run(d) for d in sorted(runs_dir.iterdir()) if d.is_dir()]
    return [r for r in runs if r is not None]


def _fmt(value: Any) -> str:
    return "n/a" if value is None else str(value)


def render(agg: Aggregate) -> str:
    """Render a human-readable report block."""
    lines = [
        f"Runs analyzed:           {agg.runs}",
        "",
        "Compile (flutter analyze):",
        f"  validated runs:        {agg.validated_runs}",
        f"  passed:                {agg.compile_passed}",
        f"  success rate:          {_fmt(agg.compile_success_rate)}",
        "",
        "Repair (LLM):",
        f"  runs needing repair:   {agg.repaired_runs}",
        f"  fixed to passing:      {agg.repair_passed}",
        f"  success rate:          {_fmt(agg.repair_success_rate)}",
        "",
        "Visual fidelity:",
        f"  runs with report:      {agg.visual_runs}",
        f"  mean visual_score:     {_fmt(agg.mean_visual_score)}",
        f"  mean SSIM:             {_fmt(agg.mean_ssim)}",
        f"  mean pixel MAE:        {_fmt(agg.mean_pixel_mae)}",
        "",
        "Code generation:",
        f"  mean generated LOC:    {_fmt(agg.mean_loc)}",
        f"  mean reuse ratio:      {_fmt(agg.mean_reuse_ratio)}",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="agent.metrics",
        description="Aggregate evaluation metrics across saved runs.",
    )
    parser.add_argument(
        "--runs-dir", default="runs", help="Directory of saved runs (default: runs)"
    )
    parser.add_argument(
        "--json", action="store_true", help="Emit aggregate metrics as JSON"
    )
    args = parser.parse_args(argv)

    runs = load_runs(Path(args.runs_dir))
    agg = aggregate(runs)

    if not runs:
        print(f"No runs found in {args.runs_dir!r} (run with --save-run first).")
        return 0

    if args.json:
        print(json.dumps(asdict(agg), indent=2, ensure_ascii=False))
    else:
        print(render(agg))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
