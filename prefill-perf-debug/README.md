# prefill-perf-debug

Make chunked-prefill performance debugging repeatable on a given model: find whether the
problem is the per-chunk cost or the prefix cost, which layers own it, which ops inside
them, and — with approval — what those ops are bound by. Then say only what was measured.

```bash
/prefill-perf-debug            # Claude follows SKILL.md

# the CLI directly. NOT necessarily ~/.claude: this account may set CLAUDE_CONFIG_DIR.
S="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/prefill-perf-debug"
python3 $S/ppd.py --help
```

## Usage

| command | what it does | device? |
|---|---|---|
| `ppd.py probe --profile M` | capability probe; run this first | no |
| `ppd.py budget --tier triage\|standard\|deep` | cost + disk + who holds each device | no |
| `ppd.py level0 --log L [--reference C]` | fit `a`/`slope` per chunk size, project to ISL | no |
| `ppd.py level1 --curve L --level0-log L` | per-layer-type depth curves, reconciled | no |
| `ppd.py level2 [--pairs J] --level0-log L` | per-op, depth 0 vs depth D, re-rendered from raw | no |
| `ppd.py level3 --list \| --propose KNOB` | **assisted** ablations: propose, snapshot, verify revert | no |
| `ppd.py check --csv C --chunk N` | assertions over one rendered capture | no |
| `ppd.py compare --a A --b B --a-raw D --b-raw D` | A6-guarded cross-branch per-op diff | no |
| `ppd.py analyze --goal "..."` | every level that has data + the whole output contract | no |
| `ppd.py teach [--level N]` | question / prediction / command / why-valid, per level | no |
| `ppd.py run --what e2e\|capture ... --launch` | build and launch a device run, **detached** | **yes** |
| `ppd.py prune <dir> --yes` | delete the ~4.8 GB raw device CSVs of finished captures | no |
| `ppd.py validate` | the published-results regression test, offline | no |

Everything except `run` is offline. Do the offline work first.

## Options that matter

- `--profile <name>` — the model profile (`profiles/<name>.json`). `gemma4` ships.
- `--goal "<the user's words>"` — routes the report's headline (TTFT / throughput /
  chunk comparison / regression).
- `--reference <chunk>` — which chunk size to quote ratios against; default is the best
  total.
- `--tier triage|standard|deep` — the budget tier. `budget` prints the estimate; get
  consent before a sweep.
- `--cross-build` on `compare` — declare a deliberate cross-branch check, so A12 becomes
  a warning instead of a refusal. Only valid when both sides were re-rendered from raw.

## What it produces

```
<workdir>/prefill-perf/<model>-<YYYY_MM_DD_HH_MM_SS>/
  manifest.json   model, branch, git sha, mesh, tier, goal, capability probe
  findings.json   a/slope per chunk, per-op attribution, assertions fired
  raw/            run logs; ops CSVs only
  reports/        rendered tt-perf-report tables + side-by-side comparisons
  TLDR.md         the answer first. Forwardable.
  REPORT.md       the full record, residuals, the traps that applied
```

`TLDR.md` leads with the answer in a *term | A vs B | cause | whose* table, names the
method behind each finding, keeps optimization ideas to one labelled section, and states
every residual.

## Adding a model

`profiles/gemma4.json` is the worked example; `profiles/TEMPLATE.json` is the blank with
each field explained. You need the model's e2e chunked-prefill test, its per-chunk log
line, its isolated-layer benchmark and signpost naming, its layer types and counts, and
— for the occupancy check — the work-unit math of whichever op grows with context.

Then `ppd.py probe --profile <new>` and fix whatever it reports missing. **v1 is
validated on Gemma4 only**; the probe is untested against a second harness and encodes
Gemma4's shape until one exercises it.

## Files

| file | what |
|---|---|
| `SKILL.md` | the procedure Claude follows |
| `METHOD.md` | why each assertion exists — the incident behind it; teaching-mode material |
| `EXAMPLES.md` | worked examples, with real output |
| `ppd.py` | the CLI |
| `helpers.py` | parsing, fitting, per-op loading, the occupancy math |
| `assertions.py` | A1–A12 as checkable code |
| `levels.py` | levels 0–2 and the device-run driver |
| `level3.py` | the assisted path: propose, snapshot, verify the revert |
| `probe.py` | the capability probe |
| `teach.py` | teaching mode: the method and the five retracted claims |
| `report.py` | the output contract |
| `validate.py` | the regression test (see below) |
| `profiles/` | model profiles |
| `tests/` | `run_tests.sh` — validate + CLI smoke tests |

Stdlib only; no third-party imports. `tt-perf-report` is needed for level 2
(`pip install tt-perf-report`).

## Self-test

```bash
python3 $S/validate.py          # expect 104 passed, 0 failed
$S/tests/run_tests.sh
```

`validate.py` is a **regression test, not documentation**. It reproduces the published
Gemma4 `a`/`slope` table, the twelve per-op rows and the four headline results offline
from captures already on disk, and exercises every assertion in both directions. It
needs `/data/kmabee/gemma4_runs/` (the six Tracy captures and the run logs); on a machine
without them it reports what it skipped rather than passing vacuously.

## Scope

**In:** where chunked-prefill device time goes, at four levels of resolution, for a model
whose harness the probe says is instrumented for it.

**Out:** automated level-3 patching; decode perf; serving/throughput benchmarks; accuracy
evaluation; comparing against stored baselines (that violates A6 unless the raw captures
are kept).
