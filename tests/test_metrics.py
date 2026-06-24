"""Tests for agent.metrics — run-artifact aggregation."""

from __future__ import annotations

import json
from pathlib import Path

from agent import metrics


def _write_run(
    runs_dir: Path,
    name: str,
    summary: dict,
    *,
    visual: dict | None = None,
    plan: dict | None = None,
    generated_before: str | None = None,
    generated_after: str | None = None,
) -> Path:
    run_dir = runs_dir / name
    run_dir.mkdir(parents=True)
    (run_dir / "summary.json").write_text(json.dumps(summary))
    if visual is not None:
        (run_dir / "visual_report.json").write_text(json.dumps(visual))
    if plan is not None:
        (run_dir / "component_plan.json").write_text(json.dumps(plan))
    if generated_before is not None:
        (run_dir / "generated_before.dart").write_text(generated_before)
    if generated_after is not None:
        (run_dir / "generated_after.dart").write_text(generated_after)
    return run_dir


def test_collect_component_refs_counts_and_dedupes():
    plan = {
        "rootComponent": {
            "type": "frame",
            "children": [
                {"type": "component", "ref": "Card"},
                {"type": "component", "ref": "Card"},
                {"type": "component", "ref": "NavBar"},
            ],
        },
        "components": [
            {"name": "Card", "root": {"type": "frame"}},
            {"name": "NavBar", "root": {"type": "frame"}},
        ],
    }
    defined, total, distinct = metrics.collect_component_refs(plan)
    assert defined == 2
    assert total == 3
    assert distinct == 2


def test_reuse_ratio_none_without_refs():
    run = metrics.RunMetrics(name="x")
    assert run.reuse_ratio is None


def test_load_run_pulls_all_signals(tmp_path):
    runs_dir = tmp_path / "runs"
    _write_run(
        runs_dir,
        "r1",
        {"validated": True, "repaired": True, "repair_attempts": 1, "success": True},
        visual={"visual_score": 80.0, "ssim": 0.8, "pixel_mae": 0.1},
        plan={
            "components": [{"name": "Card", "root": {"type": "frame"}}],
            "rootComponent": {
                "children": [
                    {"type": "component", "ref": "Card"},
                    {"type": "component", "ref": "Card"},
                ]
            },
        },
        generated_before="line1\n\nline2\n",
    )
    run = metrics.load_run(runs_dir / "r1")
    assert run is not None
    assert run.validated and run.repaired and run.success
    assert run.visual_score == 80.0
    assert run.loc == 2  # blank line ignored
    assert run.component_refs == 2 and run.distinct_refs == 1
    assert run.reuse_ratio == 2.0


def test_load_run_prefers_generated_after(tmp_path):
    runs_dir = tmp_path / "runs"
    _write_run(
        runs_dir,
        "r1",
        {"success": True},
        generated_before="a\nb\n",
        generated_after="a\nb\nc\n",
    )
    run = metrics.load_run(runs_dir / "r1")
    assert run is not None and run.loc == 3


def test_load_run_none_without_summary(tmp_path):
    (tmp_path / "empty").mkdir()
    assert metrics.load_run(tmp_path / "empty") is None


def test_aggregate_rates():
    runs = [
        metrics.RunMetrics(name="a", validated=True, success=True),
        metrics.RunMetrics(name="b", validated=True, success=False),
        metrics.RunMetrics(
            name="c", validated=True, repaired=True, repair_attempts=1, success=True
        ),
        metrics.RunMetrics(name="d"),  # not validated
    ]
    agg = metrics.aggregate(runs)
    assert agg.runs == 4
    assert agg.validated_runs == 3
    assert agg.compile_passed == 2
    assert agg.compile_success_rate == round(2 / 3, 3)
    assert agg.repaired_runs == 1
    assert agg.repair_passed == 1
    assert agg.repair_success_rate == 1.0


def test_aggregate_visual_and_loc_means():
    runs = [
        metrics.RunMetrics(name="a", visual_score=80.0, ssim=0.8, loc=100),
        metrics.RunMetrics(name="b", visual_score=90.0, ssim=0.9, loc=200),
        metrics.RunMetrics(name="c"),  # no visual / loc
    ]
    agg = metrics.aggregate(runs)
    assert agg.visual_runs == 2
    assert agg.mean_visual_score == 85.0
    assert agg.mean_ssim == 0.85
    assert agg.mean_loc == 150.0


def test_aggregate_empty():
    agg = metrics.aggregate([])
    assert agg.runs == 0
    assert agg.compile_success_rate is None
    assert agg.mean_visual_score is None


def test_load_runs_skips_non_run_dirs(tmp_path):
    runs_dir = tmp_path / "runs"
    _write_run(runs_dir, "good", {"success": True})
    (runs_dir / "stray").mkdir()  # no summary.json
    (runs_dir / "note.txt").write_text("ignore me")
    runs = metrics.load_runs(runs_dir)
    assert [r.name for r in runs] == ["good"]


def test_load_runs_missing_dir(tmp_path):
    assert metrics.load_runs(tmp_path / "nope") == []


def test_main_renders(tmp_path, capsys):
    runs_dir = tmp_path / "runs"
    _write_run(
        runs_dir, "r1", {"validated": True, "success": True}, visual={"visual_score": 88.0}
    )
    code = metrics.main(["--runs-dir", str(runs_dir)])
    assert code == 0
    out = capsys.readouterr().out
    assert "Runs analyzed:           1" in out
    assert "88.0" in out


def test_main_json(tmp_path, capsys):
    runs_dir = tmp_path / "runs"
    _write_run(runs_dir, "r1", {"validated": True, "success": True})
    code = metrics.main(["--runs-dir", str(runs_dir), "--json"])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["runs"] == 1
    assert payload["compile_success_rate"] == 1.0


def test_main_no_runs(tmp_path, capsys):
    code = metrics.main(["--runs-dir", str(tmp_path / "empty")])
    assert code == 0
    assert "No runs found" in capsys.readouterr().out
