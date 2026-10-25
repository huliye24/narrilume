# Narrilume architecture (native-first)

## Core split

**Animation domain**
Script → character / environment reference bible → storyboard JSON → ordered shots → human shot review → MP4 master.

**Compute**
CLI / future API → validated project + native model config → local GPU inference adapter → FFprobe technical check → durable shot ledger → FFmpeg normalization / assembly.

**Backends**
- Primary: **native Wan/Diffusers** on the A10 via Python API, using a local model snapshot.
- Secondary: opt-in legacy ComfyUI HTTP adapter only for backward compatibility.
- Future: LTX / DiffSynth / native Wan command worker as independent plugins, not mandatory imports.

The model config is deliberately separate from shot/episode data. No ComfyUI graph or node ID is involved in the native path.

## Output
~~~text
runs/first-short/
  state.json                 # engine=native, status, model revision, shot signatures and ffprobe report
  shots/
    shot_001.mp4
    shot_002.mp4
  first_short.mp4
~~~

Native sequential rendering caches the pipeline per CLI execution. On restart, reloading the model is required, but already finished unchanged clips are reused. Failed and interrupted steps require operator confirmation for fresh GPU attempts. GPU weights live outside Git and the configured file path must exist on local disk.

## Limits
- Single-writer local JSON ledger: no DB, auth server, distributed queue, process lock or crash-safe checkpointed diffusion yet.
- Input signature is model-config revision + shot inputs + reference content, NOT hash of every actual model weight. Operator must bump the revision on a model change.
- FFprobe proves stream metadata presence, not full clip quality or continuity.
- 'assemble' creates silent MP4; later versions will have separate soundtrack/voice workflows.
- Series/episode/sequence/take hierarchy, approval UI and multi-GPU coordination are later milestones.

See docs/NATIVE_INFERENCE.md and docs/ROADMAP.md.
