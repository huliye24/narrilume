"""Small standard-library ComfyUI HTTP client; never needs a cloud API key."""

from __future__ import annotations

import json
import mimetypes
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any

_VIDEO_EXTENSIONS = {".mp4", ".webm", ".mov", ".mkv"}


class ComfyError(RuntimeError):
    pass


class ComfyClient:
    def __init__(self, base_url: str, request_timeout: float = 60) -> None:
        parts = urllib.parse.urlsplit(base_url)
        if parts.scheme not in {"http", "https"} or not parts.netloc:
            raise ValueError("ComfyUI URL must use http(s) and contain a hostname")
        if parts.username or parts.password or parts.query or parts.fragment:
            raise ValueError("ComfyUI URL must not contain credentials/query/fragment")
        self.base_url = base_url.rstrip("/")
        self.request_timeout = request_timeout
        self.client_id = str(uuid.uuid4())

    def _request(
        self, method: str, path: str, payload: bytes | None = None,
        content_type: str | None = None
    ) -> bytes:
        headers = {"Accept": "application/json"}
        if content_type:
            headers["Content-Type"] = content_type
        request = urllib.request.Request(
            self.base_url + path, data=payload, headers=headers, method=method
        )
        try:
            with urllib.request.urlopen(request, timeout=self.request_timeout) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read(4096).decode("utf-8", errors="replace")
            raise ComfyError(f"ComfyUI HTTP {exc.code} at {path}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise ComfyError(f"Could not reach ComfyUI at {self.base_url}: {exc}") from exc

    def json_request(
        self, method: str, path: str, data: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        payload = None if data is None else json.dumps(data).encode("utf-8")
        result = json.loads(self._request(method, path, payload, "application/json" if payload else None))
        if not isinstance(result, dict):
            raise ComfyError(f"Expected JSON object from ComfyUI at {path}")
        return result

    def health(self) -> dict[str, Any]:
        return self.json_request("GET", "/system_stats")

    def submit(self, workflow: dict[str, Any]) -> str:
        response = self.json_request(
            "POST", "/prompt", {"prompt": workflow, "client_id": self.client_id}
        )
        prompt_id = response.get("prompt_id")
        if not isinstance(prompt_id, str) or not prompt_id:
            raise ComfyError(f"ComfyUI rejected prompt: {response}")
        return prompt_id

    def history(self, prompt_id: str) -> dict[str, Any] | None:
        data = self.json_request(
            "GET", "/history/" + urllib.parse.quote(prompt_id, safe="")
        )
        record = data.get(prompt_id)
        return record if isinstance(record, dict) else None

    def wait(
        self, prompt_id: str, timeout: float = 3600, poll_interval: float = 3
    ) -> dict[str, Any]:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            record = self.history(prompt_id)
            if record is not None:
                status = record.get("status", {})
                if isinstance(status, dict):
                    if status.get("status_str") == "error" or status.get("completed") is False:
                        raise ComfyError(f"ComfyUI execution failed for {prompt_id}: {status}")
                    if status.get("completed") is True or status.get("status_str") == "success":
                        return record
                # Some legacy ComfyUI builds do not populate the complete status.
                if record.get("outputs"):
                    return record
            time.sleep(poll_interval)
        raise TimeoutError(f"ComfyUI prompt {prompt_id} exceeded {timeout}s")

    def upload_image(self, path: Path) -> str:
        if path.stat().st_size > 32 * 1024 * 1024:
            raise ValueError("reference image is over the 32 MiB upload limit")
        boundary = "----narrilume-" + uuid.uuid4().hex
        mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        prefix = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="image"; filename="{path.name}"\r\n'
            f"Content-Type: {mime}\r\n\r\n"
        ).encode("utf-8")
        body = prefix + path.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
        result = json.loads(
            self._request(
                "POST", "/upload/image", body, f"multipart/form-data; boundary={boundary}"
            )
        )
        name = result.get("name")
        if not isinstance(name, str) or not name:
            raise ComfyError(f"ComfyUI did not return uploaded image name: {result}")
        subfolder = result.get("subfolder", "")
        return f"{subfolder}/{name}" if subfolder else name

    def download_video(self, record: dict[str, Any], destination: Path) -> dict[str, str]:
        artifact = find_video_output(record)
        query = urllib.parse.urlencode(
            {
                "filename": artifact["filename"],
                "subfolder": artifact.get("subfolder", ""),
                "type": artifact.get("type", "output"),
            }
        )
        suffix = Path(artifact["filename"]).suffix.lower()
        destination = destination.with_suffix(suffix)
        destination.parent.mkdir(parents=True, exist_ok=True)
        temp = destination.with_name(destination.name + ".part")
        request = urllib.request.Request(
            self.base_url + "/view?" + query,
            headers={"Accept": "application/octet-stream"},
            method="GET",
        )
        received = 0
        try:
            with urllib.request.urlopen(request, timeout=self.request_timeout) as response:
                with temp.open("wb") as handle:
                    while True:
                        chunk = response.read(1024 * 1024)
                        if not chunk:
                            break
                        received += len(chunk)
                        if received > 2 * 1024**3:
                            raise ComfyError("video exceeded the 2 GiB scene limit")
                        handle.write(chunk)
            if not received:
                raise ComfyError("video artifact is empty")
            temp.replace(destination)
        except urllib.error.HTTPError as exc:
            raise ComfyError(f"Could not download ComfyUI video: HTTP {exc.code}") from exc
        except urllib.error.URLError as exc:
            raise ComfyError(f"ComfyUI video download failed: {exc}") from exc
        finally:
            temp.unlink(missing_ok=True)
        return {"file": str(destination), "remote_filename": artifact["filename"]}


def find_video_output(record: dict[str, Any]) -> dict[str, str]:
    """ComfyUI video outputs vary by node: often in videos or gifs arrays."""
    outputs = record.get("outputs")
    if not isinstance(outputs, dict):
        raise ComfyError("ComfyUI history does not contain outputs")
    for node in outputs.values():
        if not isinstance(node, dict):
            continue
        for key in ("videos", "gifs", "video", "files"):
            group = node.get(key, [])
            if isinstance(group, dict):
                group = [group]
            if not isinstance(group, list):
                continue
            for item in group:
                if not isinstance(item, dict):
                    continue
                filename = item.get("filename")
                if isinstance(filename, str) and Path(filename).suffix.lower() in _VIDEO_EXTENSIONS:
                    file_type = item.get("type", "output")
                    if file_type != "output":
                        continue
                    return {
                        "filename": filename,
                        "subfolder": str(item.get("subfolder") or ""),
                        "type": "output",
                    }
    raise ComfyError(
        "No saved video found in ComfyUI history. Add a SaveVideo/VideoCombine "
        "output node that writes MP4/WebM/MOV/MKV to the output directory."
    )
