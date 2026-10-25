# Narrilume · 时光纪

**Rongjing Culture | 荣景文川 — AI Animation Production System**

Narrilume is a **local-first animation production orchestrator**, based on ComfyUI and locally deployed video models. It takes ordered storyboard shots, sends them to a GPU video workflow, retrieves the resulting animation clips and produces one MP4 film.

This repository does not implement a general image-generation product, chatbot, music generator or video editor. ComfyUI remains the inference engine; Narrilume manages animation production.

**Current status: v0.1 foundation**. Code has been committed, but a working GPU model, verified ComfyUI video workflow, deployment and hardware acceptance are not bundled.

## Pipeline

Story & character/style bible → Shot manifest → ComfyUI API workflow → local GPU generation → animation clips → review / retakes → MP4 master & production ledger.

One shot runs at a time on the initial AWS NVIDIA A10 GPU. Model weights and outputs are never committed to GitHub.

## Install

Python 3.10+, ComfyUI installed separately and FFmpeg for film assembly.

~~~bash
git clone https://github.com/huliye24/narrilume
cd narrilume
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
narrilume --help
~~~

Windows PowerShell activation: '.venv\Scripts\Activate.ps1'.

## First animation

1. Install ComfyUI, a compatible local **video-generation** model and a ComfyUI workflow with a **saved video output**. See docs/COMFYUI_SETUP.md.
2. Export ComfyUI workflow JSON in **API format** (not the normal editor workflow format).
3. Copy and modify examples/first-short/bindings.example.json to point at the exact IDs and input names in YOUR exported workflow. The example numbers are illustrative.
4. Edit examples/first-short/project.json (a two-shot paper-boat animation).
5. Validate, run, resume and assemble:

~~~bash
narrilume validate examples/first-short/project.json \
  --workflow /path/to/video.api.json \
  --bindings /path/to/bindings.json

narrilume health --comfy-url http://127.0.0.1:8188

narrilume render examples/first-short/project.json \
  --workflow /path/to/video.api.json \
  --bindings /path/to/bindings.json \
  --output runs/first-short

narrilume status --output runs/first-short
narrilume assemble examples/first-short/project.json --output runs/first-short
~~~

Generated file: 'runs/first-short/first_short.mp4'. Render metadata, ComfyUI prompt IDs and shot clips are saved under the same run directory. Restart the render command to reuse completed shots.

## Workflow bindings

A bindings file maps named fields to the exact node and input in your video-model ComfyUI API workflow. Example:

~~~json
{
  "positive_prompt": {"node": "6", "input": "text"},
  "seed": {"node": "3", "input": "seed"},
  "frames": {"node": "15", "input": "length"}
}
~~~

Supported keys: 'positive_prompt' (required), 'negative_prompt', 'seed', 'frames', 'fps', 'width', 'height', 'reference_image'. Unbound parameters remain as configured in the ComfyUI workflow.

'comfy_url' defaults to 'http://127.0.0.1:8188' (also configurable with 'NARRILUME_COMFY_URL'). Uses the official ComfyUI HTTP API. No third-party cloud inference API is silently invoked.

Read docs/ARCHITECTURE.md, docs/ANIMATION_PROTOCOL.md, docs/ROADMAP.md and AGENTS.md before extending the system.

## Current limits

The v0.1 ledger is local JSON, for **one orchestrator process per output directory**. There is no full model-checkpoint lockfile, approval UI, multi-GPU scheduling, clip fingerprint invalidation or guaranteed exactly-once dispatch yet. Do not claim that this version is a production-ready animation studio until A10 GPU acceptance has passed.

Software: GNU GPL v3, see LICENSE. Model weights, assets and production outputs carry their own license terms; verify commercial permission separately.

**Narrilume / 时光纪 — a Rongjing Culture project.**
