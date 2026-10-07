## Working with Kyle (conventions)
- [Ask before opening PRs](ask-before-opening-prs.md) — never gh pr create (even draft) without asking; push branch + draft description
- [MD written for GitHub](md-writing-for-github.md) — no hard wrapping; drafted replies unquoted under a bold heading; PR descriptions use bullet results, not tables (squash commit)
- [Telegram is two-way](telegram-two-way.md) — send with runs_ringsdpa/tg_send.sh, read replies with ~/scripts/tg_read.sh; env file is /home/kmabee/dotfiles/.tt-telegram.env (pass via TELEGRAM_ENV_FILE); ask there and poll instead of stopping
- [CI status only when verified](ci-status-only-when-verified.md) — never write PASSED for a run until gh shows completed/success; check the model leg, not just the run
- [Avoid rm in run commands](avoid-rm-in-run-commands.md) — no rm -rf/rm -f cleanup in run commands; use timestamped basetemp and unique ring names
- [ALL_CAPS names for reference docs](allcaps-names-for-reference-docs.md) — working docs you reopen get ALL_CAPS; snake_case is for one-off investigation records
- [Debug-docs is the doc home](debug-docs-location.md) — one canonical copy in ~/debug-docs/<topic>/; /data/kmabee copies only as throwaways for another box
- [debug-docs: batch commits](debug-docs-batch-commits.md) — push per milestone/topic, not per tracker tweak; safe squash recipe if needed
- [106k prefill metric](prefill-106k-metric.md) — mid-context number is 13 x 8k = 106,496 tokens, label it 106k

## Boxes, shared trees and devices
- [Build host bh-glx-110-a10u08](build-host-bh-glx-110-a10u08.md) — shared 32-chip BH Galaxy, no sudo, NFS checkout, outside SLURM
- [Shared tree, multiple sessions](shared-tree-multi-session.md) — other Claude sessions (even on other boxes, via NFS) use /data/kmabee/tt-metal-2 + chips; check ListAgents / queue.lock before mkb or device runs; tt-metal-3 is the second build tree, used by bh-glx-120-c03u08 (c02u02 sessions stay on tt-metal-2); override W and PY after sourcing helpers
- [Visible process is not my process](visible-process-is-not-my-process.md) — hidepid visibility means same UID; other Claude sessions run as kmabee from other checkouts
- [Device usage visibility](device-usage-visibility.md) — /proc/driver/tenstorrent/N/pids is the real owner check; four holder-checks that cannot fail under hidepid; SLURM+Grafana show kmabee's runs as idle
- [Stale chip locks look like a container](stale-chip-locks-look-like-container.md) — dead-PID /dev/shm locks after a killed run; kill -0 the owner, glx_reset + rm locks; on c03u08 the lock files are akhan-owned so rm fails and stock waitchips reset-loops: use the runs_sasha/env.sh override
- [Galaxy hard-kill needs glx_reset](glx-hard-kill-needs-reset.md) — silent 2-5x perf degradation, no error; budget two resets; re-check a minute after a reset; "Sysmem mapped at unexpected NOC address" with no holder = reset + wait ~1 min
- [TT galaxy fabric run hygiene](tt-galaxy-fabric-run-hygiene.md) — glx_reset after hard kills, background device runs, the inverted fabric-link lease API
- [Gemma4 unit dir opens chips](gemma4-unit-dir-opens-chips.md) — only test_prefill_configs/test_prefill_dispatch are host-only; never run the dir beside a live run
- [BH Galaxy prefill is power-throttled](bh-galaxy-prefill-power-throttled.md) — AICLK ~1100-1250/1350 at 115 W TDP (raised to 130 W on 2026-09-29: re-baseline); stale/zero-data hacks look falsely fast; isolated-layer bench understates energy wins
- [/data quota and tracy captures](data-quota-tracy-captures.md) — per-user quota; a capture is ~15 GB; truncated .git/index = quota; trim profiler/ after each capture
- [/data checkout venv $HOME pin](data-checkout-venv-home-pin.md) — dangling python_env on a second box: repoint at /usr/bin/python3.10 (uv-python is gone); same for CMakeCache and stale PCH
- [b03u08 device 24 is faulty](bh-glx-b02u08-dev16-dead.md) — repeatable: run hangs at first traced chunk BEFORE any reset, then POST_RESET fails on dev 24; b02u08 dev 16 same; arm a stall detector, lspci is not a health check
- [Board + fleet smoke test](tt-board-smoke-test.md) — ~/scripts/tt_board_smoke.py (0.4s, stdlib) + tt_fleet_smoke.py (7 boxes ~1s over ssh stdin); sysfs attrs NOT under device/; detects hung, MISSING tray, nodata; strace-verified safe beside a live run

