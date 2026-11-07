---
name: bh-glx-b08u08-box-facts
description: bh-glx-120-b08u08 - Gemma HF snapshot at /mnt/models/huggingface (not /data hf_cache); / full; good 8x4 fabric; clean host for #64697
metadata:
  type: project
---
Checked 2026-11-07. The Gemma4 HF snapshot here is `HF_HOME=/mnt/models/huggingface`; `runs_fork_1030/lib.sh` exports `/data/kmabee/hf_cache`, which lacks Gemma, so the KV test dies in ~8 s with `LocalEntryNotFoundError` (rjob re-exports HF_HOME every job: pass `env HF_HOME=... $PY` in the command). `/` (3.5 TB) sits at ~100% (two 52 GB apport core dumps of another user, 214 GB docker images, ~3 TB unreadable to non-root): set `TT_METAL_CACHE=/data/kmabee/tt_metal_cache_b08u08` for device runs. Fabric: 8x4 1D ring opens with no single-channel edges, but the first open after another user needed a `tt-smi -glx_reset` (device 27 UMD memory-barrier timeout). Never shows the #64697 halo race (16/16 clean). Related: [[bh-glx-b09u08-single-channel-links]], [[gemma4-kv-4096-host-variance-64697]].
