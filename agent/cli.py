from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from agent import codegen, figma_client, images, ir_parser, planner, repair, validator
from agent.figma_client import FigmaError
from agent.repair import LLMClient, StubLLMClient
from agent.run_logger import RunLogger
from agent.validator import ValidationResult


def _make_llm_client() -> LLMClient:
    """Return the LLM client used by --repair.

    Defaults to a stub that raises NotImplementedError when called. Tests
    monkeypatch this to inject a fake. Replace with a real provider once
    one is chosen.
    """
    return StubLLMClient()


def _load_figma(args: argparse.Namespace) -> tuple[dict, dict | None]:
    """Load the Figma node tree from a local file or the Figma API.

    Returns (document_node, raw_response). raw_response is the full API
    payload when fetched over the network, or None for a local --input file.
    """
    if args.figma_url:
        file_key, node_id = figma_client.parse_figma_url(args.figma_url)
        if not node_id:
            raise FigmaError("the Figma URL must include a node-id=... parameter")
        return figma_client.fetch_node(file_key, node_id, args.figma_token)
    with open(args.input) as f:
        return json.load(f), None


def _maybe_download_images(
    args: argparse.Namespace, ir: dict, warnings: list[str]
) -> None:
    """Download Figma image fills and wire them into the IR + pubspec.

    Only runs for a --figma-url source. Failures are non-fatal: a warning is
    recorded and generation continues without the images.
    """
    if not args.figma_url:
        return
    refs = images.collect_image_refs(ir)
    if not refs:
        return
    file_key, _ = figma_client.parse_figma_url(args.figma_url)
    try:
        asset_map = images.download_image_fills(
            file_key, args.figma_token, refs, args.flutter_root
        )
    except FigmaError as exc:
        warnings.append(f"image download failed: {exc}")
        return
    if asset_map:
        images.attach_image_assets(ir, asset_map)
        images.ensure_pubspec_assets(Path(args.flutter_root) / "pubspec.yaml")
        print(f"Downloaded {len(asset_map)} image(s) to {args.flutter_root}/assets/images/")
    missing = refs - set(asset_map)
    if missing:
        warnings.append(f"{len(missing)} image fill(s) had no downloadable URL")