## Build, git, CI
- [tt-metal build approach](tt-metal-build-approach.md) — host source build, not Docker; submodule/tee/SFPI traps
- [ninja target does not install](ninja-target-does-not-install.md) — partial builds leave Python loading the stale .so; use `--target install`
- [Kernel edits break queued runs](kernel-source-edits-break-queued-runs.md) — kernels JIT at run start; edit as patches mid-queue; git rebase/checkout in the shared tree also counts, use plumbing; discarded if-constexpr still compiles
- [pre-commit stashes unstaged work](precommit-stashes-unstaged-work.md) — a killed first commit hides your uncommitted changes in ~/.cache/pre-commit; plus black version skew
- [Never edit a running bash script](never-edit-a-running-bash-script.md) — bash reads by file offset; a valid edit mid-run throws a phantom syntax error
- [Cross-worktree pytest sys.path trap](cross-worktree-pytest-syspath-trap.md) — rootdir beats PYTHONPATH; run from the tree you mean, witness models/ttnn __file__, block on free devices; kernels resolve from cwd first — sparse-checkout a Python-only worktree
- [tt-metal push routes](tt-metal-push-routes.md) — SSH needs the forwarded SSO-authorized agent key (on-disk key fails SAML); HTTPS gh token lacks workflow scope (pushed range touching workflows is refused); SAML flips per box/day, probe with one real push; gate CI dispatch on ls-remote
- [tt-metal PR body edits](tt-metal-pr-body-edits.md) — edit the live body; a bot appends CI Status and rewrites the body on every push and right after gh pr create
- [tt-metal /test CI selector](tt-metal-test-command-ci-selector.md) — test-command.md maps diffs to CI; L2 nightly + additional_test_categories is mandatory for ops (WH+BH); a plain L2 dispatch skips every test job yet shows success
- [Merge Gate gcc-12 sweep](merge-gate-gcc12-sweep.md) — PR CI is clang-only; dispatch merge-gate.yaml before merging C++ changes
- [Blaze prefill CI time budget](blaze-prefill-ci-time-budget.md) — 479/488 min used; budget, not code, gates a new model leg
- [Host-only model tests have no CI home](host-only-model-tests-have-no-ci-home.md) — tests/torch/ in zero rows; models team has no cpu_medium grant
- [Deepseek collection check](deepseek-collection-check.md) — 28346 expected; run it against an unbuilt checkout, and the 3 traps (32 chips per run, no node ids, stale board)
- [Sourcing bashrc gives GH_TOKEN, not an agent](bashrc-sourcing-gh-token.md) — gh token is above the interactive guard (line 7) so `source ~/.bashrc` DOES auth gh in the Bash tool; fixagent is below it; gh auth is per-machine via dotfiles

## Profiling and measurement method
- [Tracy profiling on tt-metal](tracy-profiling-tt-metal.md) — no rebuild needed; 4 traps that give wrong/empty results silently
- [Tracy --device-trace-profiler trap](tracy-device-trace-profiler-trap.md) — it kills op attribution and breaks post-processing; omit it
- [Per-op perf compares need the same renderer](per-op-perf-compare-same-renderer.md) — a number lifted from an old writeup made a false +21% regression; device spread on one op is ~17%, re-render both sides
- [tt_cache mesh mismatch deadlocks](tt-cache-mesh-mismatch-deadlock.md) — check weight-cache provenance BEFORE debugging fabric/CCL; a wrong-mesh cache hangs silently; worked Gemma4 8x4 example (8x4 is fine: 13.6 s @256k)
- [ttnn.linear LoFi default](ttnn-linear-lofi-default.md) — a program_config or core_grid silently drops to LoFi; Gemma4 KV drift was bf16 accumulation (MLP needs fp32, attention needs HiFi2 + fp32)
- [CCL: one worker per link, one incrementer per semaphore](ccl-one-worker-per-link-and-semaphore.md) — two silent-hang traps when adding a concurrent fabric exchange
- [Ring joint kernel-config cap + skip lockstep](ring-joint-kernel-config-buffer-cap.md) — 70,656 B program cap; opt_level=O2 frees ~30% but the JIT hash ignores opt_level (purge cache before measuring); reader/compute K skips must match on BOTH compute paths

