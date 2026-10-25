import json
from pathlib import Path
from unittest.mock import patch

import pytest

from narrilume.video_probe import probe_video


def fake_run(output):
    class Result:
        stdout = json.dumps(output)
    return Result()


def test_accepts_video_stream(tmp_path):
    path = tmp_path / "shot.mp4"
    path.write_bytes(b"not real media; subprocess is stubbed")
    data = {"format": {"duration": "5.0625"}, "streams": [
        {"codec_type": "video", "codec_name": "h264", "width": 832, "height": 480,
         "avg_frame_rate": "16/1", "nb_frames": "81"},
    ]}
    with patch("narrilume.video_probe.shutil.which", return_value="/usr/bin/ffprobe"):
        with patch("narrilume.video_probe.subprocess.run", return_value=fake_run(data)):
            result = probe_video(path)
    assert result["width"] == 832
    assert result["frames"] == "81"


def test_rejects_audio_only_media(tmp_path):
    path = tmp_path / "audio.mp4"
    path.write_bytes(b"stub")
    data = {"format": {"duration": "4"}, "streams": [{"codec_type": "audio"}]}
    with patch("narrilume.video_probe.shutil.which", return_value="/usr/bin/ffprobe"):
        with patch("narrilume.video_probe.subprocess.run", return_value=fake_run(data)):
            with pytest.raises(ValueError, match="video stream"):
                probe_video(path)


def test_requires_ffprobe(tmp_path):
    path = tmp_path / "clip.mp4"
    path.write_bytes(b"stub")
    with patch("narrilume.video_probe.shutil.which", return_value=None):
        with pytest.raises(RuntimeError, match="ffprobe"):
            probe_video(path)
