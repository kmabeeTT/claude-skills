#!/usr/bin/env bash
# prefill-perf-debug test suite. Offline: no device, no new captures.
#   1. validate.py  - reproduces the published Gemma4 results (the real regression test)
#   2. CLI smoke    - every subcommand runs and exits as expected
#   3. unit checks  - the assertions fire in BOTH directions, on synthetic input
set -u
S="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
FAIL=0
run() { # run <name> <expected-rc> <cmd...>
    local name="$1" want="$2"; shift 2
    local out rc
    out="$("$@" 2>&1)"; rc=$?
    if [ "$rc" = "$want" ]; then printf '  ok   %s\n' "$name"
    else printf '  FAIL %s (rc=%s, want %s)\n%s\n' "$name" "$rc" "$want" "$(echo "$out" | tail -5)"; FAIL=1; fi
}

echo "== 1. validate.py (SPEC s6 regression) =="
python3 "$S/validate.py" >"$TMP/v.log" 2>&1; VRC=$?
tail -3 "$TMP/v.log" | sed 's/^/  /'
[ "$VRC" = 0 ] || { echo "  FAIL validate.py"; FAIL=1; }

echo "== 2. CLI smoke =="
run "probe"            0 python3 "$S/ppd.py" probe --profile gemma4
run "budget triage"    0 python3 "$S/ppd.py" budget --tier triage --profile gemma4 --workdir "$TMP"
run "budget deep"      0 python3 "$S/ppd.py" budget --tier deep --profile gemma4 --workdir "$TMP"
run "level0"           0 python3 "$S/ppd.py" level0 --profile gemma4 --reference 8192
run "level1"           0 python3 "$S/ppd.py" level1 --profile gemma4 --use-profile-layer-counts \
                              --level0-log /data/kmabee/gemma4_runs/mh_sweep/run.log
run "level2"           0 python3 "$S/ppd.py" level2 --profile gemma4 --out "$TMP/l2" \
                              --level0-log /data/kmabee/gemma4_runs/mh_sweep/run.log
run "level3 --list"    0 python3 "$S/ppd.py" level3 --profile gemma4 --list
run "level3 propose"   0 python3 "$S/ppd.py" level3 --profile gemma4 --propose GEMMA4_SDPA_FIDELITY
run "level3 baseline"  0 python3 "$S/ppd.py" level3 --profile gemma4 --record-baseline "$TMP/l3"
run "level3 revert ok" 0 python3 "$S/ppd.py" level3 --profile gemma4 --verify-revert "$TMP/l3"
run "level3 no baseln" 2 python3 "$S/ppd.py" level3 --profile gemma4 --verify-revert "$TMP/nope"
run "check"            0 python3 "$S/ppd.py" check --profile gemma4 --chunk 8192 \
                              --csv "$TMP/l2/deep_c8192_i6_global.csv"
run "check rejects A5" 2 python3 "$S/ppd.py" check --profile gemma4 --chunk 8192 \
                              --csv "$TMP/l2/deep_c8192_i6_global.csv" --cmd "tracy --device-trace-profiler"
run "compare refuses"  2 python3 "$S/ppd.py" compare --a "$TMP/l2/floor_c8192_local.csv" \
                              --b "$TMP/l2/deep_c8192_i6_local.csv"
run "compare ok"       0 python3 "$S/ppd.py" compare \
                              --a "$TMP/l2/floor_c8192_local.csv" --a-raw /data/kmabee/gemma4_runs/floor_c8192 \
                              --b "$TMP/l2/deep_c8192_i6_local.csv" --b-raw /data/kmabee/gemma4_runs/deep_c8192_i6 \
                              --a-build same --b-build same
run "run (no launch)"  0 python3 "$S/ppd.py" run --profile gemma4 --what capture --chunk 8192 \
                              --chunk-idx 6 --out "$TMP/cap"
run "teach (all)"      0 python3 "$S/ppd.py" teach
run "teach --level 2"  0 python3 "$S/ppd.py" teach --level 2
run "analyze"          0 python3 "$S/ppd.py" analyze --profile gemma4 --goal smoke --workdir "$TMP"
run "prune dry-run"    0 python3 "$S/ppd.py" prune "$TMP" 
run "bad profile"      1 python3 "$S/ppd.py" probe --profile does-not-exist

echo "== 3. output contract =="
D="$(ls -dt "$TMP"/prefill-perf/* | head -1)"
for f in TLDR.md REPORT.md manifest.json findings.json reports raw raw/SOURCES.txt; do
    [ -e "$D/$f" ] && printf '  ok   %s present\n' "$f" || { printf '  FAIL %s missing\n' "$f"; FAIL=1; }
done
python3 - "$D" <<'PY' || FAIL=1
import json, sys, os
d = sys.argv[1]
man = json.load(open(os.path.join(d, "manifest.json")))
fnd = json.load(open(os.path.join(d, "findings.json")))
tldr = open(os.path.join(d, "TLDR.md")).read()
ok = True
for k in ("model", "branch", "git_sha", "mesh", "tier", "goal", "capability_probe"):
    if man.get(k) is None:
        print(f"  FAIL manifest missing {k}"); ok = False