def _run_validate(flutter_root: str) -> ValidationResult | None:
    try:
        return validator.validate(flutter_root)
    except FileNotFoundError:
        print("error: flutter CLI not found on PATH", file=sys.stderr)
        return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="agent.cli",
        description="Convert a Figma node JSON file into a Flutter screen.",
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--input", help="Path to a local Figma node JSON file")
    source.add_argument(
        "--figma-url",
        help="Figma file/design URL with a node-id (fetched via the Figma API)",
    )
    parser.add_argument(
        "--figma-token",
        help="Figma access token (defaults to the FIGMA_TOKEN env var)",
    )
    parser.add_argument("--output", required=True, help="Path to write generated Dart file")
    parser.add_argument(
        "--llm",
        action="store_true",
        help="Use the LLM planner instead of the deterministic planner (requires a real LLMClient).",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Run `flutter analyze` in the Flutter root after generation",
    )
    parser.add_argument(
        "--flutter-root",
        default="flutter_app",
        help="Flutter project root to run `flutter analyze` in (default: flutter_app)",
    )
    parser.add_argument(
        "--repair",
        action="store_true",
        help="On validation failure, ask the LLM to repair the file and re-validate. Implies --validate.",
    )
    parser.add_argument(
        "--max-repair-attempts",
        type=int,
        default=1,
        help="Maximum repair attempts before giving up (default: 1).",
    )
    parser.add_argument(
        "--save-run",
        action="store_true",
        help="Save artifacts (input, IR, generated code, validation logs, summary) to runs/<date>-<slug>/.",
    )
    parser.add_argument(
        "--runs-dir",
        default="runs",
        help="Base directory for --save-run artifacts (default: runs).",
    )
    args = parser.parse_args(argv)

    if args.repair:
        args.validate = True
        if args.max_repair_attempts < 1:
            print("error: --max-repair-attempts must be >= 1", file=sys.stderr)
            return 1

    client = _make_llm_client()
    raw: dict | None = None
    warnings: list[str] = []
    try:
        figma, raw = _load_figma(args)
        ir = ir_parser.parse(figma, warnings)
        _maybe_download_images(args, ir, warnings)
        plan = planner.plan_with_llm(ir, client) if args.llm else planner.plan(ir)
        dart = codegen.generate(plan)
    except FileNotFoundError as exc:
        print(f"error: input file not found: {exc.filename}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as exc:
        print(
            f"error: invalid JSON in {args.input}: {exc.msg} (line {exc.lineno})",
            file=sys.stderr,
        )
        return 1
    except FigmaError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except NotImplementedError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    for w in warnings:
        print(f"warning: {w}", file=sys.stderr)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(dart)
    plan_path = out_path.parent / "component_plan.generated.json"
    plan_path.write_text(json.dumps(plan, indent=2, ensure_ascii=False))
    print(f"Generated: {out_path}")
    print(f"Plan: {plan_path}")

    # Persist the raw Figma response next to the output for debugging (7.3).
    if raw is not None:
        raw_path = out_path.parent / "figma_raw.json"
        raw_path.write_text(json.dumps(raw, indent=2, ensure_ascii=False))
        print(f"Raw Figma: {raw_path}")

    logger: RunLogger | None = None
    if args.save_run:
        slug = _slug_from_ir(ir)
        logger = RunLogger(args.runs_dir, slug=slug)
        if raw is not None:
            logger.save_raw_figma(raw)
        logger.save_input_figma(figma)
        logger.save_ir(ir)
        logger.save_plan(plan)
        logger.save_generated_before(dart)

    success = False
    repair_attempts = 0
    try:
        if not args.validate:
            success = True
            return 0

        result = _run_validate(args.flutter_root)
        if result is None:
            return 1
        if logger:
            logger.save_validation_before(result.raw_log)
        if result.success:
            print("Validation: passed")
            success = True
            return 0

        if not args.repair:
            print("Validation: failed", file=sys.stderr)
            return 2

        for attempt in range(1, args.max_repair_attempts + 1):
            repair_attempts = attempt
            print(f"Repair attempt {attempt}/{args.max_repair_attempts}...")
            try:
                dart = repair.repair(dart, result, client)
            except NotImplementedError as exc:
                print(f"error: {exc}", file=sys.stderr)
                return 1
            except ValueError as exc:
                print(f"error: repair failed: {exc}", file=sys.stderr)
                return 2
            out_path.write_text(dart)
            print(f"Generated: {out_path}")
            if logger:
                logger.save_generated_after(dart)

            result = _run_validate(args.flutter_root)
            if result is None:
                return 1
            if logger:
                logger.save_validation_after(result.raw_log)
            if result.success:
                print("Validation: passed")
                success = True
                return 0

        print("Validation: failed", file=sys.stderr)
        return 2
    finally:
        if logger:
            logger.write_summary(
                success=success,
                input=str(args.input),
                output=str(out_path),
                validated=args.validate,
                repaired=args.repair,
                repair_attempts=repair_attempts,
            )


def _slug_from_ir(ir: dict) -> str:
    """Derive a kebab-case slug from the IR's screen name."""
    name = ""
    root = ir.get("root") if isinstance(ir, dict) else None
    if isinstance(root, dict):
        name = str(root.get("name") or "")
    return _kebab(name) or "screen"


def _kebab(s: str) -> str:
    out: list[str] = []
    for i, ch in enumerate(s):
        if ch.isalnum():
            if ch.isupper() and i > 0 and (s[i - 1].islower() or s[i - 1].isdigit()):
                out.append("-")
            out.append(ch.lower())
        elif out and out[-1] != "-":
            out.append("-")
    return "".join(out).strip("-")


if __name__ == "__main__":
    raise SystemExit(main())
