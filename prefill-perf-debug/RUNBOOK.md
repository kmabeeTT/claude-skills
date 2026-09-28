# Prefill perf runbook (TT multi-chip, chunked prefill, accuracy-gated)

How to find and land prefill perf wins on a TT model without fooling yourself. Written from the Gemma4-31B
work on BH Galaxy 8x4 (Sept 2026, ~-35% at 256k over three PR rounds). Sections 1-4 and 6-7 are model-agnostic;
section 5 is a lever catalogue that grows with every model. Tools: `tools/` next to this file.

## TL;DR
- **Two numbers per chunk size:** the per-chunk floor (TTFT) and the prefix slope (long context). Report first
  chunk / ~100k / full context, and say which one a change moved (§1).
- **Same build, before and after**, on a tree you own, with a deterministic base. Never compare to an old doc (§2).
- **Check power first.** BH Galaxy prefill sits at the TDP cap, so time follows energy: fewer FPU passes pay,
  occupancy and traffic cuts mostly don't, and stale/zero-data hacks look falsely fast (§2).
- **Gate accuracy per layer**, not on the chaotic final minimum: `cmp_pcc.py` error ratios against a same-build base,
  at the context you ship. Find which error class the model actually sees before fixing one (§3).
- **Localize before tuning:** end to end -> layer type -> op -> one knob at a time. Record nulls (§4, §5).
- **Read the lever catalogue and kernel traps before starting** so you don't repeat a measured null (§5).
- **Land cleanly:** measure on the base the PR lands on, clean commits, `/simplify`, the CI legs in §7.

## 1. The cost model: two numbers per chunk size
Chunked prefill of N chunks of size C costs `T = N*a(C) + slope(C)*N(N-1)/2`.
- `a` = the per-chunk **floor** = first-chunk time = what TTFT sees. Fixed work per chunk: matmuls, CCL, norms,
  per-layer glue. Dominates at small chunks and short prompts.
- `slope` = the **prefix term**: extra cost per chunk of history. Almost always the full-attention layers'
  SDPA (and anything that re-reads the whole KV prefix). Dominates at long context.
- Get both from one run: `tools/fit_chunks.py <perf log>` (least squares on per-chunk device times).
- Always report **first chunk / mid-context (e.g. 106k) / full context** per chunk size, and say which dominates.
  A chunk-size change trades floor for slope; a kernel change moves one of them.
- The "106k" figure must be whole chunks of the size under test, with the rounding rule stated. Rounding down
  silently drops the last partial chunk; rounding up (`ceil(tokens / C)`, what a real prompt pays) covers more
  tokens at bigger chunks (100k: 100,352 / 102,400 / 106,496 tokens at 2048 / 4096 / 8192). Say "13 chunks" or
  compare an equal token count (a common multiple, e.g. 98,304).
- **Legal chunk sizes follow the parallelism.** Each device's slab (chunk / CP) must split into whole tiles for every
  sharding applied to it. With sequence parallelism over TP, the chunk must be a multiple of CP x TP x 32 (Gemma4:
  1024). Sliding layers want q-chunk multiples per device (Gemma4: 128). "Occupancy-optimal" sizes such as 3328 or
  6912 need padding or a fallback path before they can run.
- **Small chunks can add floor work that big chunks don't have.** Anything sized by a fixed window rather than the
  chunk (sliding-window halo: `ceil(halo / slab)` predecessor hops) grows as the per-device slab shrinks. Gemma4
  W1024 at CP8: 4 hops at chunk 2048, 1 at 8192. Price these separately; they are why the floor stops scaling
  down with chunk size.

## 2. Measurement hygiene (each of these cost a session once)
Baselines and provenance:
- **Same build, before and after.** Rebuild the baseline yourself; never compare to a number from an old doc.
  Per-op numbers need the same renderer too (tt-perf-report version).
- **Prove what you ran.** Check `git -C $TT_METAL_HOME log -1` and `git status` of the tree the run used, and grep
  the log for the config that matters (`Fabric Initialized with config FabricConfig::...`, chunk size). A shared tree
  that another session committed WIP into produced a "PCC win" that was their change. Run A/B in trees you own.
- **Prove the base is deterministic before reading small diffs**: run base twice (bit-identical here); then every
  4th-decimal difference is real.

