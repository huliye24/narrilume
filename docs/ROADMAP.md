# Narrow development milestones

## M0 — first code foundation
- [x] Python project/shot data schema
- [x] ComfyUI API workflow and explicit per-node binding adapter
- [x] Sequential dispatch, prompt IDs, local state and output retrieval
- [x] Optional image-to-video reference image upload
- [x] FFmpeg video normalization and MP4 concatenation
- [ ] Local hardware acceptance

## M1 — first GPU validation
- [ ] Install verified local video model on AWS A10
- [ ] Export real ComfyUI API-format workflow with saved video output
- [ ] Render two shots to files and produce playable MP4
- [ ] Stop/restart render and validate recovery
- [ ] Record VRAM, time per accepted second and creative quality

## M2 — industrial reliability
- [ ] Content hashes / invalidation of changed shots or model workflow
- [ ] Explicit retry and in-flight duplicate submission controls
- [ ] Immutable provenance: checkpoint, source art, nodes, parameters
- [ ] File locking, schema migrations and corruption recovery
- [ ] Human shot approval / retake history and automated QC
- [ ] GPU telemetry and standardized experiment reports

## M3 — studio layer
- [ ] Series / episode / scene hierarchy and character bible
- [ ] First-last-frame and controlled motion model adapters
- [ ] Multi-worker GPU scheduling and capacity budgets
- [ ] Review UI / material library / release packages

We prioritize usable animation output and reproducibility over expanding the surface area.
