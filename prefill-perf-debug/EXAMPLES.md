# prefill-perf-debug — worked examples

All output below is real, produced by this skill against the Gemma4-31B artifacts on
`bh-glx-120-b03u02`. Everything except Example 5 is **offline** — no device time.

```bash
S=~/.claude/skills/prefill-perf-debug
```

---

## Example 1 — probe first, always

```bash
python3 $S/ppd.py probe --profile gemma4
```

```
capability                                                        detail
e2e chunked-prefill test with per-chunk device times   PRESENT   test_prefill_long_context_traced ... emits '[traced_perf] chunk'
device / staging / readback timings separated          PRESENT   summary line distinguishes them
per-layer isolated benchmark (layer type x chunk index)PRESENT   test_prefill_layer_perf_chunk_n takes layer_type=['global','local','both','all']
fake-depth mechanism (pre-filled cache + valid-KV field)PRESENT  sets kv_actual_global
signposts around the measured region                   PRESENT   e.g. gemma4-layer-global-chunk0-start .. -stop
tt-perf-report installed                               PRESENT   v1.2.9
profiler utilization columns populated                 MISSING   present but EMPTY: NOC UTIL, DRAM BW UTIL, ETH BW UTIL, CB WAIT FRONT
layer-count override for layer differencing            MISSING   validate_31b_config() hard-rejects a changed num_hidden_layers

Degradations:
  - utilization columns: Do NOT use them, and do NOT infer anything from their absence.
  - layer-count override: Level 1 falls back to per-layer-type depth curves (in-tree).
      Layer-count differencing needs a temporary patch -> ASSISTED path only, like level 3.

VERDICT: levels available -> 0, 1, 2, 3 (assisted only)
```

Report this table to the user before promising anything. The two MISSING rows are real
findings, not skill bugs: the utilization columns genuinely are empty on this path, and
Gemma4 has no layer-count knob.

---

## Example 2 — level 0 triage, the default when there is no specific goal

```bash
python3 $S/ppd.py level0 --profile gemma4 --reference 8192
```

```
Level 0 - two-term fit  T = N*a + slope*N(N-1)/2   (ISL 262,144)

  chunk     N    a (ms)     slope      R^2  per-chunk    prefix     total
--------------------------------------------------------------------------
   2048   128     131.3     1.458  0.99985     16.80s    11.85s    28.65s
   4096    64     174.2     2.995  0.99974     11.15s     6.04s    17.19s
   8192    32     242.7    11.990  0.99996      7.77s     5.95s    13.71s
  16384    16     443.7    37.100  1.00000      7.10s     4.45s    11.55s
  32768     1     928.2        --       --         --        --        --   <- slope UNVERIFIABLE

ratios vs chunk 8192 (requested):
     2048: total 2.09x = per-chunk 2.16x x prefix 1.99x
     4096: total 1.25x = per-chunk 1.44x x prefix 1.02x
     8192: total 1.00x = per-chunk 1.00x x prefix 1.00x
    16384: total 0.84x = per-chunk 0.91x x prefix 0.75x

floor (A11 - two different numbers, both stated):
  chunk-invariant cost F          = 94.1 ms (affine fit of a(C) over [2048, 4096, 8192])
  excess over ideal token scaling = 70.6 ms = 0.75 x F
  NOTE chunk 32768: only 1 chunk(s) measured ... the prefix slope is not determinable and is NOT extrapolated.
```

Three things to read out loud:

- **chunk 4096's prefix term is within 2% of 8192's** — all of 4096's 1.25x penalty is
  the per-chunk floor. That single line is usually the most actionable output of a
  triage pass.
- the chunk-32768 row is honest about what one chunk can and cannot tell you.
- both floor numbers appear, labelled. 70.6 and 94.1 are the **same** measurement on two
  bases (A11); quoting one as the other is a 33% error, and it has happened.

---

## Example 3 — "is this a regression?" — the A6 path

The interesting case is the one that **refuses**:

```bash
python3 $S/ppd.py compare --a old_writeup_value.csv --b new.csv --b-raw <capture-dir>
```

```
[FAIL] A6 cross-branch compare re-rendered: old writeup: not re-rendered from a raw
       capture (value lifted from a table/summary) - REFUSED; old writeup: no raw capture recorded

REFUSED: fix the above before reporting any delta. A number lifted from an old writeup
produced a false +21% regression once; per-device spread on one op is ~17%.
```

Done properly — both sides re-rendered from their own raw captures with one tool:

