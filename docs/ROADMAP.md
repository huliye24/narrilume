# Native-first animation production roadmap

## v0.2 now
- [x] Keep project/shot JSON and MP4 assembly.
- [x] Native Python Wan T2V/I2V adapter with offline local path.
- [x] CPU-offload option, one GPU process, sequential jobs.
- [x] Model configuration + per-shot input signature.
- [x] FFprobe technical acceptance + explicit retries.
- [x] Offline tests and native-first CLI commands.
- [ ] GPU end-to-end A10 validation and actual human quality review.

## M1: Real local inference
- [ ] Install a CUDA-compatible PyTorch + Diffusers environment on an A10 instance.
- [ ] Download a licensed, verified Diffusers checkpoint and record immutable revision/size.
- [ ] Confirm one 81-frame MP4 and record memory, time, and source provenance.
- [ ] Render two scenes and compose a playable film.
- [ ] Determine whether the A10 is adequate or whether quantization/alternative model is necessary.

## M2: Reliability
- [ ] Exclusive local process lock and recoverable worker lease.
- [ ] Verify checkpoint SHA-256 manifest; record software/CUDA versions.
- [ ] Preserve historical take versions; never overwrite an approved clip.
- [ ] Full-frame decode and automatic output QC.
- [ ] GPU resource telemetry, render logs, robust OOM handling.
- [ ] Character/style bibles and human acceptance records.

## M3: Scalable studio
- [ ] Pluggable LTX / DiffSynth adapter after independent validation.
- [ ] Series → episode → sequence → shot → take hierarchy.
- [ ] Asset catalog, licensing and reference permission tracking.
- [ ] Multi-GPU scheduling and job isolation.
- [ ] Approval UI and archival/release packages.

Rule: ship usable animation seconds and recoverable jobs; don't import entire GitHub codebases by default.