if ok: print("  ok   manifest has model/branch/sha/mesh/tier/goal/probe")
for k in ("level0", "level2", "reconciliation"):
    if k not in fnd: print(f"  FAIL findings missing {k}"); ok = False
if ok: print("  ok   findings has level0/level2/reconciliation")
# TLDR contract: answer first, 4-column table, method section, one levers section
head = tldr.split("## ")[0]
checks = [("answer before any '## ' heading", "slower than" in head or "x slower" in head),
          ("4-column term|A vs B|cause|whose table", "| cause | whose |" in tldr),
          ("'How this was obtained' section", "## How this was obtained" in tldr),
          ("exactly one levers section", tldr.count("## How to make it faster") == 1),
          ("levers section is last", tldr.rfind("## How to make it faster") > tldr.rfind("## How this was obtained"))]
for name, c in checks:
    print(f"  {'ok  ' if c else 'FAIL'} TLDR: {name}")
    ok = ok and c
sys.exit(0 if ok else 1)
PY

echo "== 4. assertion unit checks (synthetic, both directions) =="
python3 - "$S" <<'PY' || FAIL=1
import sys, os
sys.path.insert(0, sys.argv[1])
import assertions as A, helpers as H
prof = H.load_profile("gemma4")
bad = 0
def t(name, cond):
    global bad
    print(f"  {'ok  ' if cond else 'FAIL'} {name}")
    if not cond: bad = 1

def rows(gaps, cores="114", op="RingJointSDPADeviceOperation"):
    return [{"op": op, "key": op, "device_us": 100.0, "gap_us": g, "total_pct": 1.0,
             "cores": cores, "fidelity": "HiFi2", "device": "0", "raw": {}} for g in gaps]

t("A2 quiet on uniform gaps", A.A2_gap_and_total_pct(rows([0.5]*20)).status == "pass")
t("A2 warns on a 100x outlier", A.A2_gap_and_total_pct(rows([0.5]*19 + [1e6])).status == "warn")
t("A3 never calls Cores occupancy",
  "NOT occupancy" in A.A3_cores_is_not_occupancy(rows([0.5]), prof, 2048).detail)
t("A4 na on empty input", A.A4_utilization_columns([]).status == "na")
t("A5 pass/fail", A.A5_no_device_trace_profiler("pytest x").status == "pass"
                  and A.A5_no_device_trace_profiler("--device-trace-profiler").status == "fail")
t("A6 refuses a missing raw capture", A.A6_rerendered_both_sides(
    {"label":"a","raw_capture":"/nope","rendered_from_raw":True},
    {"label":"b","raw_capture":"/nope","rendered_from_raw":True}).status == "fail")
t("A6 refuses mismatched tool versions", A.A6_rerendered_both_sides(
    {"label":"a","raw_capture":__file__,"rendered_from_raw":True,"tool_version":"1.2.9"},
    {"label":"b","raw_capture":__file__,"rendered_from_raw":True,"tool_version":"1.3.0"}).status == "fail")
t("A7 fails with no PREDICTION.md", A.A7_prediction_registered("/nope","x").status == "fail")
t("A8 fails a moved control",
  A.A8_control_present([{"name":"c","expected_flat":True,"delta_pct":9.0}]).status == "fail")
t("A9 fails on unmatched prior context", A.A9_matched_prior_context(
    [{"chunk":2048,"chunk_idx":7,"prior_ctx":14336},
     {"chunk":8192,"chunk_idx":7,"prior_ctx":57344}]).status == "fail")
t("A10 fails outside tolerance", A.A10_closes_against_level0(200.0, 100.0, 15.0).status == "fail")
t("A10 passes inside tolerance", A.A10_closes_against_level0(105.0, 100.0, 15.0).status == "pass")
t("A11 flags inconsistent bases", A.A11_floor_basis(70.6, 70.6, 4).status == "warn")
t("A12 allows a declared cross-build",
  A.A12_same_build({"build":"x"},{"build":"y"}, allow_cross_build=True).status == "warn")
t("gate() blocks on any fail", not A.gate([A.A5_no_device_trace_profiler("--device-trace-profiler")]))

# fit refuses to invent a slope from one point
f1 = H.fit_two_term([(0, 928.2)])
t("fit_two_term refuses a 1-point slope", f1["slope_ms"] is None)
t("project returns None without a slope", H.project(928.2, None, 262144, 32768) is None)
# occupancy math against the published table
for c, want in ((2048, 29), (4096, 58), (8192, 58), (16384, 78), (32768, 93)):
    t(f"occupancy chunk {c} = {want}%", round(H.useful_occupancy(prof, c)["useful_pct"]) == want)
t("normalize_op_code strips the matmul M",
  H.normalize_op_code("Matmul 256 x 5376 x 5376") == "Matmul _x5376x5376")
sys.exit(bad)
PY

echo
if [ "$FAIL" = 0 ]; then echo "ALL TESTS PASSED"; else echo "TESTS FAILED"; fi
exit $FAIL