Power (BH Galaxy runs power-capped):
- Sample `tt-smi -s` during a long run (`tools/smi_sample.sh`): per-chip power vs `tdp_limit`, AICLK vs `asic_fmax`. The
  full traced run sits at the 115 W cap with AICLK ~1100-1250 of 1350. Under a power cap:
  - time follows **energy**, not critical path; removing idle core-time (occupancy, finer splits) barely helps (a
    40% idle-time cut gave 2%); removing energy-cheap work (DMA traffic) gains nothing;
  - cutting FPU passes (fidelity) or operand toggles pays in full;
  - **data values matter**: zeros/stale data draw less power, so a hack that leaves a buffer stale or zero looks
    faster for power reasons. Never credit a lever from such a hack; build the real version (it may gain nothing,
    as the "append-only gather" did).
- **Isolated-layer benchmarks understate energy wins** (one short burst barely throttles) and overstate occupancy
  wins. Use them to localize, the full traced demo to decide.

Source tree and build:
- **Kernels JIT at run start from the source tree.** Don't edit, checkout or rebase in the tree a queued run uses;
  edit in a separate worktree and switch the run tree with `git checkout --detach`. Purge the op's JIT cache after
  branch switches (named compile-time args break otherwise); the JIT hash ignores opt_level, and may not see a
  header only kernels include (point `TT_METAL_CACHE` at a fresh directory for the validation run).
- `ninja <target>` does not install: build with `--target install`, or Python loads the stale .so.
- When another session owns the tree, commit with plumbing (a temporary `GIT_INDEX_FILE`, `read-tree` /
  `update-index` / `commit-tree` / `update-ref`) and check `git worktree list` before moving a branch ref.

Devices and queues:
- **One device job at a time**, queued in a script. Bash reads a small running script up front, so appending steps
  does nothing: write a new script. A killed queue script leaves its pytest running; kill by PID, not `pkill -f`
  (it matches the tool's own wrapper).
- **A hard kill or timeout leaves 32 chip locks naming a dead PID** (`kill -0` gives ESRCH; another user's live
  process gives EPERM under hidepid) and AICLK stuck high. Reset (`tt-smi -glx_reset`) and remove the locks
  (`waitchips` in `lib.sh` does both). A queue that waits for "0/32 claimed" *before* resetting deadlocks on this:
  reset first when the holder is dead.
- Shared fixed-name `/dev/shm` files (e.g. `tt_prefill_layer_completion_ring_<rank>`) left by another user's
  interrupted run fail your startup with `PermissionError`; override the name via its env var (and allowlist it if
  the test filters env).
- Env vars reach in-process ops, but a service's worker subprocess may strip them (check the test's env filter).
- A one-off host `Bus error` in `fetch_queue_write` right after model load was transient: retry once before debugging.

## 3. The accuracy gate: judge changes by per-layer error ratio
Reading the gate:
- Gemma4's gate is the 256k KV-cache PCC, min per-head >= 0.91. The final-layer minimum is chaotic: any arithmetic
  change moves it by ~+-0.001-0.01, non-additively. A base with 0.001 of margin will "fail" noise.
- **Report overall PCC and relative RMSE next to the gate.** Reviewers compare overall PCC (~0.973) with main;
  quoting only the min per-head value (~0.91) reads as a huge regression. Put all three in one line or table.
- **Validate at the context you ship.** Short-context PCC (8k) passed a change that failed at 256k, and at 8k base
  itself fails the gate; small per-layer drifts only compound past the gate at long context.
- So compare **per layer** against a same-build base: `tools/cmp_pcc.py base.runner.log new.runner.log` prints
  (1 - PCC) ratios. ~1.00-1.05 everywhere = neutral; a systematic 1.1-1.3 = a real, small cost; 3x+ at early
  layers = broken (e.g. bfp8 activations: 40x at layer 2). Look where error enters: the layer right after the
  first changed layer (e.g. L6 after global layer 5).

Attributing error:
- **When a stack of changes fails the gate, run each change alone** at the shipped context against the same base
  and read early (layers 0-20) and deep error ratios separately. Gemma4: norm 1.00 / 1.008, MLP config 1.00 / 1.016
  (the whole drift), attention 0.91 / 0.99. Early better + deep worse points at accumulation, not op precision.
- **Find which error class the model actually sees before fixing one.** Split an op's error into a per-row scale
  and the rest (least-squares scale per row, then the residual). If the model normalizes each token right after
  the op (Gemma4: post_attention_layernorm on the attention output), per-row scale errors are mostly removed and an
  op-level fix of a scale error buys nothing. Test cheaply: multiply the op output by a constant (Gemma4: x1.029
  moved per-layer error by x1.00).
