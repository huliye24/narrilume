import json
from unittest.mock import patch

import pytest

from narrilume.native_production import render_native


def fixtures(tmp_path):
    project = tmp_path / "project.json"
    model = tmp_path / "model.json"
    model_dir = tmp_path / "local-weights"
    model_dir.mkdir()
    (model_dir / "model_index.json").write_text('{"_class_name":"WanPipeline"}')
    project.write_text(
        json.dumps(
            {
                "schema_version": "0.1", "project_id": "short", "title": "Short",
                "fps": 16, "width": 832, "height": 480,
                "shots": [
                    {"id": "a", "prompt": "Boat enters", "seed": 1, "frames": 81},
                    {"id": "b", "prompt": "Boat leaves", "seed": 2, "frames": 81},
                ],
            }
        )
    )
    model.write_text(
        json.dumps(
            {
                "schema_version": "0.1", "backend": "wan-t2v",
                "model_path": str(model_dir), "revision": "rev1",
            }
        )
    )
    return project, model, tmp_path / "run"


def fake_probe(path):
    assert path.is_file()
    return {"width": 832, "height": 480, "duration_seconds": 5.0, "codec": "h264"}


class FakeBackend:
    rendered = []

    def __init__(self, cfg):
        self.cfg = cfg

    def generate(self, project, shot, destination):
        self.rendered.append(shot.prompt)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(b"fake video - probe mocked")


def test_native_render_resumes_and_invalidates_modified_shot(tmp_path):
    project, model, output = fixtures(tmp_path)
    FakeBackend.rendered = []
    with patch("narrilume.native_production.WanDiffusersBackend", FakeBackend):
        with patch("narrilume.native_production.probe_video", fake_probe):
            state = render_native(project, model, output)
            assert state["shots"]["a"]["status"] == "completed"
            assert state["shots"]["b"]["status"] == "completed"
            assert FakeBackend.rendered == ["Boat enters", "Boat leaves"]
            render_native(project, model, output)
            assert FakeBackend.rendered == ["Boat enters", "Boat leaves"]

            data = json.loads(project.read_text())
            data["shots"][0]["prompt"] = "Boat changes"
            project.write_text(json.dumps(data))
            render_native(project, model, output)
            assert FakeBackend.rendered == ["Boat enters", "Boat leaves", "Boat changes"]
            assert (output / "shots" / "a.mp4").exists()


def test_interrupted_job_requires_explicit_retry(tmp_path):
    project, model, output = fixtures(tmp_path)

    class BrokenBackend(FakeBackend):
        def generate(self, project, shot, destination):
            raise KeyboardInterrupt("user stopped render")

    with patch("narrilume.native_production.WanDiffusersBackend", BrokenBackend):
        with pytest.raises(KeyboardInterrupt):
            render_native(project, model, output)

    assert json.loads((output / "state.json").read_text())["shots"]["a"]["status"] == "running"

    with patch("narrilume.native_production.WanDiffusersBackend", FakeBackend):
        with patch("narrilume.native_production.probe_video", fake_probe):
            with pytest.raises(RuntimeError, match="--retry-failed"):
                render_native(project, model, output)
            state = render_native(project, model, output, retry_failed=True)
            assert state["shots"]["a"]["status"] == "completed"


def test_native_model_does_not_download_weights(tmp_path):
    project, model, output = fixtures(tmp_path)
    data = json.loads(model.read_text())
    data["model_path"] = str(tmp_path / "missing-weights")
    model.write_text(json.dumps(data))
    with pytest.raises(FileNotFoundError, match="model directory"):
        render_native(project, model, output)
    assert not output.exists()


def test_native_does_not_mix_legacy_and_native_outputs(tmp_path):
    project, model, output = fixtures(tmp_path)
    output.mkdir()
    (output / "state.json").write_text(json.dumps({
        "schema_version": "0.1", "project_id": "short", "engine": "comfy", "shots": {}
    }))
    with pytest.raises(ValueError, match="ComfyUI"):
        render_native(project, model, output)