## Gemma4 prefill
- [Gemma4 8192 PCC floor source](gemma4-8192-pcc-floor-source.md) — enters at global L5 attention; fidelity, Q chunk, denominator comp, bfp4 MLP ruled out; post-attn norm hides row-scale errors
- [Block-cyclic + #57998 validated](gemma4-block-cyclic-57998-validated.md) — Sasha's 2k/4k/8k test passes with my PR plus 2 halo slots + guard removal; #58685 part 1 (traced end) still open
- [Gemma4 fast tanh GELU](gemma4-fast-tanh-gelu.md) — GELU_TANH param 1: PCC-neutral, -1.8% at 8k; FP32 constants cost 2 SFPLOADI each; fit exp polys for zero mean error and [1,2)
- [Gemma4 KV PCC: use early layers](gemma4-kv-pcc-early-layer-method.md) — final PCC is chaotic/non-additive (±0.01), base fails the 0.91 gate at 8k context (passes by ~0.001 at 256k); compare layers 0-20 error ratio
- [Gemma4 M=256 matmul limits](gemma4-m256-matmul-limits.md) — 2k projections hit two ~100 us limits; only width-sharded in0 helps; bfp4/fused gate-up/subblocks null; dst_full_sync+fp32 bug
- [Gemma4 PCC not bit-reproducible](gemma4-pcc-not-bit-reproducible.md) — at 8192 layers 0-12 match run to run, drift from layer 13; use a first-differing-layer check, not final PCC, for identity claims
- [Gemma4 PCC test gate and /dev/shm](gemma4-pcc-test-gate-and-shm.md) — 0.91 gates the min per-head PCC, not overall; stale shared ring blocks runs; test strips PREFILL_* env; chunk size is ONLY GEMMA4_TEST_CHUNK_SIZE (lib.sh pcc helper got it wrong)
- [Gemma4 perf run time budget](gemma4-perf-run-time-budget.md) — sweep 307→177 s: local venv (NFS imports 50 s/process), skip placeholder host work on warm builds, Weka; CP-split weights measured 40x but not pursued; clear_program_cache between models
- [Gemma4 PP=4 measured](gemma4-pp4-scoping.md) — 1.15-1.17x at 256k (ported to the sep-07 freeze branch); TP=1 breaks concat_heads' L1; a later rank must clone its input; balance by global-layer count
- [Gemma4 prefill box setup](gemma4-prefill-box-setup.md) — real weight/tt_cache paths on bh-glx; TP-tagged cache; never trust the legacy-cache fallback
- [Gemma4 prefill chunk size](gemma4-prefill-chunk-size-win.md) — TTFT vs throughput table; 32768 best at 256k (11.28s), 4096 best single setting; never extrapolate the fit, and check a fit's point count (the 16384/32768 slopes were re-measured 2026-09-18)
- [RETRACTED: Gemma4 width-invariance](gemma4-prefill-not-width-invariant.md) — the defect was my multi-width build, not the model; always run the single-vs-multi build control in separate processes
- [Gemma4 perf test id after #58620](gemma4-prefill-perf-test-id.md) — readback_final param removed and TOTAL in ms since 2026-10-01; lib.sh perf auto-detects old vs new
- [rms_norm is row-parallel only — now FIXED by block sharding](gemma4-prefill-rmsnorm-row-parallel-floor.md) — 4.36x on the op / −16.6 ms on `a` at chunk 2048 (measured in-model 2026-09-18); the reference impls' single-tile shard height is NOT a ttnn limit, and the defect is per-core inefficiency not core count (16 cores beat 48/64/96); width-bound, ~24 ms/chunk on 8-32 cores; the chunk-invariant cost is ~94 ms, and the old 70 ms figure is ¾ of it (excess over ideal scaling)
- [Gemma4 ring SDPA K split](gemma4-ring-sdpa-ksplit.md) — 256k @2048 20.1->14.3 s and better PCC; bands of rows, L1-to-L1 merge; 8192 doesn't fit L1
- [Gemma4 ring SDPA q_chunk by slab](gemma4-ring-sdpa-qchunk-by-slab.md) — global q 32/64/96 at chunk 2k/4k/8k; one fixed value costs +7 s at 2k; only visible in total/slope, not TTFT
- [Gemma4 SDPA QK/PV LoFi](gemma4-sdpa-pv-lofi.md) — global QK^T and softmax@V at LoFi: accuracy-neutral, -20% at 256k; LoFi replay reinit across shapes HANGS; gate base-limited at >=8192
- [SDPA q_chunk occupancy owns the prefix slope](gemma4-sdpa-qchunk-occupancy.md) — global layers only: on SLIDING layers q_chunk is NOT a floor lever (q=128 is a 1.0% regression at chunk 2048, q=32 is illegal), measured 2026-09-18; MAC-bound on QK^T/PV (LoFi 0.79x, HiFi4 1.76x); occupancy passed a pre-registered test — use the depth-subtracted growth ratio 0.4995x, NOT the diluted total-at-depth 0.443x, and 2048-vs-4096 is the sharpest pair not a blind one (corrected 2026-09-18); the floor is 61% of chunk-2048's deficit at 256k, not the prefix term; ONE op grows with context, sliding flat to 0.8%; Cores always reads 114 so it hides the loss
- [Sliding K/V reuse ceiling](gemma4-sliding-kv-reuse-ceiling.md) — zero sliding K/V re-reads only -1.9% at 8k; don't build K/V chains for sliding; probe traffic before data-movement projects
- [Gemma4 sliding SDPA K split + halo overlap](gemma4-sliding-sdpa-ksplit.md) — correct but ~-1% each; sliding op at 2k is mostly fixed cost
- [Gemma4 util metric traps](gemma4-util-metric-traps.md) — layer-perf trace includes per-chunk preamble; SDPA util is HiFi2-normalised; 8k matmuls throttle to ~1050 MHz
- [Gemma4 variable chunk PoC](gemma4-variable-chunk-poc.md) — perf real but loses to fixed 8192 mid-range; functionally broken (multi-width build bug); small chunks never intrinsically better; policy is a sawtooth
- [Ring SDPA segments need 1 Q chunk/core](ring-sdpa-seg-accum-one-q-per-core.md) — seg accumulation silently off when units > cores; 12288/q96 PCC fail
- [Stack merge campaign 10-01](stack-merge-campaign-1001.md) — #58223 merged, #58224 still open (2026-10-02); after a compaction read debug-docs SESSION_STATE.md first
- [Session state 10-03](session-state-1003.md) — after a compaction read SESSION_STATE_1003.md + the experiment ledger first; chips handed off 18:07 UTC 10-03

## Mistral Small 4 / PP=4 / disagg
- [Mistral4 56,320 golden](mistral4-55k-golden.md) — staged on /mnt under blaze/mistralai, CI-green; SDPA gate; why the 0.999999 bar is unachievable
- [Mistral4 branch suites](mistral4-branch-suites.md) — which runner goes with which branch; base branch has no PP/perf tier; 3 silent-wrong-result traps
- [Mistral4 bring-up workspace](mistral4-bringup-workspace.md) — canonical checkout /data/kmabee/tt-metal; caches in /home/kmabee; uv venv has no pip
- [Mistral4 CI staging prereqs](mistral4-ci-staging-prereqs.md) — only the MoE leg is self-contained; MLA ref cache staged at /data/kmabee/mistral4_mla_ref_cache
- [Mistral4 disagg prefill+decode](mistral4-disagg-prefill-decode.md) — WORKING 2026-08-28 (6/6 tokens); handoff mechanics, the two bugs found, and why 17 min/token is harness not decode
- [Disagg on the reload ring 2026-09-19](mistral4-disagg-reload-ring-260919.md) — GREEN 7/7 + interactive chat; where to seed KV in the ring; capture is the startup cost
- [L36 chunked_padded layer-32 cliff](mistral4-l36-chunked-padded-layer32-cliff.md) — raw-PCC artifact of massive activations, FIXED via nPCC gating; L1 validates ~nothing
- [Mistral4 is movement-bound, not FLOP-bound](mistral4-movement-bound-not-flop-bound.md) — three fidelity/buffer knobs all null; go after ops and movement, not math
- [Per-layer MoE variance, not stage imbalance](mistral4-per-layer-moe-variance.md) — the "stage-1 outlier" is layer 1; stage balance is closed
- [Mistral4 PP=4 real D2D results](mistral4-pp4-real-d2d-results.md) — PP_HANDOFF=none is not a ceiling; weight-cache and column-mapping facts
- [Mistral4 precision census](mistral4-precision-census.md) — 97.5% of params are BFLOAT4_B (the MoE experts), not BF16/BFP8
- [Mistral4 prefill campaign harness](mistral4-prefill-campaign-harness.md) — archived at ~/debug-docs/.../perf/pp4_campaign_scripts with a tested restore.sh; upstream only on tt-metal-3
- [Mistral4 prefill has no LM head](mistral4-prefill-has-no-lm-head.md) — prefill emits KV only since ~2026-09; anything sampling from prefill breaks
- [Mistral4 variant rename cache trap](mistral4-variant-rename-cache-trap.md) — mistral_small4 vs mistral_small_4 orphans the 65G weight cache; symlink fix
- [MoE routing capture generation](moe-routing-capture-generation.md) — no generator in-tree; three traps that silently yield a wrong capture
- [PP=4 latency metric is contaminated](pp4-latency-metric-contaminated.md) — E2E_CLOCK eats trace capture + shutdown drain; PP only wins latency above ~7 chunks, and a stage is 0.72x not 0.25x
- [PP4 perf harness traps](pp4-perf-harness-traps.md) — the driver hides rank crashes; --profile clobbers the plain binding
- [PP stage shape: SP beats TP](pp4-stage-shape-sp-beats-tp.md) — [4,2] loses 45% at 102K; expert FFN doesn't move with TP at all
- [PP=4 headline has no steady state](pp4-throughput-headline-has-no-steady-state.md) — the tok/s number is a ramp median; slides 10% with the analyzer warmup arg
- [Reload-ring mid-walk stalls](reload-ring-mid-walk-stalls.md) — 2 of 4 runs stopped mid-`_drive` with no error; check liveness FIRST, and why rank-silence is not a symptom
- [tt-d-gen prefill migration is prebuilt](ttdgen-prefill-migration-prebuilt.md) — items 1-3 are verify-not-build; the chunk-table contract is 4 fields; d-gen main has no migration
- [Gemma4 data on /mnt/weka](gemma4-weka-paths.md) — TT_CACHE_PATH + PREFILL_TRACE_DIR Weka paths (done 2026-10-02); root-owned, ask storage to refresh; cold PCC 26.6→12.5 min
- [PR labels: no triage labels](pr-labels-no-triage.md) — topic labels only (perf, model: gemma-4); never set pr-priority / pr-risk / pr-complexity
- [Shared kernel sources across ops](shared-kernel-sources-across-ops.md) — rotary_embedding_llama compute kernel is also built by rotary_embedding_indexed; grep path constants before changing a kernel arg contract
- [Power tier decides which measurement is valid](bh-galaxy-power-tier-measurement-validity.md) — 75W box: full clock ~40s then −26%; 256k inflates +20% but layer profiles match a 190W box to 0.03%; long-run A/B deltas are the trap
- [Mistral4 TP4 perf A/B 10-05](mistral4-tp4-perf-compare-1005.md) — baseline vs Asif vs Alina branches + harness; asif -1.0% not -2.95%; Alina/local-disk runs still unmeasured
- [Gemma4 PRs do not port to Mistral4](mistral4-gemma4-pr-portability.md) — no sliding window, no GELU, fabric already torus; K-split + seg-acc measured NULL (and proved to engage); next lever is MoE
