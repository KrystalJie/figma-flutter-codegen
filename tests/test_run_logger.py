from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent import run_logger
from agent.run_logger import RunLogger


def test_creates_dated_slug_subdirectory(tmp_path: Path) -> None:
    logger = RunLogger(tmp_path, slug="profile-screen", today="2026-06-02")
    assert logger.dir == tmp_path / "2026-06-02-profile-screen"
    assert logger.dir.is_dir()
    assert logger.name == "2026-06-02-profile-screen"


def test_appends_numeric_suffix_on_collision(tmp_path: Path) -> None:
    a = RunLogger(tmp_path, slug="x", today="2026-06-02")
    b = RunLogger(tmp_path, slug="x", today="2026-06-02")
    c = RunLogger(tmp_path, slug="x", today="2026-06-02")
    assert a.dir.name == "2026-06-02-x"
    assert b.dir.name == "2026-06-02-x-2"
    assert c.dir.name == "2026-06-02-x-3"


def test_creates_parent_runs_dir_if_missing(tmp_path: Path) -> None:
    base = tmp_path / "nested" / "runs"
    logger = RunLogger(base, slug="s", today="2026-06-02")
    assert logger.dir.is_dir()


def test_save_input_figma_writes_pretty_json(tmp_path: Path) -> None:
    logger = RunLogger(tmp_path, slug="s", today="2026-06-02")
    figma = {"id": "1:1", "name": "ProfileScreen"}
    path = logger.save_input_figma(figma)
    assert path == logger.dir / "input_figma.json"
    assert json.loads(path.read_text()) == figma


def test_save_ir_writes_pretty_json(tmp_path: Path) -> None:
    logger = RunLogger(tmp_path, slug="s", today="2026-06-02")
    ir = {"version": "0.1", "root": {"type": "screen", "name": "X"}}
    path = logger.save_ir(ir)
    assert path == logger.dir / "design_ir.json"
    assert json.loads(path.read_text()) == ir


def test_save_generated_before_and_after(tmp_path: Path) -> None:
    logger = RunLogger(tmp_path, slug="s", today="2026-06-02")
    before = logger.save_generated_before("BEFORE\n")
    after = logger.save_generated_after("AFTER\n")
    assert before.name == "generated_before.dart"
    assert after.name == "generated_after.dart"
    assert before.read_text() == "BEFORE\n"
    assert after.read_text() == "AFTER\n"


def test_save_validation_before_and_after(tmp_path: Path) -> None:
    logger = RunLogger(tmp_path, slug="s", today="2026-06-02")
    a = logger.save_validation_before("bad\n")
    b = logger.save_validation_after("ok\n")
    assert a.name == "validation_before.log"
    assert b.name == "validation_after.log"
    assert a.read_text() == "bad\n"
    assert b.read_text() == "ok\n"


def test_summary_records_success_and_metadata(tmp_path: Path) -> None:
    logger = RunLogger(tmp_path, slug="profile-screen", today="2026-06-02")
    logger.save_input_figma({"id": "1"})
    logger.save_ir({"version": "0.1", "root": {"type": "screen"}})
    logger.save_generated_before("dart\n")
    logger.save_validation_before("ok\n")
    summary_path = logger.write_summary(
        success=True,
        input="examples/figma_sample.json",
        output="out.dart",
        validated=True,
        repaired=False,
        repair_attempts=0,
    )
    assert summary_path == logger.dir / "summary.json"
    data = json.loads(summary_path.read_text())
    assert data["success"] is True
    assert data["date"] == "2026-06-02"
    assert data["slug"] == "profile-screen"
    assert data["input"] == "examples/figma_sample.json"
    assert data["output"] == "out.dart"
    assert data["validated"] is True
    assert data["repaired"] is False
    assert data["repair_attempts"] == 0
    assert data["files"]["input_figma"] == "input_figma.json"
    assert data["files"]["design_ir"] == "design_ir.json"
    assert data["files"]["generated_before"] == "generated_before.dart"
    assert data["files"]["validation_before"] == "validation_before.log"
    assert "generated_after" not in data["files"]


def test_summary_lists_repair_artifacts_when_saved(tmp_path: Path) -> None:
    logger = RunLogger(tmp_path, slug="s", today="2026-06-02")
    logger.save_generated_before("a")
    logger.save_validation_before("bad")
    logger.save_generated_after("b")
    logger.save_validation_after("ok")
    logger.write_summary(success=True, repaired=True, repair_attempts=1)
    data = json.loads((logger.dir / "summary.json").read_text())
    assert data["files"]["generated_after"] == "generated_after.dart"
    assert data["files"]["validation_after"] == "validation_after.log"


def test_default_today_used_when_none(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(run_logger, "_today", lambda: "2026-06-02")
    logger = RunLogger(tmp_path, slug="x")
    assert logger.date == "2026-06-02"
    assert logger.dir.name == "2026-06-02-x"


def test_default_slug_is_screen(tmp_path: Path) -> None:
    logger = RunLogger(tmp_path, today="2026-06-02")
    assert logger.dir.name == "2026-06-02-screen"
