import pytest

from narrilume.comfy import ComfyClient, ComfyError, find_video_output


def test_video_saved_under_gifs_is_accepted():
    artifact = find_video_output(
        {
            "outputs": {
                "25": {
                    "gifs": [
                        {"filename": "scene.mp4", "subfolder": "clips", "type": "output"}
                    ]
                }
            }
        }
    )
    assert artifact == {
        "filename": "scene.mp4",
        "subfolder": "clips",
        "type": "output",
    }


def test_still_output_is_not_valid_animation():
    with pytest.raises(ComfyError, match="No saved video"):
        find_video_output(
            {"outputs": {"9": {"images": [{"filename": "still.png"}]}}}
        )


@pytest.mark.parametrize(
    "url",
    ["localhost:8188", "file:///tmp/workflow", "http://u:p@localhost:8188"],
)
def test_rejects_unsafe_comfy_url(url):
    with pytest.raises(ValueError):
        ComfyClient(url)
