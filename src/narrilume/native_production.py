"""Direct local-model execution with durable shot ledger and explicit retry semantics."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any

from .native_backend import WanDiffusersBackend
from .native_config import NativeModelConfig, inspect_local_weights, load_native_config, validate_native_project
from .production import _read_state, _timestamp, _write_json_atomic
from .schema import Project, Shot, load_project, resolve_reference
from .video_probe import probe_video


def shot_fingerprint(project: Project, shot: Shot, model: NativeModelConfig) -> str:
    reference = resolve_reference(project, shot)
    reference_digest = None
    if reference is not None:
        digest = hashlib.sha256()
        with reference.open("rb") as stream:
            while chunk := stream.read(1024 * 1024):
                digest.update(chunk)
        reference_digest = digest.hexdigest()
    identity = {
        "project": project.id,
        "fps": project.fps,
        "width": project.width,
        "height": project.height,
        "shot": vars(shot),
        "reference_sha256": reference_digest,
        "model": model.identity(),
    }
    return hashlib.sha256(
        json.dumps(identity, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def native_plan(project_path: str | Path, model_path: str | Path) -> dict[str, Any]:
    project = load_project(project_path)
    model = load_native_config(model_path)
    validate_native_project(project, model)
    return {
        "project_id": project.id,
        "backend": model.backend,
        "model_path": str(model.model_path),
        "revision": model.revision,
        "shots": [
            {
                "id": s.id,
                "seconds": round(s.frames / project.fps, 3),
                "frames": s.frames,
                "seed": s.seed,
                "fingerprint": shot_fingerprint(project, s, model),
            }
            for s in project.shots
        ],
    }


def render_native(
    project_path: str | Path,
    model_path: str | Path,
    output: str | Path,
    *,
    retry_failed: bool = False,
    continue_on_error: bool = False,
) -> dict[str, Any]:
    project = load_project(project_path)
    config = load_native_config(model_path)
    validate_native_project(project, config)
    inspect_local_weights(config)
    output = Path(output).expanduser().resolve()
    path = output / "state.json"
    state = _read_state(path, project)
    existing_engine = state.get("engine")
    if existing_engine not in {None, "native"}:
        raise ValueError("output directory belongs to ComfyUI; select a different run folder")
    state["engine"] = "native"
    backend: WanDiffusersBackend | None = None

    for shot in project.shots:
        signature = shot_fingerprint(project, shot, config)
        previous = state["shots"].get(shot.id, {})
        same = previous.get("signature") == signature
        cached = previous.get("video")
        if same and previous.get("status") == "completed" and isinstance(cached, str):
            clip = (output / cached).resolve()
            if clip.is_relative_to(output) and clip.is_file():
                if clip.stat().st_size and clip.is_relative_to(output / "shots"):
                    continue
        if same and previous.get("status") in {"running", "failed"} and not retry_failed:
            raise RuntimeError(
                f"{shot.id}: prior attempt was interrupted/failed; inspect state.json "
                "then pass --retry-failed to generate a new take"
            )

        item: dict[str, Any] = dict(previous) if same else {}
        item.pop("video", None)
        item.pop("probe", None)
        item["signature"] = signature
        item["model_revision"] = config.revision
        item["backend"] = config.backend
        item["attempts"] = int(item.get("attempts", 0)) + 1
        item["status"] = "running"
        item["started_at"] = _timestamp()
        item["error"] = None
        state["shots"][shot.id] = item
        _write_json_atomic(path, state)

        tmp = output / "shots" / (shot.id + ".partial.mp4")
        finished = output / "shots" / (shot.id + ".mp4")
        try:
            if backend is None:
                backend = WanDiffusersBackend(config)
            tmp.unlink(missing_ok=True)
            start = time.monotonic()
            backend.generate(project, shot, tmp)
            report = probe_video(tmp)
            if report["width"] != project.width or report["height"] != project.height:
                raise ValueError(f"{shot.id}: generated video size differs from project")
            os.replace(tmp, finished)
            item.update(
                status="completed",
                video=str(finished.relative_to(output)),
                probe=report,
                elapsed_seconds=round(time.monotonic() - start, 3),
                completed_at=_timestamp(),
            )
        except Exception as exc:
            item.update(status="failed", error=f"{type(exc).__name__}: {exc}",
                        completed_at=_timestamp())
            if not continue_on_error:
                state["shots"][shot.id] = item
                _write_json_atomic(path, state)
                raise
        finally:
            tmp.unlink(missing_ok=True)
        state["shots"][shot.id] = item
        _write_json_atomic(path, state)
    return state
