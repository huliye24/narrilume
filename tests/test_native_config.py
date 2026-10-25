import json
from dataclasses import replace

import pytest

from narrilume.native_config import load_native_config, validate_native_project
from narrilume.native_production import native_plan
from narrilume.schema import load_project


def write(tmp_path, filename, value):
    path = tmp_path / filename
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def model_values():
    return {
        "schema_version": "0.1",
        "backend": "wan-t2v",
        "model_path": "models/wan",
        "revision": "checkpoint-abc",
        "steps": 24,
        "guidance_scale": 5.0,
        "cpu_offload": True,
    }


def project_values():
    return {
        "schema_version": "0.1",
        "project_id": "story",
        "title": "Story",
        "fps": 16,
        "width": 832,
        "height": 480,
        "shots": [{"id": "shot1", "prompt": "A boat", "seed": 1, "frames": 81}],
    }


def test_offline_plan_does_not_require_weights(tmp_path):
    project = write(tmp_path, "project.json", project_values())
    model = write(tmp_path, "model.json", model_values())
    plan = native_plan(project, model)
    assert plan["project_id"] == "story"
    assert plan["shots"][0]["seconds"] == 81 / 16
    assert plan["backend"] == "wan-t2v"


def test_model_path_resolved_relative_to_config(tmp_path):
    path = write(tmp_path, "model.json", model_values())
    config = load_native_config(path)
    assert config.model_path == tmp_path / "models" / "wan"


@pytest.mark.parametrize(
    "field,value",
    [
        ("backend", "comfy"),
        ("revision", ""),
        ("steps", True),
        ("steps", 0),
        ("guidance_scale", float("nan")),
        ("model_path", "https://hf.co/weights"),
        ("cpu_offload", "yes"),
    ],
)
def test_invalid_model_config_fails(tmp_path, field, value):
    data = model_values()
    data[field] = value
    with pytest.raises(ValueError):
        load_native_config(write(tmp_path, "model.json", data))


def test_t2v_rejects_reference_image(tmp_path):
    data = project_values()
    img = tmp_path / "frame.png"
    img.write_bytes(b"fake")
    data["shots"][0]["reference_image"] = "frame.png"
    project = load_project(write(tmp_path, "project.json", data))
    model = load_native_config(write(tmp_path, "model.json", model_values()))
    with pytest.raises(ValueError, match="wan-t2v"):
        validate_native_project(project, model)


def test_i2v_requires_reference_image(tmp_path):
    project = load_project(write(tmp_path, "project.json", project_values()))
    config = load_native_config(write(tmp_path, "model.json", model_values()))
    with pytest.raises(ValueError, match="requires"):
        validate_native_project(project, replace(config, backend="wan-i2v"))


def test_wan_frame_alignment_fails_before_gpu(tmp_path):
    data = project_values()
    data["shots"][0]["frames"] = 80
    project = load_project(write(tmp_path, "project.json", data))
    config = load_native_config(write(tmp_path, "model.json", model_values()))
    with pytest.raises(ValueError, match="4\\*k\\+1"):
        validate_native_project(project, config)
