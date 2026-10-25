# Engineering instructions for Codex and other development agents

Narrilume produces animation using ComfyUI and local video models. It is NOT an image-generator product, music platform, LLM chatbot, quant platform, nor a general video editing app.

## Architecture constraints
1. Narrilume orchestrates jobs; the local ComfyUI service executes video-model inference.
2. Always use actual API-format ComfyUI workflow exports and explicit node bindings, never hardcode one checkpoint's node IDs.
3. Deliverables are **video clips**, never still-image-only outputs.
4. One AWS NVIDIA A10 GPU, one sequential shot worker as initial target.
5. Record prompt IDs, parameters, failures and output locations for recovery and later audit.
6. Never commit checkpoint weights, credentials, private reference images or generated movies.
7. Bind ComfyUI only to loopback/VPC or through a secured reverse proxy; no public unauthenticated port 8188.
8. Keep GPU/integration testing separate from CPU-only contract tests. Do not claim a full run before GPU acceptance.

## Engineering workflow
- Split work into one small, reviewable 15–30-minute task at a time.
- Each task needs scope, acceptance criteria, tests and a deliverable.
- Prefer small PRs over huge unrelated changes.
- Update docs and tests when changing a manifest, workflow binding or output contract.
- Keep model versions, licensing and source provenance visible.
- No unrequested SaaS dependencies; prioritize creative quality and accepted animation seconds.

## Initial GPU acceptance
Run two shots with an actual local video model; confirm video retrieval and assembled MP4, stop/restart rendering, check rerun behavior, measure runtime and VRAM, and obtain human review of identity/motion consistency.
