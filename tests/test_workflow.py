import json
from dataclasses import replace

import pytest

from narrilume.schema import load_project
from narrilume.workflow import (
    load_bindings,
    load_workflow,
    render_workflow,
    validate_bindings,
)


def make_project(tmp_path):
    data = {
        "schema_version": "0.1",
        "project_id": "demo",
        "title": "Demo",
        "fps": 16,
        "width": 832,
        "height": 480,
        "shots": [{"id": "s1", "prompt": "Moving boat", "seed": 123, "frames": 81}],
    }
    path = tmp_path / "project.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return load_project(path)


def nodes():
    return {
        "6": {"class_type": "CLIPTextEncode", "inputs": {"text": "old"}},
        "3": {"class_type": "KSampler", "inputs": {"seed": 99}},
        "15": {"class_type": "VideoLatent", "inputs": {"length": 40}},
    }


def bindings():
    return {
        "positive_prompt": {"node": "6", "input": "text"},
        "seed": {"node": "3", "input": "seed"},
        "frames": {"node": "15", "input": "length"},
    }


def test_workflow_input_binding_does_not_mutate_template(tmp_path):
    project = make_project(tmp_path)
    original = nodes()
    patched = render_workflow(original, bindings(), project, project.shots[0])
    assert patched["6"]["inputs"]["text"] == "Moving boat"
    assert patched["3"]["inputs"]["seed"] == 123
    assert patched["15"]["inputs"]["length"] == 81
    assert original["6"]["inputs"]["text"] == "old"


def test_missing_node_rejected():
    mapping = bindings()
    mapping["seed"]["node"] = "missing"
    with pytest.raises(ValueError, match="missing node"):
        validate_bindings(nodes(), mapping)


def test_comfy_editor_format_is_rejected(tmp_path):
    path = tmp_path / "workflow.json"
    path.write_text('{"nodes":[{"id":1}]}', encoding="utf-8")
    with pytest.raises(ValueError, match="API-format"):
        load_workflow(path)


def test_unknown_mapping_key_is_rejected(tmp_path):
    path = tmp_path / "bindings.json"
    path.write_text(json.dumps({**bindings(), "mystery": {"node": "1", "input": "x"}}))
    with pytest.raises(ValueError, match="unknown"):
        load_bindings(path)


def test_reference_image_binding_required(tmp_path):
    project = make_project(tmp_path)
    shot = replace(project.shots[0], reference_image="reference.png")
    with pytest.raises(ValueError, match="binding is missing"):
        render_workflow(nodes(), bindings(), project, shot, "uploaded.png")