- A fix that is correct at op level but worse in the model is a model-path bug until shown otherwise; op tests
  rarely cover the model's exact tile shapes (e.g. a 3-tile Q chunk takes a remainder path).
  Reproduce it at op level with the model's exact call (shape, dtypes, KV-pad rotation, metadata), and compare against
  the unmodified path, not against the same change on another path (both can be wrong the same way).
- **A regression test must fail without the fix.** Revert the fix locally and run it; a smaller shape silently did not
  reproduce the chunk-0 bug here.
- **Changes that only move data should be bit-identical.** A new transport (multicast, bigger packets, a different
  exchange plan) must reproduce the base PCC to every printed digit on the same fabric; anything else is a delivery
  bug (wrong block, missed arrival), not noise. Measure on the fabric you ship: a fabric/topology change itself
  reorders the collective's reduction and moves PCC in the 4th decimal, both ways.

Numerics knobs:
- **An explicit `program_config` or `core_grid` silently changes matmul numerics.** `ttnn.linear` defaults to HiFi2
  only with neither (bf16 x bfp8 inputs); with either it is LoFi, bf16 dest, `packer_l1_acc` on
  (`matmul_device_operation.cpp`). A "blocking only" change is therefore also a fidelity change: set the compute
  kernel config explicitly and say so in the PR.
- **Separate the three knobs** (fidelity, fp32 dest, packer_l1) and vary one at a time; don't infer from a combined
  flag. Gemma4: the MLP drift was bf16 accumulation across K blocks (HiFi2 + bf16 made it worse, LoFi + fp32 fixed
  it); attention needed HiFi2 AND fp32 (LoFi + fp32 still drifted). The "fp32 cost" was mostly HiFi2.
- Probe fidelity upward too: if raising a component to HiFi4 does not move per-layer error, that component is not
  what limits the gate.

Know what limits the base:
- For long-context attention on the streaming SDPA path, the bf16 running output and denominator (re-rounded every K
  chunk) and 16-bit DST accumulation of QK^T dominate; a K split helps because each partial accumulates fewer steps.
  `tools/sdpa_accum_sim*.py` reproduce these on CPU in minutes - use them before kernel work.
- Op tests with zero-mean random V hide output-accumulator saturation (real V has a mean direction, so the output
  grows coherently and saturates like the denominator); simulate and test with V = mean + noise.
- Accuracy headroom is a resource: spend it on the biggest energy lever first.

## 4. The funnel (how to go from "slow" to a lever)
1. **Level 0, end to end:** perf at 3-4 chunk sizes; fit floor/slope; PCC at the chunk sizes you ship.
2. **Level 1, which layers:** isolated-layer benchmark per layer type at early and late chunks (depth 0 vs D).
   The difference is the prefix term; depth 0 is the floor.
3. **Level 2, which ops:** Tracy capture at the same two depths, `tt-perf-report`, subtract. Watch for ops that
   don't scale with chunk width (floor) or grow with depth (slope). Captures are ~15 GB each: keep the CSV, delete
   the dump (per-user /data quota).
   - **An unexplained residual (`a` minus summed isolated-layer ops) is a subtraction, not a measurement.** Build the
     model with L = 6 / 12 / 30 / 60 layers from the warm cache and fit `a(L) = c + k*L`: `c` is what really sits
     outside the layer loop (Gemma4: 0.5 ms, not the 11 ms the subtraction claimed; ops just ran slower in-model).
