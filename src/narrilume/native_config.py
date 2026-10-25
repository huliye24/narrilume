"""Validated, explicitly offline configuration for a native video model."""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .schema import Project, resolve_reference

BACKENDS = {"wan-t2v", "wan-i2v"}


@dataclass(frozen=True)
class NativeModelConfig:
    backend: str
    model_path: Path
    revision: str
    dtype: str = "bfloat16"
    cpu_offload: bool = True
    steps: int = 30
    guidance_scale: float = 5.0

    def identity(self) -> dict[str, Any]:
        value = asdict(self)
        value["model_path"] = str(self.model_path)
        return value


def load_native_config(path: str | Path) -> NativeModelConfig:
    source = Path(path).expanduser().resolve()
    data = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("native model config must be an object")
    known = {"schema_version", "backend", "model_path", "revision",
             "dtype", "cpu_offload", "steps", "guidance_scale"}
    unknown = set(data) - known
    if unknown:
        raise ValueError(f"unknown native model options: {sorted(unknown)}")
    if data.get("schema_version") != "0.1":
        raise ValueError("model schema_version must be '0.1'")
    backend = data.get("backend")
    if backend not in BACKENDS:
        raise ValueError(f"backend must be one of {sorted(BACKENDS)}")
    model_path = data.get("model_path")
    if not isinstance(model_path, str) or not model_path.strip():
        raise ValueError("model_path must be a nonempty local directory")
    if "://" in model_path or model_path.startswith("hf:"):
        raise ValueError("remote model addresses are not allowed: download weights separately")
    model_root = Path(model_path).expanduser()
    if not model_root.is_absolute():
        model_root = source.parent / model_root
    model_root = model_root.resolve()
    revision = data.get("revision")
    if not isinstance(revision, str) or not revision.strip():
        raise ValueError("revision is required; update it whenever model weights change")
    dtype = data.get("dtype", "bfloat16")
    if dtype not in {"bfloat16", "float16", "float32"}:
        raise ValueError("dtype must be bfloat16, float16 or float32")
    offload = data.get("cpu_offload", True)
    if not isinstance(offload, bool):
        raise ValueError("cpu_offload must be boolean")
    steps = data.get("steps", 30)
    if type(steps) is not int or not 1 <= steps <= 150:
        raise ValueError("steps must be an integer in 1..150")
    guidance = data.get("guidance_scale", 5.0)
    if isinstance(guidance, bool) or not isinstance(guidance, (int, float)):
        raise ValueError("guidance_scale must be numeric")
    if not math.isfinite(float(guidance)) or not 0.0 <= guidance <= 30:
        raise ValueError("guidance_scale must be finite and in 0..30")
    return NativeModelConfig(
        backend=backend, model_path=model_root, revision=revision,
        dtype=dtype, cpu_offload=offload, steps=steps, guidance_scale=float(guidance)
    )


def validate_native_project(project: Project, config: NativeModelConfig) -> None:
    """Fail before loading any GPU weights; don't silently round shot dimensions."""
    if project.width % 32 or project.height % 32:
        raise ValueError("native Wan shots require width and height divisible by 32")
    for shot in project.shots:
        if (shot.frames - 1) % 4:
            raise ValueError(f"{shot.id}: Wan frame count must be 4*k+1 (e.g., 49 or 81)")
        resolve_reference(project, shot)
        if config.backend == "wan-t2v" and shot.reference_image is not None:
            raise ValueError(f"{shot.id}: wan-t2v cannot accept reference_image; use wan-i2v")
        if config.backend == "wan-i2v" and shot.reference_image is None:
            raise ValueError(f"{shot.id}: wan-i2v requires a local reference_image")


def inspect_local_weights(config: NativeModelConfig) -> None:
    """A local Diffusers layout is mandatory: no transparent model downloads."""
    if not config.model_path.is_dir():
        raise FileNotFoundError(f"model directory is missing: {config.model_path}")
    if not (config.model_path / "model_index.json").is_file():
        raise FileNotFoundError(
            f"missing model_index.json in {config.model_path}; "
            "use a locally downloaded Diffusers-formatted checkpoint"
        )
