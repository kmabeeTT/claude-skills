---
name: prefill-perf-debug
description: This skill should be used when the user asks to "debug prefill performance", "why is TTFT high", "why is long-context throughput bad", "compare chunk sizes", "prefill chunk size", "per-chunk vs prefix cost", "profile prefill ops", "is this a prefill perf regression", or discusses where chunked-prefill time goes on a TT model.
version: 1.0.0
---

# Prefill perf debug

A repeatable, self-checking procedure for finding where chunked-prefill time goes on a
given model, and for saying **only what was measured**.

It is a funnel. **Every level must reconcile to the level above it**, and the report
must state the residual. A level that does not close is a finding, not something to
paper over.

| level | question | how | cost |
|---|---|---|---|
| **0** | which of the two cost terms is the problem? | e2e chunked-prefill at K chunk sizes; fit `T = N·a(C) + slope(C)·N(N−1)/2` | ~3 min per chunk size |
| **1** | which *layers* own each term? | per-layer-type depth curves, and/or layer-count differencing | ~3 min per point |
| **2** | which *ops* inside those layers? | Tracy capture at depth 0 **and** depth D, render `tt-perf-report`, subtract | ~12 min + ~5 GB per capture |
| **3** | what is each op *bound by*? | one-knob-at-a-time ablations, each re-measured end to end | ~3 min + a patch |

Level 0 is the instrument of record. `a` is TTFT and `slope` is what kills long-context
throughput; they are the only two numbers a deployment cares about.

**v1 scope: levels 0–2 are automated. Level 3 is assisted only** — propose the patch,
require approval, verify the revert. Ablation sites are model-specific and cannot be
inferred for an unseen model.

Everything lives in this directory. The CLI is `ppd.py`; run it with the repo's own
python (no third-party imports, stdlib only).

```bash
S=~/.claude/skills/prefill-perf-debug
python3 $S/ppd.py --help
python3 $S/ppd.py teach          # the method, with the traps, before you start
```

---

## Step 1 — probe before promising anything

```bash
python3 $S/ppd.py probe --profile <model>
```

Report the probe table to the user **up front**. Never fabricate a level you cannot
measure; degrade and say so. The probe already knows the consequences:

- no per-chunk device-time line → **stop**, levels 0–3 all rest on it
- no signposts / no `tt-perf-report` → level 2 unavailable
- no fake-depth mechanism → depth sweeps cost a real prefill each; drop to 2 depths
- **utilization columns are empty on this path** — do not use them, and do not infer
  anything from their absence

If the model has no profile, copy `profiles/TEMPLATE.json`, fill it in against the
model's own test file, and re-probe. v1 is **validated on Gemma4 only**; the probe is
untested against a second harness.

## Step 2 — ask the goal; it selects the branch

| goal | branch | first thing to measure |
|---|---|---|
| "TTFT is too high" | the **per-chunk** term | `a(C)`, then the floor's composition at depth 0 |
| "throughput is bad at long context" | the **prefix** term | `slope(C)`, then the op that grows with depth |
| "compare chunk size A vs B" | both terms | matched-**prior-context** per-op comparison (A9) |
| "is this a regression?" | re-render **both** sides | A6 — refuse if one side's raw capture is gone |
| no specific goal | level-0 triage, then recommend | the `a`/`slope` table for the legal chunk sizes |

Accept free text; pass it to `--goal`, which routes the report's headline.

## Step 3 — state the cost and get consent

```bash
python3 $S/ppd.py budget --tier triage|standard|deep --profile <model>
```

| tier | what | device time | disk |
|---|---|---|---|
| **triage** | level 0 at the legal chunk sizes | ~15 min | a few MB |
| **standard** | + level 1, + level 2 at two depths × two chunk sizes | ~1–1.5 h | **~25–30 GB** |
| **deep** | + assisted level-3 ablations | open-ended | as above |

`budget` prints the estimate, the free disk, and who holds each device. **Never start a
sweep without printing the estimate and getting consent. Never parallelise device runs.**

Two things it cannot tell you, so say them yourself:

- an empty `fuser` does **not** mean the device is free — a `hidepid=2` baseline hides
  other users' PIDs. If acquisition fails with no visible holder, say so rather than
  debugging the model.
- each capture writes ~5 GB (a ~4.8 GB `profile_log_device.csv`, a ~420 MB `.tracy`, a
  ~37 MB ops CSV). **Only the ops CSV is needed afterwards** — prune as you go with
  `ppd.py prune <capture-dir> --yes`.

## Step 4 — do the offline work first

Before spending a minute of device time, run every level that existing artifacts already
support. On this box the Gemma4 captures and logs make levels 0, 1 and 2 fully
reproducible with no device at all:

```bash
python3 $S/ppd.py analyze --profile gemma4 --goal "<the user's words>" --reference 8192
```

That emits the whole output contract and prints the TLDR. Use it to show the user what
the answer looks like before asking for device time.

## Step 5 — run the levels

### Level 0
```bash
# build the command; check the device; then launch detached
python3 $S/ppd.py run --profile <m> --what e2e --chunk 8192 --ctx 32768 --out <dir> --launch
python3 $S/ppd.py level0 --profile <m> --log <dir>/run.log --reference 8192
```
One `ctx_32k` run per chunk size gives both coefficients. **Never run a device job in a
foreground tool call with a timeout** — a killed wrapper is a SIGKILL mid-fabric and the
next mesh open dies on ethernet cores (recover with `tt-smi -r`). `run --launch` starts
it detached; poll the log.

