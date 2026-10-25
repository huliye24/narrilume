# Legacy ComfyUI compatibility (not required)

ComfyUI is no longer part of Narrilume's required runtime. **Use docs/NATIVE_INFERENCE.md for all new animation production.**

The previous adapter remains available for existing exported ComfyUI workflows via:

- 'narrilume comfy-validate PROJECT --workflow graph.json --bindings bindings.json'
- 'narrilume comfy-health'
- 'narrilume comfy-render PROJECT --workflow graph.json --bindings bindings.json --output runs/legacy'

These legacy commands do not affect the native renderer. Do not reuse a native run directory for ComfyUI. Avoid publicly exposing an unauthenticated ComfyUI server.

The default 'narrilume render' command uses local model weights through Diffusers directly.
