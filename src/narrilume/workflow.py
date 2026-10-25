"""Bind shot attributes to nodes in a ComfyUI API-format workflow."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from .schema import Project, Shot

_FIELDS = {
    "positive_prompt",
    "negative_prompt",
    "seed",
    "frames",
    "fps",
    "width",
    "height",
    "reference_image",
}


def load_workflow(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not data:
        raise ValueError("workflow must be a nonempty API-format node dictionary")
    if "nodes" in data or not all(
        isinstance(node, dict) and "class_type" in node and "inputs" in node
        for node in data.values()
    ):
        raise ValueError(
            "Expected ComfyUI API-format JSON; export via Save (API Format), "
            "not the visual editor workflow JSON"
        )
    return data


def load_bindings(path: str | Path) -> dict[str, dict[str, str]]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "positive_prompt" not in data:
        raise ValueError("bindings must be a JSON object with positive_prompt")
    if set(data) - _FIELDS:
        raise ValueError(f"unknown workflow bindings: {sorted(set(data) - _FIELDS)}")
    for field, mapping in data.items():
        if not isinstance(mapping, dict) or set(mapping) != {"node", "input"}:
            raise ValueError(f"{field} binding must contain only node and input")
        if not all(isinstance(value, str) and value for value in mapping.values()):
            raise ValueError(f"{field} binding node/input must be nonempty strings")
    return data


def validate_bindings(
    workflow: dict[str, Any], bindings: dict[str, dict[str, str]]
) -> None:
    for field, address in bindings.items():
        node = workflow.get(address["node"])
        if not isinstance(node, dict) or not isinstance(node.get("inputs"), dict):
            raise ValueError(f"{field}: missing node {address['node']}")
        if address["input"] not in node["inputs"]:
            raise ValueError(
                f"{field}: node {address['node']} has no input {address['input']}"
            )


def render_workflow(
    workflow: dict[str, Any],
    bindings: dict[str, dict[str, str]],
    project: Project,
    shot: Shot,
    uploaded_reference: str | None = None,
) -> dict[str, Any]:
    validate_bindings(workflow, bindings)
    if shot.reference_image and "reference_image" not in bindings:
        raise ValueError(f"{shot.id}: reference_image binding is missing")
    if shot.reference_image and not uploaded_reference:
        raise ValueError(f"{shot.id}: image must be uploaded before rendering")
    values: dict[str, Any] = {
        "positive_prompt": shot.prompt,
        "negative_prompt": shot.negative_prompt,
        "seed": shot.seed,
        "frames": shot.frames,
        "fps": project.fps,
        "width": project.width,
        "height": project.height,
    }
    if uploaded_reference:
        values["reference_image"] = uploaded_reference
    result = copy.deepcopy(workflow)
    for field, address in bindings.items():
        if field in values:
            result[address["node"]]["inputs"][address["input"]] = values[field]
    return result