```bash
python3 $S/ppd.py compare \
  --a /data/kmabee/gemma4_runs/perf_reports/OLD/isl0k_local.csv --a-raw /data/kmabee/gemma4_runs/attn_op_captures/isl0k \
  --b /data/kmabee/gemma4_runs/perf_reports/floor_c8192_local.csv --b-raw /data/kmabee/gemma4_runs/floor_c8192 \
  --a-build svuckovic/gemma4-prefill-model --b-build kmabee/gemma4-swa-multihop-halo --cross-build
```

```
[PASS] A6 cross-branch compare re-rendered: both sides re-rendered from raw with tt-perf-report 1.2.9
[WARN] A12 same build: deliberate cross-build comparison (...), allowed only because both sides
       were re-rendered from raw (A6). Report it as cross-build in the writeup.
```

The measured SDPA delta is **+1.9%**, not the +21% the stored table implied. Every op is
within 2%; the sliding layer is ~4% *faster* on the newer branch.

---

## Example 4 — the full offline pass, and the TLDR it writes

```bash
python3 $S/ppd.py analyze --profile gemma4 \
  --goal "why is chunk 2048 slower than 8192 at 256k" --reference 8192 --workdir /tmp/x
```

Runs the probe, level 0, level 1 and level 2, re-renders all six captures from raw,
reconciles every level against the one above, and writes the run directory. The level-2
section:

```
chunk 2048  (c2048)
  global   layer   2.669 ->   6.142 ms  (+130.1%)   RingJointSDPA:  0.189 ->  3.662 ms   growth share 100.0%
  local    layer   2.430 ->   2.435 ms  (  +0.2%)   RingJointSDPA:  0.404 ->  0.405 ms   [CONTROL: flat]
  useful occupancy 29%  (32 units / 110 slots, depth 1) - the Cores column cannot show this
...
per-chunk floor: 83-85% is the 50 local layers, BY COUNT (three estimators over chunks [2048, 8192], agreeing to 2.2 pts)
    excess_in_range  model floor   79.0 ms  local share 84.8%   (global 1.20 ms, local 1.34 ms)
    affine_layer     model floor  110.0 ms  local share 85.0%   (global 1.65 ms, local 1.87 ms)
    per_op_clamped   model floor  112.9 ms  local share 82.8%   (global 1.94 ms, local 1.87 ms)

assertions:
  [PASS] A9 matched prior context: all 3 points at prior context 49,152 tokens (chunk indices [6, 12, 24])
  [WARN] A2 Total %/gap usability [deep_c8192_i6/global]: gap outlier EmbeddingsDeviceOperation = 1,117,241 us
         vs median 0.53 us (2,120,002x). Total % and Op-to-Op Gap are UNUSABLE - use Device Time.
  [PASS] A3 Cores != occupancy [deep_c8192_i6/global]: Cores column reads ['114'] - that is grid size,
         NOT occupancy. Useful occupancy at chunk 8192 = 58% (128 work units over 220 slots, depth 2).
  [PASS] A8 control quantity: controls flat: local @2048 +0.2%, local @4096 +0.8%, local @8192 -0.1%

reconciliation against level 0 (A10):
  [PASS] chunk 8192 per-chunk floor (sum of per-op x layer count) 276.689 ms vs level-0 242.740 ms -> +14.0%
  [PASS] chunk 8192 prefix slope implied by RingJointSDPADeviceOperation 11.629 ms vs level-0 11.990 ms -> -3.0%
```

and the head of `TLDR.md`:

```markdown
**Chunk 2048 is 2.09x slower than 8192 over a 256k prompt.** It splits into two
independent terms that live in different layers and need different fixes.

| term | 2048 vs 8192 | cause | whose |
|---|---|---|---|
| **per-chunk term** (= TTFT) | **2.16x** | a **~94 ms chunk-invariant cost** paid once per chunk | ~83-85% the 50 **local** layers, by count |
| **prefix term** | **1.99x** | the growing op leaves **71% of the core grid idle** at chunk 2048 | **100%** the 10 **global** layers |
| | **= 2.09x** | | |
```

Note what the report does *not* do: the +14.0% level-2 residual is printed, not absorbed.
The isolated-layer harness has no inter-layer overlap, so per-op sums overstate — that is
a known property, and stating it is what makes the ratios trustworthy.

---

## Example 5 — a device run, and the assisted level 3

Device runs are the only thing that costs. Print the budget and get consent first:

