# Narrilume engineering contract (荣景文川)

Narrilume makes animation through locally deployed video diffusion models. **No ComfyUI is required in the default engine.** The former HTTP adapter is legacy only (comfy-* commands). Do not add a mandatory ComfyUI dependency or bring back workflow-node ID binding into native rendering.

## Decisions
1. The primary engine is **direct Python / PyTorch / Diffusers** inference with local model directories. No surprise checkpoint downloads or remote SaaS inference.
2. Start with Wan T2V 5B in a dedicated AWS A10 GPU environment. A 24 GiB card does not guarantee it fits, so benchmark memory and host RAM.
3. Keep the application model-agnostic via standalone adapters. Treat new frameworks (LTX, DiffSynth) as separate optional plugins; never lump their dependencies into the base package.
4. One sequential worker and one writer per output directory. Store per-shot seeds, prompt, input signatures, model revision, video stream stats and errors.
5. All completed outputs must be actual videos verified with FFprobe; no still-image-only final deliverables.
6. No weights, video files, sensitive references, personal data or credentials in Git.
7. Keep character identity, motion coherence, camera continuity and approval a separate human quality gate.
8. All business footage and model weights require license/usage review.
9. Protect GPU time: validate model/shot configs first, require explicit retries, never rerender unchanged accepted shots.
10. Current 'state.json' is not a distributed queue and does not provide a process lock. Never run two renderers concurrently in the same folder.

## Microtask protocol
- Split tasks into 15–30 minute reviewable packages with an explicit, testable acceptance criterion.
- Separate offline unit tests (CI) from real local GPU acceptance.
- Avoid UI/HTTP server complexity until a genuine first animation passes hardware acceptance.
- Document version constraints and exact tested model checkpoint in the GPU acceptance report.
- Update docs and tests with every change to the engine contract.
- For every upstream project, record source link, code license, model-weight license, intended interaction and whether the backend is **implemented**, **experimental** or **planned**.

## Initial real-world acceptance
On the existing A10 host: validate model config; inspect disk/RAM; run one 81-frame text-to-video shot; ffprobe technical metadata; check clip visually; repeat for second shot; combine into MP4; collect GPU-memory, total runtime and human-approved seconds.