4. **Level 3, what bounds each op:** one knob at a time, measured end to end on the demo. Record every result,
   including nulls, in the lever catalogue. Quick bound checks first:
   - **Attention occupancy:** count (head, Q chunk) work units per device against compute cores (~110 on BH). If
     units < cores and each unit walks the whole prefix, the slope is occupancy-bound. Taller Q chunks don't fix
     this when per-token cost is sublinear in Q height (they only cut units); split the K range across cores.
   - **Matmul floor:** weight bytes per device / achievable DRAM bandwidth (~420 GB/s per BH chip, calibrated with
     a DRAM-sharded M = 32 matmul) against the measured matmul time. At small chunks the weights stream once per
     chunk whatever the chunk size, so the gap to that floor is the ceiling on config work.
   - **Matmul grid ceiling:** a 2D-mcast config can use at most `M / 32 / per_core_M` grid rows, so at short M most of
     the grid idles by construction (Gemma4 chunk 2048: M = 256 = 8 tile rows -> 96 of 120 cores). Once every shape
     sits there, more gain needs a different decomposition (split-K, 1D over N), not another `in0_block_w` sweep.
   - **CCL share:** sum the collective ops per chunk. If it is large and the ops auto-tune links/topology, only
     overlap/fusion with compute will move it.
   - **Is the requested topology the one running?** Compare the fabric the mesh is opened with (`FabricConfig` in
     the test factory / runner manifest; the "Fabric Initialized" log line) with the topology the collectives ask
     for. `get_usable_topology` silently downgrades Ring to Linear on a line fabric (`FABRIC_1D` has no wrap link;
     `FABRIC_1D_RING` does). The one-run proof: forcing linear gives identical timings to the "Ring" default. Then
     sweep fabric config x sync/async once per model (2D torus needs a torus mesh descriptor or it hangs at bring-up).
   - **Link-bound or payload-bound?** For a point-to-point exchange, count payload crossings per link direction.
     One unicast per hop to k predecessors crosses k(k+1)/2 slabs on the first link; a line multicast crosses k.
     If time across configs follows the crossing ratio rather than the payload ratio, it is link-bound: cut
     crossings (multicast, both directions, all links) before tuning kernels.

Budget: a full-demo perf run is ~3 min, a PCC run ~10 min, a rebuild ~3-5 min. Plan queues accordingly.