```bash
python3 $S/ppd.py budget --tier standard --profile gemma4 --workdir /data/kmabee
```
```
  11 e2e point(s) x ~3 min      = ~33 min
  4 profiler capture(s) x ~12 min = ~48 min, ~20 GB raw
  TOTAL ~1h 21m device time, ~20 GB disk
Devices: 33 node(s), 0 with a visible holder
  CAVEAT: empty holders does NOT prove the device is free: hidepid=2 hides other users' PIDs.
```

Build the command, look at it, then launch **detached**:

```bash
python3 $S/ppd.py run --profile gemma4 --what capture --chunk 8192 --chunk-idx 6 \
        --layer-type both --ctx 262144 --out /data/kmabee/gemma4_runs/mycap --launch
```
```
[PASS] A5 no --device-trace-profiler: capture command is clean
launched detached pid=... log=/data/kmabee/gemma4_runs/mycap/run.log
Poll the log; do NOT kill it. A SIGKILL mid-fabric makes the next mesh open fail with
'Timed out while waiting for active ethernet core ... to become active again' (recover with tt-smi -r).
```

Level 3 never patches. It proposes, snapshots, and checks the revert:

```bash
python3 $S/ppd.py level3 --propose GEMMA4_SDPA_FIDELITY --run-dir <run>
python3 $S/ppd.py level3 --record-baseline <run>      # BEFORE any edit
#   ... user approves; patch; run; revert ...
python3 $S/ppd.py level3 --verify-revert <run>
```

```
REVERT NOT CLEAN:
  - untracked files LOST: ['models/demos/gemma4_d_p/tt/attention/__init__.py.orig']

Do NOT start the next run. `git diff` against pre_patch.diff in this run dir and restore
anything the revert dropped. This is exactly the failure that cost three runs: a
`git checkout` removed an `import os` a previous patch had added, and the next run died
with NameError partway through.
```

Two settings of a fidelity-style knob are proposed together, because measuring one
direction only cannot distinguish a bound from a coincidence:

```
GEMMA4_SDPA_FIDELITY=lofi    MAC passes 2->1   0.786x
GEMMA4_SDPA_FIDELITY=hifi4   MAC passes 2->4   1.755x
```

And A1 refuses the wider claim unless the knob was actually varied:

```
python3 -c "... A1_bound_claim('fabric', catalogue)"
[FAIL] A1 bound-by needs an ablation: no ablation in the record varied "fabric".
       Measure it or drop the claim; a rate mismatch is not evidence.
```

---

## Example 6 — teaching mode

```bash
python3 $S/ppd.py teach --level 2
```

Print the block for a level **before** running it, so the prediction is on the record
first (A7). The level-2 block, abridged:

```
PREDICTION (write this BEFORE running)
  At MATCHED prior context, the prefix work is exactly proportional to the chunk's token
  count. So a 4x smaller chunk does 0.25x the work. If the op is efficiency-neutral it
  takes 0.25x the time; if it is occupancy-bound it takes 0.50x. (Measured: 0.443x.)

WHY THIS COMPARISON IS VALID
  The subtraction is between two captures of the SAME layer on the SAME branch differing
  in one thing: prior context. And the chunk-size comparison holds prior context fixed
  rather than chunk index, which is what turns it from a comparison into a test with a
  predicted number.

TRAP
  The one comparison that CANNOT discriminate is 2048 vs 4096: both models predict 0.5
  there because both are depth-1. A valid test has to include the chunk size where the
  models disagree.
```

`teach` with no `--level` adds the five claims that were published and then retracted.

---

## Example 7 — the self-test

```bash
python3 $S/validate.py
```

```
prefill-perf-debug validation - gemma4-31b (tolerance 2.0%)
...
  ok   1. chunk 8192: growth share of RingJointSDPADevic: 99.79% vs 99.8% (-0.01%, tol 1.0%)
  ok   2. chunk 4096: sliding layer flat (+0.84%, ref +0.8%)
  ok   3. time ratio 2048/8192 at matched prior context: 0.443 vs 0.443 (+0.00%, tol 1.0%)
  ok   3. discriminates: 0.443 is between the neutral prediction 0.25 and the occupancy prediction 0.5
  ok   4. the three estimators agree to 2.2 pts (<= 3.0) - agreement IS the evidence
  ok   A6: and NOT the false +21% the stored table implied
================================================================
validation: 102 passed, 0 failed, 0 skipped
================================================================
```

Run it after any edit to the skill. A change that drops a check there is a regression.
