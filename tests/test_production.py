import json
from pathlib import Path
from unittest.mock import patch

import pytest

from narrilume.production import assemble, render


def write_project(tmp_path, count=2):
    project = tmp_path / "project.json"
    project.write_text(
        json.dumps(
            {
                "schema_version": "0.1",
                "project_id": "film",
                "title": "Test",
                "fps": 16,
                "width": 832,
                "height": 480,
                "shots": [
                    {"id": f"s{i}", "prompt": f"Scene {i}", "seed": i, "frames": 16}
                    for i in range(1, count + 1)
                ],
            }
        )
    )
    return project


def test_render_dispatches_sequentially_and_resumes(tmp_path):
    project = write_project(tmp_path)
    workflow = tmp_path / "workflow.json"
    bindings = tmp_path / "bindings.json"
    out = tmp_path / "run"
    workflow.write_text(
        json.dumps({"1": {"class_type": "TextNode", "inputs": {"text": ""}}})
    )
    bindings.write_text(json.dumps({"positive_prompt": {"node": "1", "input": "text"}}))

    class FakeComfy:
        submitted = []

        def __init__(self, *_args, **_kwargs):
            pass

        def health(self):
            return {}

        def submit(self, prompt):
            self.submitted.append(prompt["1"]["inputs"]["text"])
            return f"prompt_{len(self.submitted)}"

        def wait(self, prompt_id, timeout, poll_interval):
            return {"outputs": {}, "status": {"completed": True}}

        def download_video(self, history, target):
            target = Path(str(target) + ".mp4")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b"test-mp4-content")
            return {"file": str(target), "remote_filename": "clip.mp4"}

    with patch("narrilume.production.ComfyClient", FakeComfy):
        state = render(project, workflow, bindings, out, "http://127.0.0.1:8188")
        assert state["shots"]["s1"]["status"] == "completed"
        assert state["shots"]["s2"]["status"] == "completed"
        assert FakeComfy.submitted == ["Scene 1", "Scene 2"]

        render(project, workflow, bindings, out, "http://127.0.0.1:8188")
        assert FakeComfy.submitted == ["Scene 1", "Scene 2"]

        # Changing a single shot invalidates only that shot's previous clip.
        changed = json.loads(project.read_text())
        changed["shots"][0]["prompt"] = "Revised Scene 1"
        project.write_text(json.dumps(changed))
        render(project, workflow, bindings, out, "http://127.0.0.1:8188")
        assert FakeComfy.submitted == ["Scene 1", "Scene 2", "Revised Scene 1"]


def test_assemble_requires_complete_clips(tmp_path):
    project = write_project(tmp_path, count=1)
    with pytest.raises(ValueError, match="not completed"):
        assemble(project, tmp_path / "run")


def test_timeout_keeps_existing_prompt_for_resume(tmp_path):
    project = write_project(tmp_path, count=1)
    workflow = tmp_path / "workflow.json"
    bindings = tmp_path / "bindings.json"
    output = tmp_path / "run"
    workflow.write_text(json.dumps({"1": {"class_type": "Prompt", "inputs": {"text": ""}}}))
    bindings.write_text(json.dumps({"positive_prompt": {"node": "1", "input": "text"}}))

    class InterruptedComfy:
        submitted = 0
        timeout_once = True

        def __init__(self, *_args, **_kwargs):
            pass

        def health(self):
            return {}

        def submit(self, graph):
            self.submitted += 1
            return "persisted-prompt-id"

        def wait(self, prompt_id, timeout, poll_interval):
            assert prompt_id == "persisted-prompt-id"
            if self.timeout_once:
                self.timeout_once = False
                raise TimeoutError("render still running")
            return {"outputs": {}, "status": {"completed": True}}

        def download_video(self, history, target):
            path = Path(str(target) + ".mp4")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"clip")
            return {"file": str(path), "remote_filename": "clip.mp4"}

    with patch("narrilume.production.ComfyClient", InterruptedComfy):
        with pytest.raises(TimeoutError):
            render(project, workflow, bindings, output, "http://127.0.0.1:8188")
        state = json.loads((output / "state.json").read_text())
        assert state["shots"]["s1"]["status"] == "queued"
        assert state["shots"]["s1"]["prompt_id"] == "persisted-prompt-id"
        assert render(project, workflow, bindings, output, "http://127.0.0.1:8188")[
            "shots"
        ]["s1"]["status"] == "completed"
        assert InterruptedComfy.submitted == 1
