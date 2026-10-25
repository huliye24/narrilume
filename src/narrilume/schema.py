"""A minimal, versioned contract for an animation project and its shots."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_ID = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$")
_SUPPORTED_SCHEMA = "0.1"


@dataclass(frozen=True)
class Shot:
    id: str
    prompt: str
    negative_prompt: str
    seed: int
    frames: int
    reference_image: str | None = None


@dataclass(frozen=True)
class Project:
    id: str
    title: str
    fps: int
    width: int
    height: int
    shots: tuple[Shot, ...]
    source: Path


def _integer(value: Any, name: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer")
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return value


def _identifier(value: Any, name: str) -> str:
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise ValueError(f"{name} must be a 1-64 character ASCII identifier")
    return value


def load_project(path: str | Path) -> Project:
    source = Path(path).expanduser().resolve()
    data = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("project must be a JSON object")
    if data.get("schema_version") != _SUPPORTED_SCHEMA:
        raise ValueError(f"schema_version must be {_SUPPORTED_SCHEMA!r}")
    project_id = _identifier(data.get("project_id"), "project_id")
    title = data.get("title")
    if not isinstance(title, str) or not title.strip():
        raise ValueError("title must be a nonempty string")
    fps = _integer(data.get("fps"), "fps", 1, 120)
    width = _integer(data.get("width"), "width", 64, 8192)
    height = _integer(data.get("height"), "height", 64, 8192)
    items = data.get("shots")
    if not isinstance(items, list) or not items:
        raise ValueError("shots must be a nonempty array")
    shots: list[Shot] = []
    seen: set[str] = set()
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValueError(f"shots[{index}] must be an object")
        shot_id = _identifier(item.get("id"), f"shots[{index}].id")
        if shot_id in seen:
            raise ValueError(f"duplicate shot id: {shot_id}")
        seen.add(shot_id)
        prompt = item.get("prompt")
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError(f"{shot_id}.prompt must be a nonempty string")
        negative = item.get("negative_prompt", "")
        if not isinstance(negative, str):
            raise ValueError(f"{shot_id}.negative_prompt must be a string")
        reference = item.get("reference_image")
        if reference is not None and (
            not isinstance(reference, str) or not reference.strip()
        ):
            raise ValueError(f"{shot_id}.reference_image must be a nonempty path")
        shots.append(
            Shot(
                id=shot_id,
                prompt=prompt,
                negative_prompt=negative,
                seed=_integer(item.get("seed"), f"{shot_id}.seed", 0, 2**64 - 1),
                frames=_integer(item.get("frames"), f"{shot_id}.frames", 2, 1200),
                reference_image=reference,
            )
        )
    return Project(
        id=project_id,
        title=title,
        fps=fps,
        width=width,
        height=height,
        shots=tuple(shots),
        source=source,
    )


def resolve_reference(project: Project, shot: Shot) -> Path | None:
    """Constrain relative reference paths to the project directory."""
    if shot.reference_image is None:
        return None
    relative = Path(shot.reference_image)
    if relative.is_absolute():
        raise ValueError(f"{shot.id}: absolute reference_image paths are not allowed")
    root = project.source.parent
    candidate = (root / relative).resolve()
    if not candidate.is_relative_to(root):
        raise ValueError(f"{shot.id}: reference_image escapes project directory")
    if not candidate.is_file():
        raise FileNotFoundError(f"{shot.id}: reference_image not found: {candidate}")
    if candidate.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
        raise ValueError(f"{shot.id}: reference_image must be png, jpeg or webp")
    return candidate
