# Local ComfyUI + AWS A10 deployment

We keep ComfyUI and model weights separate from Narrilume. This prevents the application from depending on one video checkpoint and avoids adding multi-gigabyte binaries to GitHub.

Official resources:
- https://github.com/Comfy-Org/ComfyUI
- https://docs.comfy.org/development/comfyui-server/comms_routes
- https://docs.comfy.org/tutorials/video/wan/wan2_2
- https://huggingface.co/Comfy-Org/Wan-2.2

## Starting model candidate

Wan2.2 TI2V **5B** is a candidate for initial text-to-video and image-to-video experiments on a single 24 GiB A10. This is not a guarantee of fitting every workflow or of achieving a particular generation speed. Start with small resolution/frame count, monitor peak VRAM, then increase. Larger 14B pipelines may need quantization/offloading or larger GPUs. Follow the official video templates for exact node versions, model files and folder locations.

**Licensing:** check each model checkpoint, training/source asset and custom node's terms before commercial use. Narrilume GPL v3 does not automatically license the video model or grant rights to reference media.

## Host checklist
1. Provision a suitable GPU EC2 instance and encrypted EBS, then verify NVIDIA driver, PyTorch and 'nvidia-smi'.
2. Install ComfyUI according to its official documentation, including compatible PyTorch CUDA packages.
3. Obtain official/verified local video model weights and load the model's official ComfyUI video template.
4. Launch ComfyUI from its repository directory:

~~~bash
python main.py --listen 127.0.0.1 --port 8188
~~~

5. Access from a local machine with SSH tunneling:

~~~bash
ssh -N -L 8188:127.0.0.1:8188 YOUR_SSH_USER@YOUR_EC2_HOST
~~~

6. Run 'narrilume health'; export an actual **API-format JSON video workflow** with a saved MP4/WebM/MOV/MKV output node; configure bindings matching its real node IDs.
7. Validate a two-shot example before consuming substantial GPU time.

Never expose ComfyUI port 8188 without authentication on the public Internet.

## Acceptance measurements
Record actual ComfyUI revision, node versions, checkpoint names/hashes, driver/CUDA/PyTorch, peak VRAM, GPU minutes per accepted animation second, rejected shots and motion/identity artifacts.

Stopping a cloud instance does not necessarily stop charges for EBS and other persistent resources.
