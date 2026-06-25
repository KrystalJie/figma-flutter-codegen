from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent import cli, run_logger, validator
from agent.llm import DeepSeekLLMClient, StubLLMClient
from agent.repair import LLMClient
from agent.validator import ValidationResult


class FakeLLM:
    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)
        self.calls: list[str] = []

    def complete(self, prompt: str) -> str:
        self.calls.append(prompt)
        if not self._responses:
            raise AssertionError("FakeLLM ran out of canned responses")
        return self._responses.pop(0)


def _stub_results(*results: ValidationResult) -> object:
    """Return a fake validate() that yields the given results in order."""
    queue = list(results)

    def fake_validate(_dir: object) -> ValidationResult:
        if not queue:
            raise AssertionError("validate called more times than expected")
        return queue.pop(0)

    return fake_validate


ROOT = Path(__file__).resolve().parent.parent
SAMPLE = ROOT / "examples" / "figma_sample.json"


# The real formatter, captured before the autouse fixture stubs it out, so the
# formatting tests below can exercise it directly.
_REAL_FORMAT_OUTPUT = cli._format_output


@pytest.fixture(autouse=True)
def _no_dart_format(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stub out the `dart format` pass so CLI tests stay deterministic and
    never shell out. Tests that exercise formatting patch it back."""
    monkeypatch.setattr(cli, "_format_output", lambda _path: None)


def _stack_input(tmp_path: Path) -> Path:
    """Write a Figma file whose inner 'Panel' frame has no auto-layout, so the
    parser lowers it to a Stack — the case --llm layout inference targets."""
    fig = {
        "id": "1:1", "name": "Screen", "type": "FRAME",
        "absoluteBoundingBox": {"x": 0, "y": 0, "width": 300, "height": 400},
        "layoutMode": "VERTICAL",
        "children": [
            {
                "id": "1:2", "name": "Panel", "type": "FRAME",
                "absoluteBoundingBox": {"x": 0, "y": 0, "width": 300, "height": 200},
                "children": [
                    {"id": "1:3", "type": "TEXT", "characters": "A",
                     "absoluteBoundingBox": {"x": 0, "y": 0, "width": 100, "height": 20}},
                    {"id": "1:4", "type": "TEXT", "characters": "B",
                     "absoluteBoundingBox": {"x": 0, "y": 40, "width": 100, "height": 20}},
                ],
            }
        ],
    }
    path = tmp_path / "stack_input.json"
    path.write_text(json.dumps(fig))
    return path


def test_make_llm_client_stub_without_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    assert isinstance(cli._make_llm_client(), StubLLMClient)


def test_make_llm_client_deepseek_with_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    assert isinstance(cli._make_llm_client(), DeepSeekLLMClient)


def test_lib_import_path_handles_subdirectory(tmp_path: Path) -> None:
    root = tmp_path / "flutter_app"
    (root / "lib" / "generated").mkdir(parents=True)
    out = root / "lib" / "generated" / "eval_screen.dart"
    assert cli._lib_import_path(str(root), out) == "generated/eval_screen.dart"
    top = root / "lib" / "screen.dart"
    assert cli._lib_import_path(str(root), top) == "screen.dart"


def test_lib_import_path_falls_back_to_name_outside_lib(tmp_path: Path) -> None:
    root = tmp_path / "flutter_app"
    (root / "lib").mkdir(parents=True)
    outside = tmp_path / "elsewhere" / "screen.dart"
    assert cli._lib_import_path(str(root), outside) == "screen.dart"


def test_writes_dart_file_for_sample(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "generated.dart"
    rc = cli.main(["--input", str(SAMPLE), "--output", str(out)])
    assert rc == 0
    text = out.read_text()
    assert text.startswith("import 'package:flutter/material.dart';")
    assert "class ProfileScreen extends StatelessWidget" in text
    plan_path = out.parent / "component_plan.generated.json"
    assert plan_path.exists()
    plan = json.loads(plan_path.read_text())
    assert plan["rootComponent"] == "ProfileScreen"
    stdout = capsys.readouterr().out
    assert f"Generated: {out}" in stdout
    assert f"Plan: {plan_path}" in stdout


def test_creates_parent_directories(tmp_path: Path) -> None:
    out = tmp_path / "nested" / "lib" / "generated.dart"
    rc = cli.main(["--input", str(SAMPLE), "--output", str(out)])
    assert rc == 0
    assert out.exists()


def test_missing_input_returns_1(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "out.dart"
    rc = cli.main(
        ["--input", str(tmp_path / "nonexistent.json"), "--output", str(out)]
    )
    assert rc == 1
    assert "not found" in capsys.readouterr().err
    assert not out.exists()


def test_invalid_json_returns_1(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{not valid json")
    out = tmp_path / "out.dart"
    rc = cli.main(["--input", str(bad), "--output", str(out)])
    assert rc == 1
    assert "invalid JSON" in capsys.readouterr().err
    assert not out.exists()


def test_parser_error_returns_1(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    bad = tmp_path / "input.json"
    bad.write_text(json.dumps({"id": "1", "type": "TEXT", "characters": "x"}))
    out = tmp_path / "out.dart"
    rc = cli.main(["--input", str(bad), "--output", str(out)])
    assert rc == 1
    err = capsys.readouterr().err
    assert err.startswith("error:")
    assert "FRAME" in err
    assert not out.exists()


def test_missing_required_args_exits_2() -> None:
    with pytest.raises(SystemExit) as exc_info:
        cli.main(["--input", "x.json"])
    assert exc_info.value.code == 2


def test_figma_url_fetches_and_saves_raw(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    figma = json.loads(SAMPLE.read_text())
    raw = {"nodes": {"1:1": {"document": figma}}}

    def fake_fetch(file_key: str, node_id: str, token: object) -> tuple[dict, dict]:
        assert (file_key, node_id) == ("KEY", "1:1")
        return figma, raw

    monkeypatch.setattr(cli.figma_client, "fetch_node", fake_fetch)
    out = tmp_path / "generated.dart"
    rc = cli.main(
        [
            "--figma-url",
            "https://www.figma.com/design/KEY/App?node-id=1-1",
            "--figma-token",
            "tok",
            "--output",
            str(out),
        ]
    )
    assert rc == 0
    assert "class ProfileScreen" in out.read_text()
    raw_path = out.parent / "figma_raw.json"
    assert json.loads(raw_path.read_text()) == raw
    assert f"Raw Figma: {raw_path}" in capsys.readouterr().out


def test_figma_url_without_node_id_returns_1(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "out.dart"
    rc = cli.main(
        ["--figma-url", "https://figma.com/file/KEY/App", "--output", str(out)]
    )
    assert rc == 1
    assert "node-id" in capsys.readouterr().err
    assert not out.exists()


def test_input_and_figma_url_mutually_exclusive() -> None:
    with pytest.raises(SystemExit) as exc_info:
        cli.main(["--input", "x.json", "--figma-url", "y", "--output", "o.dart"])
    assert exc_info.value.code == 2


def test_cli_smoke(tmp_path: Path) -> None:
    output = tmp_path / "generated.dart"
    rc = cli.main(["--input", str(SAMPLE), "--output", str(output)])
    assert rc == 0
    assert output.exists()
    text = output.read_text()
    assert "class ProfileScreen" in text
    assert "Widget build" in text


def test_validate_flag_runs_validator_with_default_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    calls: list[object] = []

    def fake_validate(d: object) -> ValidationResult:
        calls.append(d)
        return ValidationResult(success=True, raw_log="No issues found!\n")

    monkeypatch.setattr(validator, "validate", fake_validate)

    out = tmp_path / "x.dart"
    rc = cli.main(["--input", str(SAMPLE), "--output", str(out), "--validate"])
    assert rc == 0
    assert calls == ["flutter_app"]
    out_text = capsys.readouterr().out
    assert "Validation: passed" in out_text
    # Quiet on success: no raw analyzer log on stdout.
    assert "No issues found!" not in out_text


def test_validate_flag_honors_custom_flutter_root(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls: list[object] = []
    monkeypatch.setattr(
        validator,
        "validate",
        lambda d: calls.append(d) or ValidationResult(success=True, raw_log=""),
    )

    out = tmp_path / "x.dart"
    custom = tmp_path / "my_app"
    rc = cli.main(
        [
            "--input",
            str(SAMPLE),
            "--output",
            str(out),
            "--validate",
            "--flutter-root",
            str(custom),
        ]
    )
    assert rc == 0
    assert calls == [str(custom)]


def test_validate_failure_returns_2(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        validator,
        "validate",
        lambda d: ValidationResult(
            success=False, raw_log="error: line 1: bad token\n"
        ),
    )
    out = tmp_path / "x.dart"
    rc = cli.main(["--input", str(SAMPLE), "--output", str(out), "--validate"])
    assert rc == 2
    captured = capsys.readouterr()
    assert "Validation: failed" in captured.err
    # No raw analyzer log on stdout — terse mode.
    assert "bad token" not in captured.out


def test_no_validate_flag_skips_validator(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    called: list[object] = []
    monkeypatch.setattr(
        validator,
        "validate",
        lambda d: called.append(d) or ValidationResult(success=True, raw_log=""),
    )
    out = tmp_path / "x.dart"
    rc = cli.main(["--input", str(SAMPLE), "--output", str(out)])
    assert rc == 0
    assert called == []


def test_repair_implies_validate_and_skips_repair_when_clean(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        validator,
        "validate",
        _stub_results(ValidationResult(success=True, raw_log="No issues found!\n")),
    )
    client = FakeLLM(responses=[])
    monkeypatch.setattr(cli, "_make_llm_client", lambda: client)

    out = tmp_path / "x.dart"
    rc = cli.main(["--input", str(SAMPLE), "--output", str(out), "--repair"])
    assert rc == 0
    assert client.calls == []


def test_repair_fixes_and_revalidates(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        validator,
        "validate",
        _stub_results(
            ValidationResult(success=False, raw_log="error: missing ';'\n"),
            ValidationResult(success=True, raw_log="No issues found!\n"),
        ),
    )
    fixed = "import 'package:flutter/material.dart';\n\nclass Fixed {}\n"
    client = FakeLLM(responses=[fixed])
    monkeypatch.setattr(cli, "_make_llm_client", lambda: client)

    out = tmp_path / "x.dart"
    rc = cli.main(["--input", str(SAMPLE), "--output", str(out), "--repair"])
    assert rc == 0
    assert out.read_text() == fixed
    assert len(client.calls) == 1
    assert "missing ';'" in client.calls[0]
    captured = capsys.readouterr().out
    assert "Repair attempt 1/1" in captured
    assert "Validation: passed" in captured


def test_repair_exhausts_attempts_and_returns_2(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        validator,
        "validate",
        _stub_results(
            ValidationResult(success=False, raw_log="error A\n"),
            ValidationResult(success=False, raw_log="error B\n"),
            ValidationResult(success=False, raw_log="error C\n"),
        ),
    )
    client = FakeLLM(
        responses=[
            "import 'package:flutter/material.dart';\nclass A {}\n",
            "import 'package:flutter/material.dart';\nclass B {}\n",
        ]
    )
    monkeypatch.setattr(cli, "_make_llm_client", lambda: client)

    out = tmp_path / "x.dart"
    rc = cli.main(
        [
            "--input",
            str(SAMPLE),
            "--output",
            str(out),
            "--repair",
            "--max-repair-attempts",
            "2",
        ]
    )
    assert rc == 2
    assert len(client.calls) == 2
    err = capsys.readouterr().err
    assert "Validation: failed" in err


def test_repair_succeeds_on_second_attempt(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        validator,
        "validate",
        _stub_results(
            ValidationResult(success=False, raw_log="bad 1\n"),
            ValidationResult(success=False, raw_log="bad 2\n"),
            ValidationResult(success=True, raw_log="No issues found!\n"),
        ),
    )
    final = "import 'package:flutter/material.dart';\nclass Good {}\n"
    client = FakeLLM(
        responses=[
            "import 'package:flutter/material.dart';\nclass Bad {}\n",
            final,
        ]
    )
    monkeypatch.setattr(cli, "_make_llm_client", lambda: client)

    out = tmp_path / "x.dart"
    rc = cli.main(
        [
            "--input",
            str(SAMPLE),
            "--output",
            str(out),
            "--repair",
            "--max-repair-attempts",
            "3",
        ]
    )
    assert rc == 0
    assert out.read_text() == final
    assert len(client.calls) == 2


def test_repair_default_client_errors_clearly(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        validator,
        "validate",
        _stub_results(ValidationResult(success=False, raw_log="bad\n")),
    )

    out = tmp_path / "x.dart"
    rc = cli.main(["--input", str(SAMPLE), "--output", str(out), "--repair"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "no LLM client" in err


def test_repair_max_attempts_must_be_positive(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "x.dart"
    rc = cli.main(
        [
            "--input",
            str(SAMPLE),
            "--output",
            str(out),
            "--repair",
            "--max-repair-attempts",
            "0",
        ]
    )
    assert rc == 1
    assert "--max-repair-attempts" in capsys.readouterr().err


def test_save_run_writes_input_ir_and_generated_before(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(run_logger, "_today", lambda: "2026-06-02")
    runs_dir = tmp_path / "runs"
    out = tmp_path / "x.dart"
    rc = cli.main(
        [
            "--input",
            str(SAMPLE),
            "--output",
            str(out),
            "--save-run",
            "--runs-dir",
            str(runs_dir),
        ]
    )
    assert rc == 0
    run_dir = runs_dir / "2026-06-02-profile-screen"
    assert run_dir.is_dir()

    figma = json.loads((run_dir / "input_figma.json").read_text())
    assert figma["name"] == "ProfileScreen"

    ir = json.loads((run_dir / "design_ir.json").read_text())
    assert ir["version"] == "0.1"

    dart = (run_dir / "generated_before.dart").read_text()
    assert dart.startswith("import 'package:flutter/material.dart';")

    summary = json.loads((run_dir / "summary.json").read_text())
    assert summary["success"] is True
    assert summary["validated"] is False
    assert summary["repaired"] is False
    assert summary["slug"] == "profile-screen"
    assert summary["date"] == "2026-06-02"
    assert summary["files"]["input_figma"] == "input_figma.json"
    assert summary["files"]["design_ir"] == "design_ir.json"
    assert summary["files"]["generated_before"] == "generated_before.dart"
    assert "validation_before" not in summary["files"]
    assert "generated_after" not in summary["files"]
    assert not (run_dir / "validation_before.log").exists()
    assert not (run_dir / "generated_after.dart").exists()


def test_save_run_writes_validation_before_when_validate(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(run_logger, "_today", lambda: "2026-06-02")
    monkeypatch.setattr(
        validator,
        "validate",
        _stub_results(ValidationResult(success=True, raw_log="No issues found!\n")),
    )
    runs_dir = tmp_path / "runs"
    out = tmp_path / "x.dart"
    rc = cli.main(
        [
            "--input",
            str(SAMPLE),
            "--output",
            str(out),
            "--validate",
            "--save-run",
            "--runs-dir",
            str(runs_dir),
        ]
    )
    assert rc == 0
    run_dir = runs_dir / "2026-06-02-profile-screen"
    assert (run_dir / "validation_before.log").read_text() == "No issues found!\n"
    summary = json.loads((run_dir / "summary.json").read_text())
    assert summary["success"] is True
    assert summary["validated"] is True
    assert summary["files"]["validation_before"] == "validation_before.log"


def test_save_run_writes_after_artifacts_when_repair(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(run_logger, "_today", lambda: "2026-06-02")
    monkeypatch.setattr(
        validator,
        "validate",
        _stub_results(
            ValidationResult(success=False, raw_log="error: bad\n"),
            ValidationResult(success=True, raw_log="No issues found!\n"),
        ),
    )
    fixed = "import 'package:flutter/material.dart';\n\nclass Fixed {}\n"
    client = FakeLLM(responses=[fixed])
    monkeypatch.setattr(cli, "_make_llm_client", lambda: client)

    runs_dir = tmp_path / "runs"
    out = tmp_path / "x.dart"
    rc = cli.main(
        [
            "--input",
            str(SAMPLE),
            "--output",
            str(out),
            "--repair",
            "--save-run",
            "--runs-dir",
            str(runs_dir),
        ]
    )
    assert rc == 0
    run_dir = runs_dir / "2026-06-02-profile-screen"
    assert (run_dir / "input_figma.json").exists()
    assert (run_dir / "design_ir.json").exists()
    assert (run_dir / "generated_before.dart").exists()
    assert (run_dir / "validation_before.log").read_text() == "error: bad\n"
    assert (run_dir / "generated_after.dart").read_text() == fixed
    assert (run_dir / "validation_after.log").read_text() == "No issues found!\n"
    summary = json.loads((run_dir / "summary.json").read_text())
    assert summary["success"] is True
    assert summary["repaired"] is True
    assert summary["repair_attempts"] == 1
    assert summary["files"]["generated_after"] == "generated_after.dart"
    assert summary["files"]["validation_after"] == "validation_after.log"


def test_save_run_repair_produces_exact_spec_layout(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """When --validate --repair --save-run trigger the repair branch, the run
    directory must contain exactly the 7 files documented in the spec."""
    monkeypatch.setattr(run_logger, "_today", lambda: "2026-06-02")
    monkeypatch.setattr(
        validator,
        "validate",
        _stub_results(
            ValidationResult(success=False, raw_log="error: missing ';'\n"),
            ValidationResult(success=True, raw_log="No issues found!\n"),
        ),
    )
    fixed = "import 'package:flutter/material.dart';\n\nclass Fixed {}\n"
    client = FakeLLM(responses=[fixed])
    monkeypatch.setattr(cli, "_make_llm_client", lambda: client)

    runs_dir = tmp_path / "runs"
    out = tmp_path / "x.dart"
    rc = cli.main(
        [
            "--input",
            str(SAMPLE),
            "--output",
            str(out),
            "--validate",
            "--repair",
            "--save-run",
            "--runs-dir",
            str(runs_dir),
        ]
    )
    assert rc == 0

    run_dir = runs_dir / "2026-06-02-profile-screen"
    expected = {
        "input_figma.json",
        "design_ir.json",
        "component_plan.json",
        "generated_before.dart",
        "validation_before.log",
        "generated_after.dart",
        "validation_after.log",
        "summary.json",
    }
    actual = {p.name for p in run_dir.iterdir()}
    assert actual == expected, (
        f"run dir contents differ from spec.\n"
        f"  missing: {expected - actual}\n"
        f"  extra:   {actual - expected}"
    )

    summary = json.loads((run_dir / "summary.json").read_text())
    assert summary["success"] is True
    assert summary["validated"] is True
    assert summary["repaired"] is True
    assert summary["repair_attempts"] == 1
    assert set(summary["files"].values()) == expected - {"summary.json"}
    for fname in summary["files"].values():
        assert (run_dir / fname).is_file()


def test_save_run_summary_records_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(run_logger, "_today", lambda: "2026-06-02")
    monkeypatch.setattr(
        validator,
        "validate",
        _stub_results(ValidationResult(success=False, raw_log="error\n")),
    )
    runs_dir = tmp_path / "runs"
    out = tmp_path / "x.dart"
    rc = cli.main(
        [
            "--input",
            str(SAMPLE),
            "--output",
            str(out),
            "--validate",
            "--save-run",
            "--runs-dir",
            str(runs_dir),
        ]
    )
    assert rc == 2
    summary = json.loads(
        (runs_dir / "2026-06-02-profile-screen" / "summary.json").read_text()
    )
    assert summary["success"] is False
    assert summary["validated"] is True
    assert summary["repaired"] is False


def test_save_run_collision_appends_suffix(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(run_logger, "_today", lambda: "2026-06-02")
    runs_dir = tmp_path / "runs"
    out = tmp_path / "x.dart"
    rc1 = cli.main(
        ["--input", str(SAMPLE), "--output", str(out), "--save-run", "--runs-dir", str(runs_dir)]
    )
    rc2 = cli.main(
        ["--input", str(SAMPLE), "--output", str(out), "--save-run", "--runs-dir", str(runs_dir)]
    )
    assert rc1 == 0 and rc2 == 0
    assert (runs_dir / "2026-06-02-profile-screen").is_dir()
    assert (runs_dir / "2026-06-02-profile-screen-2").is_dir()


def test_save_run_disabled_by_default(tmp_path: Path) -> None:
    runs_dir = tmp_path / "runs"
    out = tmp_path / "x.dart"
    rc = cli.main(["--input", str(SAMPLE), "--output", str(out), "--runs-dir", str(runs_dir)])
    assert rc == 0
    assert not runs_dir.exists()


def test_llm_flag_without_key_is_non_fatal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # With no API key, layout inference is skipped per-frame and generation
    # continues: the Panel stays a Stack rather than failing the run.
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    out = tmp_path / "x.dart"
    rc = cli.main(["--input", str(_stack_input(tmp_path)), "--output", str(out), "--llm"])
    assert rc == 0
    assert "Positioned(" in out.read_text()


def test_llm_flag_infers_flow_layout(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    resp = json.dumps({"direction": "vertical", "order": ["1:3", "1:4"], "spacing": 20})
    client = FakeLLM(responses=[resp])
    monkeypatch.setattr(cli, "_make_llm_client", lambda: client)

    out = tmp_path / "x.dart"
    rc = cli.main(["--input", str(_stack_input(tmp_path)), "--output", str(out), "--llm"])
    assert rc == 0
    assert len(client.calls) == 1  # one request for the one stack frame
    dart = out.read_text()
    assert "Column(" in dart
    assert "Positioned(" not in dart


def test_make_llm_client_returns_stub_by_default() -> None:
    from agent.repair import StubLLMClient

    client: LLMClient = cli._make_llm_client()
    assert isinstance(client, StubLLMClient)
    with pytest.raises(NotImplementedError, match="no LLM client"):
        client.complete("anything")


def test_validate_flutter_not_installed_returns_1(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def raise_not_found(_d: object) -> ValidationResult:
        raise FileNotFoundError(2, "No such file or directory", "flutter")

    monkeypatch.setattr(validator, "validate", raise_not_found)
    out = tmp_path / "x.dart"
    rc = cli.main(["--input", str(SAMPLE), "--output", str(out), "--validate"])
    assert rc == 1
    assert "flutter CLI not found on PATH" in capsys.readouterr().err


def test_visual_validate_writes_report(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import numpy as np
    from PIL import Image

    arr = np.random.default_rng(0).integers(0, 256, (40, 40, 3)).astype("uint8")
    ref = tmp_path / "ref.png"
    shot = tmp_path / "shot.png"
    Image.fromarray(arr).save(ref)
    Image.fromarray(arr).save(shot)
    monkeypatch.setattr(cli.screenshot, "capture", lambda *a, **k: shot)

    out = tmp_path / "lib" / "generated.dart"
    rc = cli.main(
        [
            "--input", str(SAMPLE),
            "--output", str(out),
            "--reference-image", str(ref),
            "--visual-validate",
        ]
    )
    assert rc == 0
    report = out.parent / "visual_report.json"
    assert report.exists()
    data = json.loads(report.read_text())
    assert data["visual_score"] == 100.0
    out_text = capsys.readouterr().out
    assert "Visual score: 100.0/100" in out_text
    assert f"Reference image: {ref}" in out_text
    assert f"Flutter screenshot: {shot}" in out_text


def test_visual_validate_save_run_copies_artifacts(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import numpy as np
    from PIL import Image

    arr = np.random.default_rng(1).integers(0, 256, (24, 24, 3)).astype("uint8")
    ref = tmp_path / "ref.png"
    shot = tmp_path / "shot.png"
    Image.fromarray(arr).save(ref)
    Image.fromarray(arr).save(shot)
    monkeypatch.setattr(cli.screenshot, "capture", lambda *a, **k: shot)

    out = tmp_path / "lib" / "generated.dart"
    runs = tmp_path / "runs"
    rc = cli.main(
        [
            "--input", str(SAMPLE),
            "--output", str(out),
            "--reference-image", str(ref),
            "--visual-validate",
            "--save-run", "--runs-dir", str(runs),
        ]
    )
    assert rc == 0
    run_dir = next(runs.iterdir())
    assert (run_dir / "visual_report.json").exists()
    assert (run_dir / "visual_reference.png").exists()
    assert (run_dir / "visual_screenshot.png").exists()
    summary = json.loads((run_dir / "summary.json").read_text())
    assert summary["files"]["visual_report"] == "visual_report.json"
    assert summary["files"]["visual_screenshot"] == "visual_screenshot.png"


def test_visual_validate_skips_without_reference(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "out.dart"
    rc = cli.main(
        ["--input", str(SAMPLE), "--output", str(out), "--visual-validate"]
    )
    assert rc == 0
    assert "needs --reference-image or --figma-url" in capsys.readouterr().err


def test_generated_output_is_formatted(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The generation path runs the file through dart format so output is
    readable regardless of source (closes the 'one long line' gap)."""
    calls: list[Path] = []
    monkeypatch.setattr(validator, "format_file", lambda p: calls.append(p) or True)
    monkeypatch.setattr(cli, "_format_output", _REAL_FORMAT_OUTPUT)

    out = tmp_path / "out.dart"
    rc = cli.main(["--input", str(SAMPLE), "--output", str(out)])
    assert rc == 0
    assert calls == [out]


def test_format_output_non_fatal_without_dart(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A missing `dart` CLI must warn and continue, never crash."""
    def _raise(_path: object) -> bool:
        raise FileNotFoundError("dart")

    monkeypatch.setattr(validator, "format_file", _raise)
    _REAL_FORMAT_OUTPUT(Path("out.dart"))  # does not raise
    assert "dart CLI not found" in capsys.readouterr().err


def test_format_output_warns_on_format_error(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(validator, "format_file", lambda _p: False)
    _REAL_FORMAT_OUTPUT(Path("out.dart"))
    assert "dart format reported an error" in capsys.readouterr().err
