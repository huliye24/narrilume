"""Verify actual video streams, not merely nonzero file size."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any


def probe_video(path: Path) -> dict[str, Any]:
    if shutil.which("ffprobe") is None:
        raise RuntimeError("ffprobe (FFmpeg) is required to verify generated animation clips")
    if not path.is_file() or not path.stat().st_size:
        raise ValueError(f"missing or empty video clip: {path}")
    result = subprocess.run(
        [
            "ffprobe", "-v", "error", "-show_entries",
            "stream=codec_type,codec_name,width,height,avg_frame_rate,nb_frames",
            "-show_entries", "format=duration,size", "-of", "json", str(path)
        ],
        capture_output=True, text=True, check=True, timeout=120
    )
    data = json.loads(result.stdout)
    streams = [x for x in data.get("streams", []) if x.get("codec_type") == "video"]
    if not streams:
        raise ValueError(f"no decodable video stream in {path}")
    video = streams[0]
    if int(video.get("width") or 0) <= 0 or int(video.get("height") or 0) <= 0:
        raise ValueError(f"invalid video dimensions in {path}")
    duration = float(data.get("format", {}).get("duration") or 0)
    if duration <= 0:
        raise ValueError(f"invalid or missing video duration in {path}")
    return {
        "codec": video.get("codec_name"),
        "width": int(video["width"]),
        "height": int(video["height"]),
        "avg_frame_rate": video.get("avg_frame_rate"),
        "frames": video.get("nb_frames"),
        "duration_seconds": duration,
        "bytes": path.stat().st_size,
    }
