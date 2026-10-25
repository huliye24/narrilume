"""Native Wan inference via Diffusers. No ComfyUI process or network service."""

from __future__ import annotations

from pathlib import Path

from .native_config import NativeModelConfig, inspect_local_weights
from .schema import Project, Shot, resolve_reference


class WanDiffusersBackend:
    """Load one local model and reuse it for sequential shots on a single CUDA GPU."""

    def __init__(self, config: NativeModelConfig) -> None:
        inspect_local_weights(config)
        try:
            import torch
            from diffusers import WanImageToVideoPipeline, WanPipeline
        except ImportError as exc:
            raise RuntimeError(
                "Native Wan dependencies are missing. Install on the GPU host using "
                "pip install -e '.[wan]' and a compatible CUDA-enabled PyTorch."
            ) from exc
        if not torch.cuda.is_available():
            raise RuntimeError("Native Wan backend requires a CUDA GPU; no CPU fallback")
        self.torch = torch
        self.config = config
        dtype = getattr(torch, config.dtype)
        cls = WanPipeline if config.backend == "wan-t2v" else WanImageToVideoPipeline
        # The model source is always a local directory. No Hugging Face Hub request.
        self.pipeline = cls.from_pretrained(
            str(config.model_path), dtype=dtype, local_files_only=True
        )
        if config.cpu_offload:
            self.pipeline.enable_model_cpu_offload()
        else:
            self.pipeline.to("cuda")

    def generate(self, project: Project, shot: Shot, destination: Path) -> None:
        from diffusers.utils import export_to_video, load_image

        kwargs = {
            "prompt": shot.prompt,
            "negative_prompt": shot.negative_prompt,
            "height": project.height,
            "width": project.width,
            "num_frames": shot.frames,
            "num_inference_steps": self.config.steps,
            "guidance_scale": self.config.guidance_scale,
            "generator": self.torch.Generator(device="cpu").manual_seed(shot.seed),
        }
        reference = resolve_reference(project, shot)
        if reference is not None:
            if self.config.backend != "wan-i2v":
                raise ValueError("reference images require wan-i2v mode")
            kwargs["image"] = load_image(str(reference))
        destination.parent.mkdir(parents=True, exist_ok=True)
        # Importantly this is not a remotely hosted inference endpoint.
        with self.torch.inference_mode():
            frames = self.pipeline(**kwargs).frames[0]
        export_to_video(frames, str(destination), fps=project.fps)
