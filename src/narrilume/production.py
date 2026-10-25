"""Sequential shot execution, durable progress records and deterministic assembly."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .comfy import ComfyClient, ComfyError
from .schema import Project, load_project, resolve_reference
from .workflow import load_bindings, load_workflow, render_workflow, validate_bindings


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _shot_signature(
    project: Project, shot: Any, workflow: dict[str, Any],
    bindings: dict[str, dict[str, str]]
) -> str:
    """Invalidate cached video whenever a source shot or workflow changes."""
    source = resolve_reference(project, shot)
    reference_hash = hashlib.sha256(source.read_bytes()).hexdigest() if source else None
    identity = {
        "project_id": project.id,
        "fps": project.fps,
        "width": project.width,
        "height": project.height,
        "shot": vars(shot),
        "reference_sha256": reference_hash,
        "workflow": workflow,
        "bindings": bindings,
    }
    payload = json.dumps(identity, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, delete=False
    ) as handle:
        temporary = Path(handle.name)
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    os.replace(temporary, path)


def _read_state(path: Path, project: Project) -> dict[str, Any]:
    if not path.exists():
        return {
            "schema_version": "0.1",
            "project_id": project.id,
            "created_at": _timestamp(),
            "shots": {},
        }
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("project_id") != project.id:
        raise ValueError("run directory belongs to a different project")
    return value


def render(
    project_path: str | Path,
    workflow_path: str | Path,
    bindings_path: str | Path,
    output: str | Path,
    comfy_url: str,
    timeout: float = 3600,
    poll_interval: float = 3,
    continue_on_error: bool = False,
    retry_failed: bool = False,
) -> dict[str, Any]:
    project = load_project(project_path)
    workflow = load_workflow(workflow_path)
    bindings = load_bindings(bindings_path)
    validate_bindings(workflow, bindings)

    output = Path(output).expanduser().resolve()
    state_path = output / "state.json"
    state = _read_state(state_path, project)
    client = ComfyClient(comfy_url)
    client.health()
    for shot in project.shots:
        signature = _shot_signature(project, shot, workflow, bindings)
        previous = state["shots"].get(shot.id, {})
        previous_status = previous.get("status")
        same_inputs = previous.get("signature") == signature
        if previous_status in {"queued", "submitting"} and not same_inputs:
            raise ValueError(
                f"{shot.id}: inputs changed while job is in flight; reconcile state.json first"
            )
        video = previous.get("video")
        if same_inputs and previous_status == "completed" and isinstance(video, str):
            existing = (output / video).resolve()
            if existing.is_relative_to(output) and existing.is_file() and existing.stat().st_size:
                continue
        if same_inputs and previous_status in {"failed", "submitting"} and not retry_failed:
            raise ValueError(
                f"{shot.id}: previous job requires review; pass --retry-failed to resubmit "
                "(may duplicate work if prior submission reached ComfyUI)"
            )

        record = dict(previous) if same_inputs else {}
        record.setdefault("attempts", 0)
        record["signature"] = signature
        if retry_failed and record.get("status") in {"failed", "submitting"}:
            record.pop("prompt_id", None)
            record["status"] = "retrying"
        try:
            if record.get("status") != "queued" or not record.get("prompt_id"):
                reference_path = resolve_reference(project, shot)
                remote_image = client.upload_image(reference_path) if reference_path else None
                prompt = render_workflow(workflow, bindings, project, shot, remote_image)
                record["attempts"] += 1
                record["status"] = "submitting"
                record["updated_at"] = _timestamp()
                state["shots"][shot.id] = record
                _write_json_atomic(state_path, state)
                prompt_id = client.submit(prompt)
                record["prompt_id"] = prompt_id
                record["status"] = "queued"
                record["updated_at"] = _timestamp()
                _write_json_atomic(state_path, state)

            history = client.wait(
                record["prompt_id"], timeout=timeout, poll_interval=poll_interval
            )
            downloaded = client.download_video(history, output / "shots" / shot.id)
            record.update(
                {
                    "status": "completed",
                    "video": str(Path(downloaded["file"]).relative_to(output)),
                    "source_file": downloaded["remote_filename"],
                    "updated_at": _timestamp(),
                    "error": None,
                }
            )
        except TimeoutError as exc:
            # ComfyUI may still be rendering. Keep the prompt ID and poll on next run.
            record["status"] = "queued"
            record["error"] = str(exc)
            record["updated_at"] = _timestamp()
            state["shots"][shot.id] = record
            _write_json_atomic(state_path, state)
            raise
        except (ComfyError, OSError, ValueError) as exc:
            record["status"] = "failed"
            record["error"] = str(exc)
            record["updated_at"] = _timestamp()
            state["shots"][shot.id] = record
            _write_json_atomic(state_path, state)
            if not continue_on_error:
                raise
        state["shots"][shot.id] = record
        _write_json_atomic(state_path, state)
    return state


def assemble(project_path: str | Path, output: str | Path) -> Path:
    """Normalize all clips then concatenate in storyboard order; video only."""
    project = load_project(project_path)
    output = Path(output).expanduser().resolve()
    state = _read_state(output / "state.json", project)
    source_files: list[Path] = []
    for shot in project.shots:
        record = state["shots"].get(shot.id, {})
        path = record.get("video")
        if record.get("status") != "completed" or not isinstance(path, str):
            raise ValueError(f"cannot assemble: shot {shot.id} is not completed")
        source = (output / path).resolve()
        if not source.is_relative_to(output) or not source.is_file():
            raise ValueError(f"cannot assemble: missing or invalid clip for {shot.id}")
        source_files.append(source)
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg must be installed and available in PATH")
    output.mkdir(parents=True, exist_ok=True)
    target = output / (project.id + ".mp4")
    with tempfile.TemporaryDirectory(dir=output, prefix=".assemble-") as workspace:
        scratch = Path(workspace)
        normalized: list[Path] = []
        for index, path in enumerate(source_files):
            normalized_path = scratch / f"shot_{index:04d}.mp4"
            scale_filter = (
                f"scale={project.width}:{project.height}:"
                "force_original_aspect_ratio=decrease,"
                f"pad={project.width}:{project.height}:(ow-iw)/2:(oh-ih)/2,"
                f"fps={project.fps},format=yuv420p"
            )
            subprocess.run(
                [
                    "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
                    "-i", str(path), "-vf", scale_filter, "-an",
                    "-c:v", "libx264", "-crf", "20", "-preset", "medium",
                    str(normalized_path),
                ],
                check=True,
            )
            normalized.append(normalized_path)
        listing = scratch / "concat.txt"
        listing.write_text(
            "".join(f"file '{path.name}'\n" for path in normalized), encoding="utf-8"
        )
        temporary_target = scratch / "assembled.mp4"
        subprocess.run(
            [
                "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
                "-f", "concat", "-safe", "0", "-i", str(listing),
                "-c", "copy", "-movflags", "+faststart", str(temporary_target),
            ],
            cwd=scratch,
            check=True,
        )
        os.replace(temporary_target, target)
    return target
