#!/usr/bin/env python3
"""SPEC s6 as an executable regression test. Offline: no device, no new captures.

s6 is a regression test, not documentation. A build of this skill that cannot
reproduce the `a`/`slope` table and the four headline per-op results is not working.

Everything here reads artifacts that already exist on this box:
  - the level-0 `a`/`slope` table  <- the ctx_32k sweep log
  - the level-1 depth curves and layer-count differencing <- their run logs
  - the twelve level-2 rows and the four headline results <- the six Tracy captures,
    RE-RENDERED from the raw ops CSVs with tt-perf-report (never from a stored table)
  - A2 / A3 / A6 <- the same CSVs
"""

from __future__ import annotations

import json
import math
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import helpers as H
import assertions as A
import levels as LV


class Runner:
    def __init__(self, verbose=True):
        self.verbose = verbose
        self.passed = 0
        self.failed = 0
        self.skipped = 0

    def check(self, name, got, ref, tol_pct, unit=""):
        if got is None:
            return self.skip(name, "not measurable")
        err = H.pct_err(got, ref)
        ok = err is not None and abs(err) <= tol_pct
        self._say(ok, f"{name}: {got:.4g}{unit} vs {ref:.4g}{unit} ({err:+.2f}%, tol {tol_pct}%)")
        return ok

    def truth(self, name, ok, detail=""):
        self._say(ok, f"{name}{': ' + detail if detail else ''}")
        return ok

    def skip(self, name, why):
        self.skipped += 1
        if self.verbose:
            print(f"  SKIP {name}: {why}")
        return None

    def _say(self, ok, msg):
        if ok:
            self.passed += 1
        else:
            self.failed += 1
        if self.verbose or not ok:
            print(f"  {'ok  ' if ok else 'FAIL'} {msg}")

    def section(self, title):
        if self.verbose:
            print(f"\n{title}")


def _render_all(prof, outdir):
    """Re-render every capture in the profile from its RAW ops CSV (A6).

    Deliberately not reading perf_reports/*.csv: those are stored tables, and the whole
    point of A6 is that a stored number is not a measurement you can compare.
    """
    arts = prof["artifacts"]
    base = arts["runs_dir"]
    made = {}
    for tag, meta in arts["captures"].items():
        cdir = os.path.join(base, tag)
        ops = H.find_ops_csv(cdir)
        if not ops:
            continue
        made[tag] = {}
        for lt in prof["layers"]["types"]:
            start, stop = H.signpost_names(prof, lt, meta["chunk_idx"])
            out = os.path.join(outdir, f"{tag}_{lt}.csv")
            H.render_ops(ops, start, stop, out)
            made[tag][lt] = {"csv": out, "raw": ops}
    return made


