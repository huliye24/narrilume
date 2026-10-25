# Animation studio protocol 0.1

1. **Story**: original narrative, episode intent, emotional change; human editorial approval.
2. **Design**: character bible, environment/style bible, keyframes and reference material rights.
3. **Storyboard**: shot IDs, ordered actions, camera intent, movement and cut structure.
4. **Render**: deterministic seed + prompt + negative prompt + frame count + FPS/resolution + reference keyframe mapped into a local video-model ComfyUI API workflow.
5. **Review**: check coherent motion, no flicker, consistent characters, stable clothing/anatomy, correct camera, no unrequested subtitles or watermark.
6. **Retake**: edit shot input explicitly and preserve revision history once take history is implemented.
7. **Master**: FFmpeg normalizes each shot to the project's fps/resolution then concatenates into video-only MP4.
8. **Archive**: project definition, ComfyUI workflow version, model license/checkpoint revision, prompt IDs, output files and reviewer decision.

Only the basic shot/project source, prompt IDs, output paths and errors are captured in the v0.1 code. Full immutable provenance, review records and revision history are future work.

Primary KPI: **human-approved seconds of animation per GPU-hour and reviewer-hour**. Track acceptance rate, character/style continuity and GPU cost per accepted second, rather than counts of generated frames.

The engine is for animation, not standalone images. Reference images may be inputs, but a saved animation clip must be a video artifact. Human review is required before claiming quality, rights or suitability for publication.
