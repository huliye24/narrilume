# Native video inference: no ComfyUI

Narrilume's default engine executes model inference directly in the Python process with PyTorch, Diffusers and optional Accelerate CPU offload. ComfyUI is not installed, called or required in the native production path.

## Upstream building blocks (link rather than vendor)
| Project | Purpose | Repository | Integration |
|---|---|---|---|
| PyTorch | CUDA tensors, random generator and inference | https://github.com/pytorch/pytorch | Python runtime |
| Hugging Face Diffusers | Wan T2V/I2V pipeline and video export | https://github.com/huggingface/diffusers | Primary native adapter |
| Hugging Face Accelerate | Model CPU/GPU offload for constrained VRAM | https://github.com/huggingface/accelerate | Optional GPU package |
| Wan2.2 | Original Wan video model architecture and checkpoints | https://github.com/Wan-Video/Wan2.2 | Model weights NOT vendored |
| Hugging Face Hub | Model snapshot download/metadata, separate offline provisioning step | https://github.com/huggingface/huggingface_hub | Future controlled model installer |
| LTX-Video / LTX-2 | Alternative temporal/video generation models | https://github.com/Lightricks/LTX-Video and https://github.com/Lightricks/LTX-2 | Research candidate, NOT an implemented adapter |
| DiffSynth-Studio | Multi-model local inference, LoRA workflows | https://github.com/modelscope/DiffSynth-Studio | Research candidate, NOT bundled |
| FFmpeg | Clip inspection, normalization, cut assembly | https://github.com/FFmpeg/FFmpeg | External command, not bundled |

Check model **weights** licenses, commercial rights, custom node/runtime dependencies and each asset separately. Software code and model checkpoints can have different legal terms. No copied upstream code is added to the repository.

## A10 first iteration

A10 has 24 GiB VRAM. Wan2.2 TI2V 5B Diffusers checkpoint is larger than 24 GiB in total; enable CPU offload and ensure host RAM and EBS are adequate. **No guarantee of fit or speed** until the real AWS machine completes its acceptance trial. Avoid parallel inference in v0.2.

1. Confirm GPU, driver, system RAM, disk availability using 'nvidia-smi' and the instance console.
2. Create a CUDA-compatible Python environment and install '.[wan]'.
3. Download the Diffusers-formatted model snapshot from a verified publisher to the instance storage **as a separate, intentional provisioning operation** (e.g. using Hugging Face Hub snapshot_download into a chosen local path).
4. Write a local 'model.json' pointing at that on-disk directory and set 'revision' to the exact immutable snapshot commit hash.
5. Start with 832x480, 81 frames, 16 fps and a single short shot. Use 'narrilume plan' without GPU to check the parameters.
6. Run 'narrilume render ... --model ... --output ...'. Watch memory and OOMs. Check resulting state.json and ffprobe results.
7. Compare two adjacent clips, review flicker, motion consistency and character integrity. Then assemble the film.

The Python backend picks 'WanPipeline' for 'wan-t2v' and 'WanImageToVideoPipeline' for 'wan-i2v'. The selected local checkpoint **must** support that pipeline; neither is interchangeable with a ComfyUI-only checkpoint format. 'wan-i2v' requires a local reference image relative to the project manifest.

## Explicit JSON contract

~~~json
{
  "schema_version": "0.1",
  "backend": "wan-t2v",
  "model_path": "/mnt/models/wan-2.2-ti2v-5b-diffusers",
  "revision": "<verified immutable checkpoint commit hash>",
  "dtype": "bfloat16",
  "cpu_offload": true,
  "steps": 30,
  "guidance_scale": 5.0
}
~~~

The native engine insists on a local model directory with model_index.json and invokes 'from_pretrained(..., local_files_only=True)'. It does not download assets, and it does not provide a remote inference API. Revisions are user-supplied; the backend does not currently compute hashes of all multi-gigabyte checkpoint files. Pin versions and review supply-chain provenance before production.

For Wan, fps/resolution are output constraints, frames follow '4*k+1' (81, 49, etc.), and current project dimensions must be multiples of 32. Validate before loading the model.

## Failure semantics

State is saved to 'output/state.json'; single worker only. Every shot signature includes project settings, prompt, seed, reference-image SHA-256 and model configuration/revision. Previously finished unchanged files are reused; changed inputs are regenerated.

A crash or KeyboardInterrupt leaves a shot marked 'running'; an error marks it 'failed'. An operator reviews and uses '--retry-failed' to resubmit. Since we cannot checkpoint in-progress diffusion steps yet, retries start a fresh GPU render. The ledger and artifacts are not yet atomic transactions across hosts; a distributed queue and take-history versioning are future work.

FFprobe validates metadata and that a video stream is present. **It does not guarantee aesthetic consistency or full-frame decode.** Review every clip for animation suitability.

## Future engine plugins

Keep interfaces small: input project/shot plus local immutable model specification; output video file and reported technical metadata. New adapters (LTX, DiffSynth, native Wan repo generation script) must be optional, tested independently and not interfere with the default GPU environment.

Do not put all open-source projects into requirements.txt at once: CUDA/PyTorch/Transformer versions can conflict across ecosystems.