def main(profile_name="gemma4", verbose=True, tolerance=None):
    prof = H.load_profile(profile_name)
    val = prof.get("validation")
    if not val:
        print(f"profile {profile_name} carries no `validation` block - nothing to regress against.")
        return 1
    tol = tolerance if tolerance is not None else val.get("tolerance_pct", 2.0)
    R = Runner(verbose)
    print(f"prefill-perf-debug validation - {prof['model']} (tolerance {tol}%)")
    print(f"source of truth: {val['source']}")

    # ── level 0 ──────────────────────────────────────────────────────────────
    R.section("Level 0 - two-term fit from the ctx_32k sweep")
    v0 = val["level0"]
    if not os.path.exists(v0["log"]):
        R.skip("level 0", f"log missing: {v0['log']}")
        l0 = None
    else:
        l0 = LV.level0(prof, [v0["log"]], isl=val["isl"])
        by_chunk = {r["chunk"]: r for r in l0["rows"]}
        for ref in v0["rows"]:
            r = by_chunk.get(ref["chunk"])
            if not r:
                R.skip(f"chunk {ref['chunk']}", "not in the sweep log")
                continue
            R.check(f"chunk {ref['chunk']:>5} a", r["a_ms"], ref["a_ms"], tol, " ms")
            if ref.get("slope_unverifiable"):
                R.truth(f"chunk {ref['chunk']:>5} slope reported UNVERIFIABLE, not extrapolated",
                        r.get("slope_ms") is None, ref["slope_unverifiable"][:90] + "...")
            else:
                R.check(f"chunk {ref['chunk']:>5} slope", r["slope_ms"], ref["slope_ms"], tol, " ms")
                R.check(f"chunk {ref['chunk']:>5} T({val['isl']//1024}k)", r.get("total_s"),
                        ref["total_s"], tol, " s")
                R.truth(f"chunk {ref['chunk']:>5} R^2 >= {v0['min_r2']}",
                        r["r2"] >= v0["min_r2"], f"{r['r2']:.6f}")
        d = v0.get("derived", {})
        if d and l0.get("floor"):
            R.check("chunk-invariant cost F", l0["floor"]["chunk_invariant_cost_ms"],
                    d["chunk_invariant_cost_ms"], 3.0, " ms")
            R.check("excess over ideal scaling", l0["floor"]["excess_over_ideal_scaling_ms"],
                    d["excess_over_ideal_ms"], 3.0, " ms")
            R.truth("A11: excess = 3/4 * F (the two are NOT the same number)",
                    abs(l0["floor"]["excess_over_ideal_scaling_ms"] /
                        l0["floor"]["chunk_invariant_cost_ms"] - 0.75) < 0.05)

    # ── level 1 ──────────────────────────────────────────────────────────────
    R.section("Level 1 - per-layer-type depth curves and layer-count differencing")
    v1 = val.get("level1", {})
    curves = [p for p in (prof["artifacts"].get("level1_logs") or {}).values() if os.path.exists(p)]
    if curves:
        l1 = LV.level1_depth_curves(prof, curves, l0)
        for ref in v1.get("depth_curves", []):
            e = l1["by_chunk"].get(str(ref["chunk"]))
            got = (e or {}).get("by_layer_type", {}).get(ref["layer"])
            if not got:
                R.skip(f"chunk {ref['chunk']} {ref['layer']}", "no curve")
                continue
            R.check(f"chunk {ref['chunk']} {ref['layer']:<6} a", got["a_ms"], ref["a_ms"], tol, " ms")
            if abs(ref["slope_ms"]) < 0.01:
                R.truth(f"chunk {ref['chunk']} {ref['layer']:<6} slope ~ 0 (the control)",
                        abs(got["slope_ms"]) < 0.01, f"{got['slope_ms']:+.4f} ms/index")
            else:
                R.check(f"chunk {ref['chunk']} {ref['layer']:<6} slope", got["slope_ms"],
                        ref["slope_ms"], tol, " ms")
        rc = v1.get("reconstruction")
        if rc:
            e = l1["by_chunk"].get(str(rc["chunk"]))
            if e:
                R.check(f"reconstructed whole-model slope @ {rc['chunk']}",
                        e["predicted_slope_ms"], rc["predicted_slope_ms"], rc["tol_pct"], " ms")
                if e.get("reconstruction_err_pct") is not None:
                    R.truth(f"reconstruction closes against level 0 within {rc['tol_pct']}%",
                            abs(e["reconstruction_err_pct"]) <= rc["tol_pct"],
                            f"{e['reconstruction_err_pct']:+.2f}%")
    else:
        R.skip("level 1 depth curves", "no curve logs on this box")

    lcl = prof["artifacts"].get("layer_count_logs")
    if lcl and v1.get("layer_count_differencing"):
        l1b = LV.level1_layer_counts(prof, lcl)
        for ref in v1["layer_count_differencing"]:
            e = l1b["by_chunk"].get(str(ref["chunk"]))
            if not e:
                R.skip(f"layer differencing chunk {ref['chunk']}", "no logs")
                continue
            R.check(f"chunk {ref['chunk']} per-layer L", e["L_ms"], ref["L_ms"], tol, " ms")
            R.check(f"chunk {ref['chunk']} non-layer F", e["F_ms"], ref["F_ms"], 10.0, " ms")
            R.truth(f"chunk {ref['chunk']} linearity in N tested (pairwise L spread < 2%)",
                    e["L_spread_pct"] < 2.0, f"{e['L_spread_pct']:.2f}%")

    # ── level 2 ──────────────────────────────────────────────────────────────
    R.section("Level 2 - per-op, re-rendered from the raw captures (A6)")
    v2 = val.get("level2", {})
    tmp = tempfile.mkdtemp(prefix="ppd-validate-")
    rendered = _render_all(prof, tmp)
    if not rendered:
        R.skip("level 2", "no raw captures found")
    else:
        loaded = {(t, lt): H.load_ops(d["csv"]) for t, per in rendered.items() for lt, d in per.items()}
        for ref in v2.get("rows", []):
            rows = loaded.get((ref["capture"], ref["layer"]))
            if rows is None:
                R.skip(f"{ref['capture']} {ref['layer']}", "capture missing")
                continue
            R.check(f"{ref['capture']:<15} {ref['layer']:<6} layer total",
                    H.total_device_us(rows) / 1000.0, ref["layer_ms"], tol, " ms")
            R.check(f"{ref['capture']:<15} {ref['layer']:<6} its SDPA",
                    H.op_device_us(rows, prof["growing_op"]["name"]) / 1000.0, ref["sdpa_ms"], tol, " ms")

        # ── the four headline results ────────────────────────────────────────
        R.section("The four headline results")
        hd = v2.get("headline", {})
        pairs = []
        for chunk in (2048, 4096, 8192):
            fl = f"floor_c{chunk}"
            dp = next((t for t, m in prof["artifacts"]["captures"].items()
                       if m["chunk"] == chunk and m["prior_ctx"] > 0), None)
            if fl in rendered and dp in rendered:
                pairs.append((chunk, fl, dp))

        # 1. exactly one op grows with context
        for chunk, fl, dp in pairs:
            f = loaded[(fl, "global")]
            d = loaded[(dp, "global")]
            delta = H.total_device_us(d) - H.total_device_us(f)
            g = (H.op_device_us(d, prof["growing_op"]["name"])
                 - H.op_device_us(f, prof["growing_op"]["name"]))
            share = 100.0 * g / delta
            R.check(f"1. chunk {chunk}: growth share of {prof['growing_op']['name'][:18]}",
                    share, hd["growth_share_pct"][str(chunk)], 1.0, "%")

        # 2. the sliding layer is context-invariant
        for chunk, fl, dp in pairs:
            f = H.total_device_us(loaded[(fl, "local")])
            d = H.total_device_us(loaded[(dp, "local")])
            got = 100.0 * (d - f) / f
            ref = hd["sliding_delta_pct"][str(chunk)]
            R.truth(f"2. chunk {chunk}: sliding layer flat ({got:+.2f}%, ref {ref:+.1f}%)",
                    abs(got - ref) < 0.5 and abs(got) < 1.0)

        # 3. occupancy passes a discriminating test
        ot = hd.get("occupancy_test", {})
        if len(pairs) >= 2:
            d2048 = next((p for p in pairs if p[0] == 2048), None)
            d8192 = next((p for p in pairs if p[0] == 8192), None)
            d4096 = next((p for p in pairs if p[0] == 4096), None)
            if d2048 and d8192:
                s2 = H.op_device_us(loaded[(d2048[2], "global")], prof["growing_op"]["name"])
                s8 = H.op_device_us(loaded[(d8192[2], "global")], prof["growing_op"]["name"])
                R.check("3. time ratio 2048/8192 at matched prior context", s2 / s8,
                        ot["time_ratio"], 1.0)
                R.truth(f"3. discriminates: {s2/s8:.3f} is between the neutral prediction "
                        f"{ot['predicted_neutral']} and the occupancy prediction {ot['predicted_occupancy']}",
                        ot["predicted_neutral"] < s2 / s8 < ot["predicted_occupancy"])
                R.check("3. efficiency loss vs work ratio", (s2 / s8) / ot["work_ratio"],
                        ot["efficiency_loss"], 2.0, "x")
                pts = [{"chunk": c, "chunk_idx": prof["artifacts"]["captures"][t]["chunk_idx"],
                        "prior_ctx": prof["artifacts"]["captures"][t]["prior_ctx"]}
                       for c, _, t in pairs]
                a9 = A.A9_matched_prior_context(pts)
                R.truth("3. A9: the comparison holds prior context fixed", a9.status == "pass", a9.detail)
            if d2048 and d4096:
                s2 = H.op_device_us(loaded[(d2048[2], "global")], prof["growing_op"]["name"])
                s4 = H.op_device_us(loaded[(d4096[2], "global")], prof["growing_op"]["name"])
                R.check("3. 2048 vs 4096 (cannot discriminate - both depth-1)", s2 / s4,
                        ot["pair_2048_4096"], 1.5)
        for chunk, ref in hd.get("useful_occupancy_pct", {}).items():
            occ = H.useful_occupancy(prof, int(chunk))
            R.check(f"3. useful occupancy @ chunk {chunk}", occ["useful_pct"], ref, 1.0, "%")

        # 4. the floor is chassis, not attention
        fa_ref = hd.get("floor_attribution")
        if fa_ref and len(pairs) >= 2:
            rows_by_chunk = {c: {lt: loaded[(fl, lt)] for lt in prof["layers"]["types"]}
                             for c, fl, _ in pairs}
            fa = LV.floor_attribution(prof, rows_by_chunk)
            R.truth(f"4. dominant floor owner is the {fa['dominant_layer_type']} layers",
                    fa["dominant_layer_type"] == fa_ref["dominant_layer_type"])
            for name, ref in fa_ref["share_pct"].items():
                got = fa["estimators"][name]["share_pct"][fa["dominant_layer_type"]]
                R.check(f"4. floor share via {name:<16}", got, ref, 1.0, "%")
            for name, ref in fa_ref["model_total_ms"].items():
                R.check(f"4. model floor total via {name:<16}",
                        fa["estimators"][name]["model_total_ms"], ref, 2.0, " ms")
            for lt, ref in fa_ref["per_layer_ms_per_op_clamped"].items():
                R.check(f"4. per-layer fixed cost, {lt:<6} (per-op clamped)",
                        fa["estimators"]["per_op_clamped"]["per_layer_ms"][lt], ref, 2.0, " ms")
            R.truth(f"4. the three estimators agree to {fa['agreement_pts']:.1f} pts "
                    f"(<= {fa_ref['max_spread_pts']}) - agreement IS the evidence",
                    fa["agreement_pts"] <= fa_ref["max_spread_pts"])
        # LayerNorm on 8-32 cores, and the collectives scaling near-ideally
        # ── cross-checks against level 0 (A10) ───────────────────────────────
        R.section("Cross-checks: level 2 closes against level 0 (A10)")
        for cc in v2.get("cross_check", []):
            R.check(cc["what"], cc["perop_ms"], cc["level0_ms"], cc["tol_pct"], " ms")

    # ── assertions ───────────────────────────────────────────────────────────
    R.section("Assertions A1-A12")
    va = val.get("assertions", {})
    tag = va.get("A2_gap_outlier_capture")
    if rendered and tag in rendered:
        rows = H.load_ops(rendered[tag]["global"]["csv"])
        a2 = A.A2_gap_and_total_pct(rows)
        R.truth("A2 detects the host-gap outlier that makes Total % unusable",
                a2.status == "warn" and va["A2_expect_outlier_op"] in a2.detail, a2.detail[:110])
        a3 = A.A3_cores_is_not_occupancy(rows, prof, prof["artifacts"]["captures"][tag]["chunk"])
        R.truth(f"A3 reports Cores={va['A3_cores_constant']} AND the real occupancy",
                str(va["A3_cores_constant"]) in a3.detail and "occupancy" in a3.detail, a3.detail[:110])
        a4 = A.A4_utilization_columns(rows)
        R.truth("A4 refuses the utilization columns (empty on this path)", a4.status == "warn",
                a4.detail[:110])
    a5 = A.A5_no_device_trace_profiler("python -m tracy -r -p -v --device-trace-profiler -m pytest x")
    R.truth("A5 rejects --device-trace-profiler", a5.status == "fail")
    a5b = A.A5_no_device_trace_profiler(LV.build_capture_cmd(prof, 8192, 6, "both", 262144, "/tmp/x"))
    R.truth("A5 passes the capture command this skill builds", a5b.status == "pass")

    # A6: both sides re-rendered, and the false-regression story
    pair = va.get("A6_pair")
    if pair and all(os.path.exists(p) for p in pair):
        bad = A.A6_rerendered_both_sides(
            {"label": "old writeup", "raw_capture": None, "rendered_from_raw": False},
            {"label": "this branch", "raw_capture": pair[1], "rendered_from_raw": True})
        R.truth("A6 refuses a number lifted from a writeup", bad.status == "fail", bad.detail[:110])
        good = A.A6_rerendered_both_sides(
            {"label": "pre-halo", "raw_capture": pair[0], "rendered_from_raw": True,
             "tool_version": H.perf_report_version()},
            {"label": "multi-hop", "raw_capture": pair[1], "rendered_from_raw": True,
             "tool_version": H.perf_report_version()})
        R.truth("A6 accepts two sides re-rendered with one tool", good.status == "pass")
        old = H.op_device_us(H.load_ops(pair[0]), prof["growing_op"]["name"])
        new = H.op_device_us(H.load_ops(pair[1]), prof["growing_op"]["name"])
        R.check("A6: the re-rendered cross-branch SDPA delta", 100.0 * (new - old) / old,
                va["A6_expected_sdpa_delta_pct"], 30.0, "%")
        R.truth(f"A6: and NOT the false +{va['A6_false_regression_pct']:.0f}% the stored table implied",
                abs(100.0 * (new - old) / old) < 5.0)
    ref = va.get("A12_reference_captures_straddle")
    if ref:
        fb = H.capture_build(os.path.join(prof["artifacts"]["runs_dir"], "floor_c8192"))
        db = H.capture_build(os.path.join(prof["artifacts"]["runs_dir"], "deep_c8192_i6"))
        R.truth(f"A12 reads the capture sha out of the run log "
                f"({fb['sha']} / {db['sha']})",
                fb["sha"] == ref["floor_sha"] and db["sha"] == ref["deep_sha"])
        R.truth("A12 DETECTS that the reference floor/deep captures straddle a code change "
                f"({ref['straddled_commit']}) - the published subtraction is cross-build",
                A.A12_same_build({"build": fb["sha"]}, {"build": db["sha"]}).status == "fail")
    a12 = A.A12_same_build({"build": "svuckovic/gemma4-prefill-model"},
                           {"build": "kmabee/gemma4-swa-multihop-halo"})
    R.truth("A12 blocks a silent cross-build per-op comparison", a12.status == "fail")
    a1_bad = A.A1_bound_claim("fabric", prof["ablation_catalogue"])
    R.truth("A1 refuses 'fabric-bound' - no ablation varied fabric", a1_bad.status == "fail",
            a1_bad.detail[:100])
    a1_ok = A.A1_bound_claim("MAC passes", prof["ablation_catalogue"])
    R.truth("A1 licenses 'MAC-bound' - two fidelity ablations moved it", a1_ok.status == "pass",
            a1_ok.detail[:100])
    a7 = A.A7_prediction_registered(prof["artifacts"]["runs_dir"], "occupancy")
    R.truth("A7 finds the pre-registered PREDICTION.md", a7.status in ("pass", "warn"), a7.detail[:90])
    a8 = A.A8_control_present([{"name": "sliding layer", "expected_flat": True, "delta_pct": 0.8}])
    R.truth("A8 accepts the sliding layer as the control", a8.status == "pass")
    a8b = A.A8_control_present([])
    R.truth("A8 refuses a run with no control", a8b.status == "fail")
    a11 = A.A11_floor_basis(70.6, 94.2, 4)
    R.truth("A11 accepts 70.6 ms excess against a 94.2 ms chunk-invariant cost", a11.status == "pass")
    a11b = A.A11_floor_basis(excess_ms=70.6)
    R.truth("A11 converts a lone 'floor' figure and demands a label", a11b.status == "warn",
            a11b.detail[:90])

    print(f"\n{'=' * 64}")
    print(f"validation: {R.passed} passed, {R.failed} failed, {R.skipped} skipped")
    if R.failed:
        print("A build that cannot reproduce SPEC s6 is not working. Fix before shipping.")
    print("=" * 64)
    return 1 if R.failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "gemma4"))
