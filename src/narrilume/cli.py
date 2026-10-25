"""Narrilume command line interface."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .comfy import ComfyClient
from .production import assemble, render
from .schema import load_project, resolve_reference
from .workflow import load_bindings, load_workflow, validate_bindings


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="narrilume", description="Local-first ComfyUI animation production"
    )
    commands = parser.add_subparsers(dest="command", required=True)

    check = commands.add_parser("validate", help="validate project and workflow bindings")
    check.add_argument("project")
    check.add_argument("--workflow", required=True)
    check.add_argument("--bindings", required=True)

    health = commands.add_parser("health", help="check locally accessible ComfyUI")
    health.add_argument("--comfy-url", default=os.getenv("NARRILUME_COMFY_URL", "http://127.0.0.1:8188"))

    render_command = commands.add_parser("render", help="render/resume shots sequentially")
    render_command.add_argument("project")
    render_command.add_argument("--workflow", required=True)
    render_command.add_argument("--bindings", required=True)
    render_command.add_argument("--output", required=True)
    render_command.add_argument("--comfy-url", default=os.getenv("NARRILUME_COMFY_URL", "http://127.0.0.1:8188"))
    render_command.add_argument(
        "--timeout", type=float, default=float(os.getenv("NARRILUME_TIMEOUT_SECONDS", "3600"))
    )
    render_command.add_argument(
        "--poll-interval", type=float, default=float(os.getenv("NARRILUME_POLL_INTERVAL", "3"))
    )
    render_command.add_argument("--continue-on-error", action="store_true")
    render_command.add_argument("--retry-failed", action="store_true")

    join = commands.add_parser("assemble", help="stitch completed animation clips into MP4")
    join.add_argument("project")
    join.add_argument("--output", required=True)

    status = commands.add_parser("status", help="read the saved shot manifest")
    status.add_argument("--output", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "validate":
            project = load_project(args.project)
            workflow = load_workflow(args.workflow)
            bindings = load_bindings(args.bindings)
            validate_bindings(workflow, bindings)
            for shot in project.shots:
                resolve_reference(project, shot)
                if shot.reference_image and "reference_image" not in bindings:
                    raise ValueError(f"{shot.id}: missing reference_image binding")
            print(f"Valid: {project.id}, {len(project.shots)} shots")
        elif args.command == "health":
            client = ComfyClient(args.comfy_url)
            print(json.dumps(client.health(), ensure_ascii=False, indent=2))
        elif args.command == "render":
            if args.timeout <= 0 or args.poll_interval <= 0:
                raise ValueError("timeout and poll-interval must be positive")
            state = render(
                args.project, args.workflow, args.bindings, args.output,
                args.comfy_url, args.timeout, args.poll_interval,
                args.continue_on_error, args.retry_failed
            )
            counts = {
                key: sum(shot.get("status") == key for shot in state["shots"].values())
                for key in ("completed", "failed", "queued")
            }
            print(json.dumps(counts, indent=2))
            if counts["failed"]:
                return 1
        elif args.command == "assemble":
            print(assemble(args.project, args.output))
        elif args.command == "status":
            path = Path(args.output) / "state.json"
            print(path.read_text(encoding="utf-8"))
        return 0
    except (ValueError, OSError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
