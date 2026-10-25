"""Narrilume CLI: native local-model inference by default; ComfyUI is optional legacy."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from .comfy import ComfyClient
from .native_config import load_native_config, validate_native_project
from .native_production import native_plan, render_native
from .production import assemble, render as comfy_render
from .schema import load_project, resolve_reference
from .workflow import load_bindings, load_workflow, validate_bindings


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="narrilume", description="Native AI animation studio CLI")
    commands = parser.add_subparsers(dest="command", required=True)

    check = commands.add_parser("validate", help="validate local model config and shot contract")
    check.add_argument("project")
    check.add_argument("--model", required=True)

    plan = commands.add_parser("plan", help="inspect shot plan without GPU/model download")
    plan.add_argument("project")
    plan.add_argument("--model", required=True)

    generate = commands.add_parser("render", help="generate sequential clips using local Wan weights")
    generate.add_argument("project")
    generate.add_argument("--model", required=True)
    generate.add_argument("--output", required=True)
    generate.add_argument("--retry-failed", action="store_true")
    generate.add_argument("--continue-on-error", action="store_true")

    join = commands.add_parser("assemble", help="assemble completed shot clips into an MP4")
    join.add_argument("project")
    join.add_argument("--output", required=True)

    status = commands.add_parser("status", help="read persistent rendering state")
    status.add_argument("--output", required=True)

    # Existing ComfyUI features remain available but are never required by native commands.
    legacy_validate = commands.add_parser("comfy-validate", help="legacy ComfyUI API graph validation")
    legacy_validate.add_argument("project")
    legacy_validate.add_argument("--workflow", required=True)
    legacy_validate.add_argument("--bindings", required=True)

    legacy_health = commands.add_parser("comfy-health", help="legacy ComfyUI HTTP status")
    legacy_health.add_argument(
        "--comfy-url", default=os.getenv("NARRILUME_COMFY_URL", "http://127.0.0.1:8188")
    )

    legacy_render = commands.add_parser("comfy-render", help="legacy ComfyUI execution")
    legacy_render.add_argument("project")
    legacy_render.add_argument("--workflow", required=True)
    legacy_render.add_argument("--bindings", required=True)
    legacy_render.add_argument("--output", required=True)
    legacy_render.add_argument(
        "--comfy-url", default=os.getenv("NARRILUME_COMFY_URL", "http://127.0.0.1:8188")
    )
    legacy_render.add_argument(
        "--timeout", type=float, default=float(os.getenv("NARRILUME_TIMEOUT_SECONDS", "3600"))
    )
    legacy_render.add_argument(
        "--poll-interval", type=float, default=float(os.getenv("NARRILUME_POLL_INTERVAL", "3"))
    )
    legacy_render.add_argument("--continue-on-error", action="store_true")
    legacy_render.add_argument("--retry-failed", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "validate":
            project = load_project(args.project)
            model = load_native_config(args.model)
            validate_native_project(project, model)
            print(f"Valid: {project.id}; {len(project.shots)} shots; {model.backend}")
        elif args.command == "plan":
            print(json.dumps(native_plan(args.project, args.model), ensure_ascii=False, indent=2))
        elif args.command == "render":
            state = render_native(
                args.project, args.model, args.output,
                retry_failed=args.retry_failed, continue_on_error=args.continue_on_error,
            )
            counts = {
                name: sum(s.get("status") == name for s in state["shots"].values())
                for name in ("completed", "failed", "running")
            }
            print(json.dumps(counts, ensure_ascii=False, indent=2))
            if counts["failed"]:
                return 1
        elif args.command == "assemble":
            print(assemble(args.project, args.output))
        elif args.command == "status":
            print((Path(args.output) / "state.json").read_text(encoding="utf-8"))
        elif args.command == "comfy-validate":
            project = load_project(args.project)
            workflow = load_workflow(args.workflow)
            bindings = load_bindings(args.bindings)
            validate_bindings(workflow, bindings)
            for shot in project.shots:
                resolve_reference(project, shot)
                if shot.reference_image and "reference_image" not in bindings:
                    raise ValueError(f"{shot.id}: missing reference_image binding")
            print(f"Valid ComfyUI graph: {project.id}; {len(project.shots)} shots")
        elif args.command == "comfy-health":
            print(json.dumps(ComfyClient(args.comfy_url).health(), ensure_ascii=False, indent=2))
        elif args.command == "comfy-render":
            if args.timeout <= 0 or args.poll_interval <= 0:
                raise ValueError("timeout and poll_interval must be positive")
            state = comfy_render(
                args.project, args.workflow, args.bindings, args.output,
                args.comfy_url, args.timeout, args.poll_interval,
                args.continue_on_error, args.retry_failed,
            )
            print(json.dumps({
                name: sum(s.get("status") == name for s in state["shots"].values())
                for name in ("completed", "failed", "queued")
            }, indent=2))
        return 0
    except (ValueError, OSError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
