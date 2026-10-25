# Animation production architecture

Production flow: script & IP bible → character / style reference → ordered shot manifest → ComfyUI model-specific workflow → GPU render → clip retrieval → human review → FFmpeg MP4 master.

## Responsibility boundaries
- **Narrilume**: manifest schema, workflow parameter binding, jobs, run ledger, storage paths, output assembly.
- **ComfyUI**: local model inference, node graphs, local video-generation model file loading and generated media.
- **GPU worker**: initial AWS NVIDIA A10 (24 GiB VRAM), one shot in flight.
- **Creative direction**: original scripts, continuity, character identity/style, storyboard and human approval.
- **Audio**: not included in v0.1 animation engine; optional later editorial integration via other systems.

## Runtime layout
~~~text
runs/first-short/
  state.json
  shots/
    shot_001.mp4
    shot_002.mp4
  first_short.mp4
~~~

The current state is only a simple local manifest. It does **not** provide a durable distributed queue, immutable fingerprints, process locking, job cancellation or exactly-once execution. These are next-step engineering tasks; use one orchestrator per output path for now.

## Future hierarchy
Series → Season → Episode → Sequence → Shot → Take → Clip → Master.

v0.1 implements only Project → Shot → Clip. Add more hierarchy after the first verified A10 rendering experiment.
