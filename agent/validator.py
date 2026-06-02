from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ValidationResult:
    success: bool
    raw_log: str


def validate(flutter_app_dir: str | Path) -> ValidationResult:
    """Run `flutter analyze` inside flutter_app_dir.

    success is True only when the process exits with code 0. raw_log
    contains the combined stdout and stderr of the flutter process.
    """
    result = subprocess.run(
        ["flutter", "analyze"],
        cwd=flutter_app_dir,
        capture_output=True,
        text=True,
        check=False,
    )
    return ValidationResult(
        success=result.returncode == 0,
        raw_log=result.stdout + result.stderr,
    )
