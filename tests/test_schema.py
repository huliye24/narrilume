import json

import pytest

from narrilume.schema import load_project, resolve_reference


def project_data():
    return {
        "schema_version": "0.1",
        "project_id": "demo_film",
        "title": "Demo film",
        "fps": 16,
        "width": 832,
        "height": 480,
        "shots": [{"id": "s1", "prompt": "A moving boat", "seed": 42, "frames": 81}],
    }


def write_project(tmp_path, data):
    path = tmp_path / "project.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_valid_project(tmp_path):
    project = load_project(write_project(tmp_path, project_data()))
    assert project.id == "demo_film"
    assert project.shots[0].negative_prompt == ""
    assert project.shots[0].seed == 42


def test_duplicate_shot_rejected(tmp_path):
    data = project_data()
    data["shots"].append(dict(data["shots"][0]))
    with pytest.raises(ValueError, match="duplicate shot"):
        load_project(write_project(tmp_path, data))


@pytest.mark.parametrize("field,value", [("fps", True), ("width", -1), ("height", 0)])
def test_reject_invalid_video_params(tmp_path, field, value):
    data = project_data()
    data[field] = value
    with pytest.raises(ValueError):
        load_project(write_project(tmp_path, data))


def test_reference_image_may_not_escape_project(tmp_path):
    data = project_data()
    data["shots"][0]["reference_image"] = "../secret.png"
    project = load_project(write_project(tmp_path, data))
    with pytest.raises(ValueError, match="escapes"):
        resolve_reference(project, project.shots[0])
