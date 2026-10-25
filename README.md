# Narrilume · 时光纪

**荣景文川｜RONGJING CULTURE — local AI animation production software**

Narrilume is an **animation production system**: scripts and storyboards → individual animated shots → reviewed clips → final films. Its primary backend now calls **local video models directly through Python / Hugging Face Diffusers**. **ComfyUI is NOT required** and is kept only as an opt-in legacy compatibility adapter.

No hosted GPU inference API, automatic third-party SaaS connection or checkpoint download is used by the native renderer.

## Engineering status

**v0.2 local-inference foundation** — implemented code, not yet validated on AWS A10. GPU weights and production video clips are never committed to Git.

Core capabilities:
- Versioned project and shot manifests; prompts, seeds, frame counts and optional reference keyframes.
- Native Wan text-to-video / image-to-video adapter, with local-only model paths and lazy CUDA loading.
- GPU jobs sequential by default; reusable loaded pipeline per run.
- Per-shot state, input fingerprints, explicit retry for failed/interrupted work, atomic video output.
- FFprobe technical acceptance for real video streams before marking success.
- FFmpeg normalization and MP4 film assembly in storyboard order.
- Offline test/CI without downloading weights or requiring ComfyUI.

**First target:** single NVIDIA A10 (24 GiB VRAM); actual model fit, latency and quality must be measured. Start with Wan2.2 TI2V 5B or a checkpoint compatible with the chosen Diffusers backend.

## Install

Python >=3.10, FFmpeg/FFprobe for video output. Install the base package anywhere:

~~~bash
git clone https://github.com/huliye24/narrilume.git
cd narrilume
python -m pip install -e .
narrilume --help
~~~

On the GPU host, install a CUDA-compatible PyTorch build appropriate for the driver, then the optional Wan dependencies:

~~~bash
python -m pip install -e '.[wan]'
~~~

Download a **Diffusers-formatted** checkpoint separately to a local disk path. Review model license terms, provenance and deployment resource requirements first. The native renderer strictly checks for a local directory with 'model_index.json' and never auto-downloads a model.

## Generate your first short film (no ComfyUI)

Edit the absolute local path and checkpoint revision in 'examples/first-short/native-model.example.json'. The two-shot example is text-to-video and declares frames=81, 832x480, 16 fps.

~~~bash
# Does not load models or use a GPU
narrilume validate examples/first-short/project.json \
  --model examples/first-short/native-model.example.json

narrilume plan examples/first-short/project.json \
  --model examples/first-short/native-model.example.json

# On the GPU host with weights and FFmpeg/FFprobe installed
narrilume render examples/first-short/project.json \
  --model examples/first-short/native-model.example.json \
  --output runs/first-short

narrilume status --output runs/first-short
narrilume assemble examples/first-short/project.json --output runs/first-short
~~~

Output is 'runs/first-short/first_short.mp4'. Rendering saves each clip separately and skips previously validated, unchanged clips. If a process crashes while generating a clip, inspect state and manually choose '--retry-failed'. This is **at-least-once** rendering, not a distributed exactly-once queue.

For image-guided animation, choose '"backend": "wan-i2v"' with a matching **local I2V-compatible** Diffusers checkpoint and a shot '"reference_image": "local-image.png"'. A T2V-only checkpoint does not become I2V just by changing the config flag. Compatibility must be verified per model; local asset files may not escape the project folder.

## Native model contract

See docs/NATIVE_INFERENCE.md for backend configuration, A10 sizing, supported model types, dependencies and licensing. Never assume a model checkpoint is small enough for one A10; enable CPU offload and benchmark an actual short clip. The config's 'revision' identifies the exact weights you installed; **update it when weights change** so completed outputs are invalidated correctly.

Other useful sources: Wan2.2, Hugging Face Diffusers, PyTorch, Accelerate, DiffSynth-Studio and LTX-Video (future backend candidate). We integrate through documented Python APIs; we do **not** copy their source files or weights into our Git repository.

## Production scope

Series → Episodes → Sequences → Shots → Takes → approved clips → final master is the long-term shape. v0.2 implements Project → Shots → Clips plus reproducible shot state. UI, multiple GPU workers, character/style approval and industrial scheduler are later milestones.

The **ComfyUI adapter remains available only through 'comfy-validate', 'comfy-health', and 'comfy-render'** for any legacy runs. Never share a run directory across native and ComfyUI execution. Main CLI commands use local inference.

Software: GPL-3.0-only. Model checkpoints and third-party creative assets have separate license terms; check commercial terms independently.

**Narrilume / 时光纪 — a Rongjing Culture project.**
