from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any


def _today() -> str:
    """Date slug used for the run subdirectory. Patched in tests."""
    return date.today().isoformat()


class RunLogger:
    """Optional per-run artifact logger.

    Created only when --save-run is passed. Each instance owns one
    `runs/<date>-<slug>/` directory and records artifacts as the pipeline
    progresses. `write_summary` finalizes a `summary.json` describing
    what ran and which files were saved.

    If the target directory already exists (same date + slug), a numeric
    suffix is appended so we never clobber a previous run.
    """

    def __init__(
        self,
        runs_dir: str | Path,
        slug: str = "screen",
        today: str | None = None,
    ) -> None:
        day = today or _today()
        base = f"{day}-{slug}"
        parent = Path(runs_dir)
        candidate = parent / base
        n = 2
        while candidate.exists():
            candidate = parent / f"{base}-{n}"
            n += 1
        candidate.mkdir(parents=True)
        self.dir = candidate
        self.name = candidate.name
        self.slug = slug
        self.date = day
        self._files: dict[str, str] = {}

    def _save_text(self, key: str, filename: str, content: str) -> Path:
        path = self.dir / filename
        path.write_text(content)
        self._files[key] = filename
        return path

    def save_input_figma(self, figma: dict) -> Path:
        path = self.dir / "input_figma.json"
        path.write_text(json.dumps(figma, indent=2, ensure_ascii=False))
        self._files["input_figma"] = "input_figma.json"
        return path

    def save_ir(self, ir: dict) -> Path:
        path = self.dir / "design_ir.json"
        path.write_text(json.dumps(ir, indent=2, ensure_ascii=False))
        self._files["design_ir"] = "design_ir.json"
        return path

    def save_plan(self, plan: dict) -> Path:
        path = self.dir / "component_plan.json"
        path.write_text(json.dumps(plan, indent=2, ensure_ascii=False))
        self._files["component_plan"] = "component_plan.json"
        return path

    def save_generated_before(self, dart: str) -> Path:
        return self._save_text("generated_before", "generated_before.dart", dart)

    def save_validation_before(self, log: str) -> Path:
        return self._save_text("validation_before", "validation_before.log", log)

    def save_generated_after(self, dart: str) -> Path:
        return self._save_text("generated_after", "generated_after.dart", dart)

    def save_validation_after(self, log: str) -> Path:
        return self._save_text("validation_after", "validation_after.log", log)

    def write_summary(self, *, success: bool, **meta: Any) -> Path:
        summary: dict[str, Any] = {
            "success": success,
            "date": self.date,
            "slug": self.slug,
            **meta,
            "files": dict(self._files),
        }
        path = self.dir / "summary.json"
        path.write_text(json.dumps(summary, indent=2, ensure_ascii=False))
        return path