## 5. Lever catalogue (Gemma4-31B, BH Galaxy 8x4, CP8/TP4) - measured outcomes
Worked:
- **K split for global SDPA at short Q slabs** (grid bands share a unit's K range, L1 merge): 256k at chunk 2048
  20.1 -> 14.3 s, and PCC up (fewer bf16 steps per partial). Only fits L1 at small Q chunks.
- **Sequence-parallel residual over TP** (RS/AG around each block, norms on 1/TP rows), 1D in0-mcast matmul for
  M <= 8 tiles, block-sharded RMSNorm, batched NoC in head ops, reading a packed K/V cache in place.
- **Global attention matmuls (QK^T, softmax@V) at LoFi**: -20% at 256k / -14% at 106k (chunk 8192), per-layer
  error 1.00-1.05. Sliding-window attention gains nothing from LoFi (not FPU-bound).
- **Explicit matmul blocking where ttnn's auto config underperforms** (MLP at M = 1024): -3% per chunk. Cap explicit
  configs by per-core M and fall back to the default above it: fp32 dest halves the subblock budget (8 -> 4 tiles),
  free at per-core M 1-2 but ~7 ms/chunk at 4 (Gemma4 chunk 8192), and per-core M 7 (chunk 16384) overflows L1. The
  explicit MLP config was worth -11 / -27 ms at chunk 2048 / 4096 and ~0 at 8192.
- Bigger chunks for long prompts (trades TTFT for throughput).
- **Segmented accumulation for unsplit global SDPA** (`SDPAProgramConfig.segmented_accumulation`): each ring
  iteration accumulates into a fresh sum and output, merged into a long-term state. The whole 4096-vs-8192 PCC gap was
  the K split (4096 unsplit == 8192): 8192 min per-head 0.9112 -> 0.9460 at +0.7% time. It buys attention
  projections at LoFi: 8192 2.232 -> 2.120 s at 106k (-5%), 4096 -2.4%; nothing at 2048 (DRAM-bound projections).
- **Open the fabric as FABRIC_1D_RING** (#57931): the Ring collectives were running as Linear. First chunk -6 / -10 /
  -15% at chunk 2048 / 4096 / 8192 (gain grows with all-reduce size); 256k -0.6 to -0.8 s. Sync CCL still beats
  async on the ring.
- **Multicast the multi-hop sliding halo** (#57979, on the ring): 86.6 -> 78.3 ms first chunk at chunk 2048 (4 hops),
  105.4 -> 100.6 at 4096 (2 hops), none at 8192 (1 hop). The enabler is a layout where every receiver's destination
  address is the same (block keyed by source, not by distance), so one line multicast serves all receivers;
  geometries that can't do that keep unicasts.
- **Fuller fabric packets:** fill packets to the fabric's scatter limit (`NOC_SCATTER_WRITE_MAX_CHUNKS` = 4 pages),
  not the 2 the fused scatter+atomic-inc header allows; split only the last packet (plain pages, then the signalled
  pair). ~2.4 ms per chunk at 2048, all halo exchanges.

Null or negative (don't repeat without a new reason):
- More cores for the MLP (padded N, 64 -> 88 cores) and a bigger sliding K chunk (fewer steps): both null.
- Append-only ring gather (traffic not the cost under the power cap); async CCL (slower); fewer/more TP links
  (sync CCL already uses all); exp_approx_mode; Q-chunk occupancy at chunk >= 8192 (~2%); smaller K chunk to fit a
  bigger Q chunk (slower); bfp8 activations into CCL (accuracy x40); LoFi on attention projections (x1.06-1.3
  error, only worth it with headroom); bigger K chunk for accuracy (L1).
- MLP weights at bfp4: -3.7% at 106k (chunk 4096, DRAM energy) but per-layer error x8 (PCC 0.856). Dead.
- Raising sliding SDPA / projections / global SDPA to HiFi4: PCC unchanged (none of them sets the 8192 floor).
- bf16 softmax denominator compensation alone (SFPU two-sum): fixes the op-level row-scale drift, but the model got
  worse: the output accumulator saturates too and the two saturations partly cancel, so fixing one breaks that.
  Compensating both fixes it (sim: 12% -> 0.1%), but the output needs SFPU work on every output tile (~16x),
  estimated +20-25% end to end.

Known traps in the SDPA kernel:
- The ring joint program must fit the 70,656 B kernel config buffer ("Program size (N) too large"). New compute
  code costs KB per LLK instantiation across all three TRISCs, and template args that differ by one value make a
  second copy. Reuse the kernel's existing instantiations, read the ELF sizes with `size -A` in the JIT cache, and
  build a heavy variant at O2 (`KernelDescriptor.opt_level`, ~30% smaller) before cutting features.
- `if constexpr` inside a non-template `kernel_main` does not discard the branch. A `static_assert` or constexpr
  query there fires for every config, so guard it (`static_assert(!feature || cond)`). This compile-broke unrelated
  SDPA configs in CI while every Gemma-shaped local test passed.
- Anything that changes which K chunks the reader sends must be mirrored in every compute path (the streaming path
  and the fp32 path) and in the multi-Q-chunk writer flush logic. A reader-only skip hangs until pytest times out.
- A LoFi no-MOP matmul replay image bakes in the matmul shape; reinit'ing it for a different-shaped matmul hangs.
- `MATH_FIDELITY` exists only in the math thread's JIT build; anything referencing it outside `MATH(())` breaks
  the unpack/pack builds.
- L1: circular buffers must end below the lowest live L1 tensor, not just below the L1 size; the error names the
  address.
- The chunked path masks K chunks past a query's position (-inf diag stamp) rather than skipping them, so at chunk 0
  whole later shards are fully masked. Any restart of the online softmax (a new segment, a split) must start from a
  finite running max: `exp_tile_first_column`'s range reduction turns exp(-inf - m) into garbage (~1e16), and the K
  loop never feeds it -inf.
- `binary_max_tile` / `max_block` use SFPLOADMACRO, whose state races the pack thread's exp; use a plain-SFPI max in
  any merge that follows the K loop (`TT_METAL_DISABLE_SFPLOADMACRO=1` is the one-run check).

Open:
- TP CCL (~25% of the floor at 8192) is link-bound; only overlap/fusion with matmuls would help.
- Raising the power limit (hardware/ops decision).

## 6. Running experiments (Gemma4 harness; adapt paths per model)
- `source tools/lib.sh` (settings in its header, example in `tools/README.md`): `perf <label> <chunk> [ENV=V]`,
  `pcc <label> <chunk> [ENV=V]`, `lp <label> <chunk> <idx> <global|local|both>` (isolated layer), `mkb <branch>`
  (detached checkout + build + JIT purge), `sw <branch>` (Python-only switch), `t <label> <pytest args>`,
  `waitchips` (blocks until chips are free; resets stale locks).
- Experiments go behind LOCAL env knobs on a run branch (branch = clean stack + local extras + knobs), so one build
  serves many runs; the clean stack never carries knobs.
- **Host-side planning logic gets a standalone gtest** (exchange plans, layouts, route math): it builds in seconds
  without the device. Move pure constexpr helpers out of kernel-only headers so host tests and kernels share one
  definition, and mutation-test new tests (break the formula, confirm a failure). Before testing a kernel branch,
  check the validator can reach it; unreachable cases (e.g. odd per-link page counts under a fixed K chunk) are
  not worth a test.
- Each session: keep a PROGRESS md (results, dead ends, open items) and end with a HANDOFF md for the next one.

## 7. Landing a PR
Measuring for the PR:
- **Decide on the base the PR will land on.** Another in-flight PR can change the default path you compare against:
  after #56862 gave the MLP a fast core-grid path, #57454 at chunk 8192 measured 246.6 -> 238.4 ms on old main but
  206.8 -> 200.7 on main + #56862, and the explicit MLP config there stopped paying. Run the combined branch
  (main + the PRs about to merge) with same-build base and PR arms.
- **Stacked perf PRs:** measure all four cells of a 2x2 (base / A / B / A+B) in one queued script on one base; gains
  may or may not add, so measure A+B rather than summing (fabric ring + halo multicast at 2048: -6% and -9% alone,
  -15% together; at 8192 the multicast's -2.5% on the line fabric vanished on the ring). When A merges, re-baseline
  B's description on base+A so each PR claims only its own delta.
Cleaning the branch:
- **Commits:** one per concern (op change, model change, config), each building and passing on its own. Fold every
  fix and review follow-up back into the commit it belongs to. Nothing LOCAL/DEBUG/experiment-knob survives;
  pre-commit clean.
- **Run `/simplify`** on the whole diff, apply what it finds, then fold those edits into the original commits.
- **Comments:** only where the code can't say it (a hardware constraint, a non-obvious invariant), in one or two
  short lines. No history ("previously", "we tried", "was X"): that belongs in the PR body.
- **Commit messages:** a short subject (`[component] What it does`) and a body of a few lines (the why), no numbers
  tables.
- **Fewer PRs is better:** group changes that one reviewer approves together; split only where the reviewers or the
  risk differ (op vs model).
- Then rebuild, re-run perf + PCC on the cleaned branch, and write the body per the house style.

The PR body (squash-merge uses it as the commit message):
- **Summary** = the causal chain (what the code asked for, what it got, where, the one observation that proves it),
  then "This PR does X" in one sentence. `Fixes #N` goes in the body, never the title.
- **One context line** for the measurement (model, hardware + mesh, metric, base sha, same build before and after),
  then **results as bullets**, one per config, same column order, % on the headline column. No markdown tables.
- **One sentence on the trend** (why the gain grows with chunk size or context).
- **Accuracy** with metric names and the gate (overall / RRMSE / min per-head, gate 0.91).
- **Notes for reviewers** answering their likely questions: why a metric moved, the obvious alternative and its
  measured result, what was not measured and why, interactions with other PRs, CI links pinned to a sha.
  Reference: tenstorrent/tt-metal#57931.

Validation and CI:
- **Validation scope for an op change:** model-shaped tests don't cover other models' shapes. Run the op's whole
  nightly test file (not just your parametrizations; exclude harness tests that spawn tracy, which time out
  inside a device-holding pytest), then CI Sanity, whose QB2 SDPA job covers wan2_2 / videogen / mla shapes.
- **CI legs** (workflow_dispatch on the pushed sha; check `git ls-remote` first): L2 nightly with
  `additional_test_categories=sdpa,transformers` and `run_ccl_tests=true`; Sanity; Blaze prefill with
  `test-type=<model stage>,sdpa_perf`. Record them in the PR body, RUNNING -> PASSED, and write PASSED only after
  `gh run view` shows the run completed with success, including the model leg (a run can be green except one queued
  job). A failed job with no failing step and no log blob is a runner that died: re-run failed jobs only.
- **Triage a red model-CI run against a same-base baseline run, job by job:** list jobs that fail only with the PR,
  then grep each one's first error ("Executing the custom container implementation failed" = infra; perf "outside
  band" below the floor = faster, not a regression; determinism tests are flaky across baselines). A PR branch whose
  base predates a new CI gate action fails that gate ("Can't find action.yml") until rebased.
- **A queued Galaxy leg can wait for hours.** Check the runner label (`gh api .../actions/jobs/<id>` -> `labels`)
  and how many jobs on it are queued across recent runs; a pool with nothing started for hours is an infra
  problem, not your job. Evidence while waiting: run the same test function locally on the PR branch and say so
  in the PR ("pending, passed locally").

After review:
- **Review feedback after CI passed:** push a follow-up commit rather than rewriting the tested one, validate it
  with the narrowest device test that exercises the change, and note in the body that the new tip is identical to
  the CI'd sha apart from that commit.
- **PR bodies:** a bot appends a "CI Status" section and can rewrite the body from its copy right after an edit.
  Edit from the current body (`gh pr view --json body`) and re-check a minute later.