Refuse to report a slope fitted from one chunk. `level0` marks it **UNVERIFIABLE** and
does not extrapolate.

### Level 1
```bash
python3 $S/ppd.py level1 --profile <m> --curve <depth-curve.log> --level0-log <e2e.log>
```
Per-layer-type depth curves, reconstructed against level 0's slope. Layer-count
differencing is the second route; on a model with no layer-count override it needs a
temporary patch, so treat it like level 3.

### Level 2
```bash
python3 $S/ppd.py run --profile <m> --what capture --chunk 8192 --chunk-idx 6 \
        --layer-type both --ctx 262144 --out <dir> --launch
python3 $S/ppd.py level2 --profile <m> --pairs pairs.json --out <dir>/reports \
        --level0-log <e2e.log>
```
**Hold prior context fixed, not the chunk index** (A9). Chunk index 7 is 57k of history
at chunk 8192 and 14k at 2048; matching prior context makes the prefix work exactly
proportional to chunk size, which turns the comparison into a test with a predicted
number. `level2` refuses an unmatched set.

### Level 3 — assisted only
```bash
python3 $S/ppd.py level3 --list
python3 $S/ppd.py level3 --propose <KNOB> --run-dir <run>     # prints the checklist
python3 $S/ppd.py level3 --record-baseline <run>              # BEFORE the patch
#   ... user approves; patch applied; run; revert ...
python3 $S/ppd.py level3 --verify-revert <run>                # must pass before the next run
```
Never patch unsupervised. An unsupervised revert already cost three runs: a `git
checkout` silently dropped an `import os` a previous patch had added. `--record-baseline`
/ `--verify-revert` is what catches that.

## Step 6 — the assertions

These belong in code, not prose, and `ppd.py` enforces them. Report the ones that fired.

| # | assertion |
|---|---|
| A1 | Refuse "bound by X" unless an ablation actually **varied X** |
| A2 | Ignore `Total %` and `Op-to-Op Gap` when one op's gap exceeds ~100× the median; use `Device Time` |
| A3 | Never report `Cores` as occupancy. Compute useful occupancy from the op's own work-unit math and print **both** |
| A4 | Assert utilization columns are non-empty before using them |
| A5 | Never pass `--device-trace-profiler` |
| A6 | For any cross-branch/build/date comparison, **re-render both sides from the raw captures with the same tool**; refuse if one side's raw capture is gone |
| A7 | Require a **pre-registered prediction** before an ablation or a discriminating comparison |
| A8 | Require a **control** — a quantity that should *not* move |
| A9 | When comparing chunk sizes at depth, hold **prior context** fixed, not chunk index |
| A10 | Every per-op attribution must **close against level 0** within ~15%; state the residual |
| A11 | Distinguish **"excess over ideal scaling"** from **"chunk-invariant cost"** — they differ by 4/3 |
| A12 | Never compare per-op timings across builds without A6 |

`METHOD.md` records the incident behind each one. Read it before overriding any of them.

```bash
python3 $S/ppd.py check   --profile <m> --csv <rendered.csv> --chunk 8192
python3 $S/ppd.py compare --a old.csv --b new.csv --a-raw <dir> --b-raw <dir> \
        --a-build <branch> --b-build <branch> [--cross-build]
```

## Step 7 — the output contract

One run directory per invocation:

```
<workdir>/prefill-perf/<model>-<YYYY_MM_DD_HH_MM_SS>/
  manifest.json   model, branch, git sha, mesh, tier, goal, capability probe
  findings.json   a/slope per chunk, per-op attribution, assertions fired
  raw/            run logs; ops CSVs only (the 4.8 GB device CSVs pruned by default)
  reports/        rendered tt-perf-report tables + side-by-side comparisons
  TLDR.md         the answer first. Forwardable. Links to REPORT.md
  REPORT.md       full record, every measurement, residuals, the traps that applied
```

`TLDR.md` rules, learned from the first writeup being called hard to parse:

- **Lead with the answer.** Not the method, not the optimization ideas.
- A 4-column table: *term | A vs B | cause | whose* (which layers own it).
- A **"how this was obtained"** section naming the method per finding. This is what made
  the difference when the first writeup was doubted.
- Confine "how to make it faster" to **one clearly-labelled section**. The
  investigation's job is to explain; drifting into levers was a documented complaint.
- State residuals and anything retracted. Do not present a clean pie chart over a
  measurement that did not close.

## Teaching mode

When the user says `--teach` or "explain as you go":

```bash
python3 $S/ppd.py teach            # all four levels + the failures
python3 $S/ppd.py teach --level 2  # just the one you are about to run
```

At each level it states **the question, the prediction, the command, the result, and why
that comparison is valid** — naming the A-numbered assertion it honours, and the trap
specific to that level. Print the level's block before running it, so the prediction is
on the record first (A7).

Surface the failures rather than hiding them; they are the most instructive part.
`teach` with no `--level` ends with the five that were published and then retracted, and
`METHOD.md` has them at length.

## Out of scope for v1

Automated level-3 patching; multi-model generalisation claims; comparing against stored
baselines (violates A6 unless the raw captures are kept); decode perf, serving benchmarks
and accuracy evaluation.

## Self-test

`validate.py` is the regression test, not documentation. It reproduces the published
`a`/`slope` table, the twelve per-op rows and the four headline results **offline**, from
captures already on disk, and exercises every assertion.

```bash
python3 $S/validate.py          # expect: 102 passed, 0 failed
```

A change to this skill that drops a check there is a regression. Run it after any edit.
