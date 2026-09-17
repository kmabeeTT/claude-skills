#!/usr/bin/env python3
"""Levels 0, 1 and 2 of the prefill-perf funnel, plus the device-run driver.

Every level must reconcile to the level above it, and the residual is reported.
A level that does not close is a finding, not something to paper over.
"""

from __future__ import annotations

import glob
import json
import math
import os
import shlex
import subprocess
import time

import helpers as H
import assertions as A


# ── device runs: detached, serialised, never parallel ────────────────────────


def _env_prefix(profile):
    ef = profile.get("env_file")
    return f"source {shlex.quote(ef)} && " if ef and os.path.exists(ef) else ""


def build_e2e_cmd(profile, chunk, ctx, extra_env=None):
    e2e = profile["e2e"]
    node = e2e["node_id"].format(ctx_k=ctx // 1024, chunk=chunk, mesh=profile["mesh"]["id"])
    nodeid = f'{e2e["test_file"]}::{e2e["test_name"]}[{node}]'
    py = profile.get("python", "python3").format(tree=profile["tree"])
    env = " ".join(f"{k}={shlex.quote(str(v))}" for k, v in (extra_env or {}).items())
    return f'{env} {shlex.quote(py)} -m pytest {shlex.quote(nodeid)} -sv'.strip()


def build_capture_cmd(profile, chunk, chunk_idx, layer_type, ctx, out_dir):
    """Tracy capture of the isolated-layer benchmark. A5: no --device-trace-profiler."""
    lb = profile["layer_bench"]
    node = lb["node_id"].format(idx=chunk_idx, layer_type=layer_type, chunk=chunk,
                                ctx_k=ctx // 1024, mesh=profile["mesh"]["id"])
    nodeid = f'{lb["test_file"]}::{lb["test_name"]}[{node}]'
    py = profile.get("python", "python3").format(tree=profile["tree"])
    cmd = (f'TT_METAL_PROFILER_PROGRAM_SUPPORT_COUNT=20000 {shlex.quote(py)} -m tracy -r -p -v '
           f'-o {shlex.quote(os.path.join(out_dir, "profiler"))} '
           f'-m pytest {shlex.quote(nodeid)} -sv')
    assert "--device-trace-profiler" not in cmd
    return cmd


def launch_detached(profile, cmd, log_path):
    """Start a device run detached and return immediately.

    A device job must NEVER run in a foreground tool call with a timeout: a killed
    wrapper is a SIGKILL mid-fabric, and the next mesh open dies with "Timed out while
    waiting for active ethernet core N-N to become active again". Poll the log instead.
    """
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    tree = profile["tree"]
    full = f'{_env_prefix(profile)}cd {shlex.quote(tree)} && {cmd}'
    with open(log_path, "a") as fh:
        fh.write(f"### {time.strftime('%Y-%m-%dT%H:%M:%S%z')} cmd: {full}\n")
        git = H.git_info(tree)
        fh.write(f"### git: {git['sha']} {git['branch']} dirty={git['dirty']}\n")
    p = subprocess.Popen(["setsid", "nohup", "bash", "-lc", f'{full} >> {shlex.quote(log_path)} 2>&1'],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         stdin=subprocess.DEVNULL, start_new_session=True)
    return {"pid": p.pid, "log": log_path, "cmd": full}


def device_busy():
    """Who holds a TT device. Empty output does NOT mean free.

    Since a hidepid=2 hardening baseline landed on these boxes, ps/fuser/pkill see only
    your own PIDs, so another user's holder is invisible. If acquisition fails with no
    visible holder, say so rather than debugging the model.
    """
    devs = sorted(glob.glob("/dev/tenstorrent/*"))
    holders = {}
    for d in devs:
        try:
            r = subprocess.run(["fuser", d], capture_output=True, text=True, timeout=20)
            pids = r.stdout.split() + r.stderr.replace(f"{d}:", "").split()
            holders[d] = [p for p in pids if p.isdigit()]
        except Exception:
            holders[d] = []
    return {"devices": devs, "holders": holders,
            "caveat": "empty holders does NOT prove the device is free: hidepid=2 hides other "
                      "users' PIDs. If acquisition fails with nothing visible, suspect an unseen holder."}


def disk_free(path):
    st = os.statvfs(path)
    return st.f_bavail * st.f_frsize


# ── level 0 ──────────────────────────────────────────────────────────────────


def level0(profile, logs, isl=None, reference_chunk=None):
    """Fit t_i = a + slope*i per chunk size, project to ISL, and report the two terms."""
    isl = isl or profile.get("validation", {}).get("isl", 262144)
    series = {}
    sources = {}
    for lg in logs:
        for chunk, pts in H.parse_e2e_log(lg, profile).items():
            series.setdefault(chunk, []).extend(pts)
            sources.setdefault(chunk, []).append(lg)
    rows = []
    for chunk in sorted(series):
        f = H.fit_two_term(series[chunk])
        proj = H.project(f["a_ms"], f["slope_ms"], isl, chunk)
        row = {"chunk": chunk, "sources": sources[chunk], **f}
        if proj:
            row.update(proj)
        else:
            row["unverifiable"] = (
                f"only {f['n']} chunk(s) measured at chunk {chunk}: the prefix slope is not "
                f"determinable and is NOT extrapolated. Run a longer context to fit it.")
        rows.append(row)
    out = {"level": 0, "isl": isl, "rows": rows}

    # the two terms, as ratios against the best total
    fitted = [r for r in rows if r.get("total_s")]
    if fitted:
        explicit = next((r for r in fitted if r["chunk"] == reference_chunk), None)
        best = explicit or min(fitted, key=lambda r: r["total_s"])
        out["reference_basis"] = "requested" if explicit else "best total"
        out["reference_chunk"] = best["chunk"]
        for r in fitted:
            r["vs_reference"] = {
                "total": r["total_s"] / best["total_s"],
                "per_chunk_term": r["per_chunk_term_s"] / best["per_chunk_term_s"],
                "prefix_term": r["prefix_term_s"] / best["prefix_term_s"] if best["prefix_term_s"] else None,
            }

    # A11: both floor bases, explicitly labelled and computed on the SAME chunk pair
    fit_chunks = profile.get("floor_fit_chunks") or sorted(
        c for c in (r["chunk"] for r in rows if r.get("a_ms") is not None))[:3]
    by_chunk = {r["chunk"]: r["a_ms"] for r in rows
                if r.get("a_ms") is not None and r["chunk"] in fit_chunks}
    cs = sorted(by_chunk)
    if len(cs) >= 2:
        lo, hi = cs[0], cs[-1]
        ratio = hi / lo
        # endpoint solve: a(C) = F + k*C on (lo, hi). This is the basis that makes
        # excess = (1 - 1/r)*F an identity rather than an approximation.
        k = (by_chunk[hi] - by_chunk[lo]) / (hi - lo)
        F = by_chunk[lo] - k * lo
        excess = by_chunk[lo] - by_chunk[hi] / ratio
        # every pair, so the spread is visible: a(C) is CONCAVE, not affine, so the
        # intercept depends on which pair you solve on. Do not extrapolate to C = 0.
        pairwise = []
        for i in range(len(cs)):
            for j in range(i + 1, len(cs)):
                ci, cj = cs[i], cs[j]
                kk = (by_chunk[cj] - by_chunk[ci]) / (cj - ci)
                pairwise.append({"pair": [ci, cj], "F_ms": by_chunk[ci] - kk * ci})
        Fs = [p["F_ms"] for p in pairwise]
        out["floor"] = {
            "chunk_invariant_cost_ms": F,
            "excess_over_ideal_scaling_ms": excess,
            "ratio": ratio,
            "basis_pair": [lo, hi],
            "fitted_over_chunks": cs,
            "pairwise_F_ms": pairwise,
            "F_spread_pct": 100.0 * (max(Fs) - min(Fs)) / abs(F) if F else None,
            "note": "TWO DIFFERENT NUMBERS (A11): excess = (1 - 1/r) * F. a(C) is concave, "
                    "so F depends on the pair solved - see pairwise_F_ms; never extrapolate to C=0.",
        }
        out["assertions"] = [A.A11_floor_basis(excess, F, ratio).to_dict()]

    # R^2 gate: the fit is the instrument of record, so a poor one invalidates everything above it
    bad = [r for r in rows if r.get("r2") is not None and r["r2"] < profile.get("validation", {})
           .get("level0", {}).get("min_r2", 0.999)]
    out["fit_quality_warnings"] = [
        {"chunk": r["chunk"], "r2": r["r2"],
         "detail": "t_i is not linear in i here; the two-term model does not describe this run"}
        for r in bad]
    return out


def render_level0(res):
    L = [f"Level 0 - two-term fit  T = N*a + slope*N(N-1)/2   (ISL {res['isl']:,})", ""]
    L.append(f"{'chunk':>7} {'N':>5} {'a (ms)':>9} {'slope':>9} {'R^2':>8} {'per-chunk':>10} "
             f"{'prefix':>9} {'total':>9}")
    L.append("-" * 74)
    for r in res["rows"]:
        if r.get("total_s") is None:
            L.append(f"{r['chunk']:>7} {r.get('n',0):>5} {r['a_ms']:>9.1f} {'--':>9} {'--':>8} "
                     f"{'--':>10} {'--':>9} {'--':>9}   <- slope UNVERIFIABLE")
            continue
        L.append(f"{r['chunk']:>7} {r['n_chunks']:>5} {r['a_ms']:>9.1f} {r['slope_ms']:>9.3f} "
                 f"{r['r2']:>8.5f} {r['per_chunk_term_s']:>9.2f}s {r['prefix_term_s']:>8.2f}s "
                 f"{r['total_s']:>8.2f}s")
    if res.get("reference_chunk"):
        L += ["", f"ratios vs chunk {res['reference_chunk']} ({res.get('reference_basis','best total')}):"]
        for r in res["rows"]:
            v = r.get("vs_reference")
            if v:
                L.append(f"  {r['chunk']:>7}: total {v['total']:.2f}x = per-chunk {v['per_chunk_term']:.2f}x "
                         f"x prefix {v['prefix_term']:.2f}x" if v["prefix_term"] else
                         f"  {r['chunk']:>7}: total {v['total']:.2f}x")
    f = res.get("floor")
    if f:
        L += ["", f"floor (A11 - two different numbers, both stated):",
              f"  chunk-invariant cost F          = {f['chunk_invariant_cost_ms']:.1f} ms "
              f"(affine fit of a(C) over {f['fitted_over_chunks']})"]
        if f.get("excess_over_ideal_scaling_ms"):
            L.append(f"  excess over ideal token scaling = {f['excess_over_ideal_scaling_ms']:.1f} ms "
                     f"= {1-1/f['ratio']:.2f} x F")
    for w in res.get("fit_quality_warnings", []):
        L.append(f"  WARNING chunk {w['chunk']}: R^2 = {w['r2']:.5f} - {w['detail']}")
    for r in res["rows"]:
        if r.get("unverifiable"):
            L.append(f"  NOTE chunk {r['chunk']}: {r['unverifiable']}")
    return "\n".join(L)


# ── level 1 ──────────────────────────────────────────────────────────────────


def level1_depth_curves(profile, logs, level0_res=None):
    """Per-layer-type depth curves -> which layer type owns each term.

    The in-tree route. Reconstructs the whole-model slope from the per-type slopes
    weighted by layer count, and reconciles against level 0.
    """
    out = {"level": 1, "route": "per-layer-type depth curves", "by_chunk": {}}
    for lg in logs:
        curves, kv = H.parse_layer_log(lg, profile)
        if not curves:
            continue
        # chunk size is not in the RESULT line; take it from kv_actual_global spacing
        chunk = None
        for lt, m in kv.items():
            idxs = sorted(i for i in m if i > 0)
            if idxs:
                chunk = m[idxs[0]] // idxs[0]
                break
        rec = H.reconstruct_model_slope(curves, profile)
        entry = {"log": lg, "chunk": chunk, **rec}
        if level0_res and chunk:
            l0 = next((r for r in level0_res["rows"] if r["chunk"] == chunk), None)
            if l0 and l0.get("slope_ms"):
                entry["measured_slope_ms"] = l0["slope_ms"]
                entry["reconstruction_err_pct"] = H.pct_err(rec["predicted_slope_ms"], l0["slope_ms"])
                entry["assertion"] = A.A10_closes_against_level0(
                    rec["predicted_slope_ms"], l0["slope_ms"], 5.0,
                    f"reconstructed slope at chunk {chunk}").to_dict()
        # A8: a layer type whose slope is ~0 is the control
        controls = [{"name": f"{lt} layer slope", "expected_flat": True,
                     "delta_pct": 100.0 * p["slope_ms"] * max(1, p["n"] - 1) / p["a_ms"]}
                    for lt, p in rec["by_layer_type"].items()
                    if p.get("slope_ms") is not None and p.get("a_ms")
                    and abs(p["slope_ms"]) * max(1, p["n"] - 1) < 0.02 * p["a_ms"]]
        if controls:
            entry["control"] = A.A8_control_present(controls).to_dict()
        out["by_chunk"][str(chunk)] = entry
    return out


def level1_layer_counts(profile, logs_by_chunk):
    """Layer-count differencing: a(N) = F + N*L. ASSISTED route on models with no override.

    `logs_by_chunk` is {chunk: {layer_count: log_path}}.
    """
    out = {"level": 1, "route": "layer-count differencing", "by_chunk": {},
           "caveat": profile.get("layer_count_override", {}).get("reason")}
    for chunk, by_n in logs_by_chunk.items():
        a_by_n = {}
        for n, lg in by_n.items():
            s = H.parse_e2e_log(lg, profile)
            key = int(chunk)
            if key in s:
                a_by_n[int(n)] = H.fit_two_term(s[key])["a_ms"]
        sol = H.layer_count_difference(a_by_n)
        if sol:
            sol["a_by_layer_count"] = a_by_n
            sol["linearity"] = ("tested: pairwise L agrees to "
                                f"{sol['L_spread_pct']:.1f}%, F to {sol['F_spread_pct']:.1f}%")
            out["by_chunk"][str(chunk)] = sol
    return out


def render_level1(res):
    L = [f"Level 1 - {res['route']}", ""]
    for chunk, e in sorted(res.get("by_chunk", {}).items(), key=lambda kv: int(kv[0] or 0)):
        if res["route"].startswith("per-layer"):
            L.append(f"chunk {chunk}:")
            for lt, p in e["by_layer_type"].items():
                sl = f"{p['slope_ms']:+.4f}" if p["slope_ms"] is not None else "--"
                L.append(f"    {lt:<8} x{p['count']:<3} a={p['a_ms']:.2f} ms  slope={sl} ms/index  "
                         f"R^2={p['r2']:.4f}  ({p['n']} points)")
            L.append(f"    reconstructed whole-model slope = {e['predicted_slope_ms']:.4f} ms/index")
            if e.get("measured_slope_ms"):
                L.append(f"    measured (level 0)              = {e['measured_slope_ms']:.4f} ms/index  "
                         f"-> {e['reconstruction_err_pct']:+.1f}%")
            if e.get("control"):
                L.append(f"    {e['control']['detail']}")
        else:
            L.append(f"chunk {chunk}: L = {e['L_ms']:.3f} ms/layer, F (non-layer) = {e['F_ms']:.2f} ms")
            L.append(f"    a by layer count: {e['a_by_layer_count']}")
            L.append(f"    {e['linearity']}")
    if res.get("caveat"):
        L += ["", f"NOTE: {res['caveat']}"]
    return "\n".join(L)


# ── level 2 ──────────────────────────────────────────────────────────────────


def render_capture(profile, capture_dir, chunk_idx, layer_types, out_dir, tag):
    """Re-render one capture's per-layer tables from the RAW ops CSV (A6)."""
    ops_csv = H.find_ops_csv(capture_dir)
    if not ops_csv:
        raise SystemExit(f"no ops_perf_results_*.csv under {capture_dir} - raw capture missing, "
                         f"so no valid comparison is possible (A6)")
    os.makedirs(out_dir, exist_ok=True)
    made = {}
    for lt in layer_types:
        start, stop = H.signpost_names(profile, lt, chunk_idx)
        out_csv = os.path.join(out_dir, f"{tag}_{lt}.csv")
        meta = H.render_ops(ops_csv, start, stop, out_csv)
        H.render_table(ops_csv, start, stop, os.path.join(out_dir, f"{tag}_{lt}.txt"))
        made[lt] = {"csv": out_csv, "raw_capture": ops_csv, "rendered_from_raw": True,
                    "tool_version": meta["tool_version"], "signposts": [start, stop]}
    return made


def level2(profile, pairs, out_dir, rendered=None):
    """Per-op attribution: capture at depth 0 AND at depth D, subtract.

    `pairs` is a list of dicts:
      {"name": "c8192", "chunk": 8192,
       "floor": {"dir": ..., "chunk_idx": 0,  "prior_ctx": 0},
       "deep":  {"dir": ..., "chunk_idx": 6,  "prior_ctx": 49152}}
    `rendered` optionally supplies already-rendered CSVs: {tag: {layer_type: csv_path}}.
    """
    layer_types = list(profile["layers"]["types"])
    res = {"level": 2, "pairs": [], "assertions": []}
    # A9 across the deep points of all pairs
    deep_pts = [{"chunk": p["chunk"], "chunk_idx": p["deep"]["chunk_idx"],
                 "prior_ctx": p["deep"]["prior_ctx"]} for p in pairs]
    if len(deep_pts) > 1:
        res["assertions"].append(A.A9_matched_prior_context(deep_pts).to_dict())

    for p in pairs:
        entry = {"name": p["name"], "chunk": p["chunk"],
                 "prior_ctx": p["deep"].get("prior_ctx"), "layers": {}}
        sides = {}
        for side in ("floor", "deep"):
            spec = p[side]
            tag = spec.get("tag") or f'{p["name"]}_{side}'
            if rendered and tag in rendered:
                sides[side] = {lt: {"csv": c, "raw_capture": spec.get("dir"),
                                    "rendered_from_raw": bool(spec.get("dir")),
                                    "tool_version": H.perf_report_version()}
                               for lt, c in rendered[tag].items()}
            else:
                sides[side] = render_capture(profile, spec["dir"], spec["chunk_idx"],
                                             layer_types, out_dir, tag)
        for lt in layer_types:
            fr = H.load_ops(sides["floor"][lt]["csv"])
            dr = H.load_ops(sides["deep"][lt]["csv"])
            fg, dg = H.group_ops(fr), H.group_ops(dr)
            ftot, dtot = H.total_device_us(fr), H.total_device_us(dr)
            delta = dtot - ftot
            growing = profile.get("growing_op", {}).get("name", "")
            gdelta = H.op_device_us(dr, growing) - H.op_device_us(fr, growing)
            entry["layers"][lt] = {
                "floor_ms": ftot / 1000.0,
                "deep_ms": dtot / 1000.0,
                "delta_ms": delta / 1000.0,
                "delta_pct": 100.0 * delta / ftot if ftot else None,
                "growing_op": growing,
                "growing_op_floor_ms": H.op_device_us(fr, growing) / 1000.0,
                "growing_op_deep_ms": H.op_device_us(dr, growing) / 1000.0,
                # a growth share is meaningless when the layer barely moved: noise/noise.
                # Below 2% the layer is the control, and it is labelled as one.
                "growth_share_pct": (100.0 * gdelta / delta)
                                    if (ftot and abs(100.0 * delta / ftot) >= 2.0) else None,
                "is_control": bool(ftot and abs(100.0 * delta / ftot) < 2.0),
                "by_op": H.subtract(dg, fg)[:12],
                "floor_by_op": [{"op": k, "n": v["n"], "device_us": v["device_us"],
                                 "cores": v["cores"], "fidelity": v["fidelity"]}
                                for k, v in sorted(fg.items(), key=lambda kv: -kv[1]["device_us"])],
                "sources": {"floor": sides["floor"][lt], "deep": sides["deep"][lt]},
            }
            entry.setdefault("_rows", []).append((lt, fr, dr))
        # per-capture assertions, once per pair, on the deep global capture
        main_lt = layer_types[0]
        drows = H.load_ops(sides["deep"][main_lt]["csv"])
        for a in A.run_capture_checks(drows, profile, p["chunk"]):
            a.name = f'{a.name} [{p["deep"].get("tag", p["name"])}/{main_lt}]'
            res["assertions"].append(a.to_dict())
        entry.pop("_rows", None)
        res["pairs"].append(entry)

    # A8: a layer type that should not move with context is the control
    controls = []
    for e in res["pairs"]:
        for lt, d in e["layers"].items():
            if profile["layers"]["types"][lt].get("note", "").startswith("context-invariant"):
                controls.append({"name": f'{lt} layer @ chunk {e["chunk"]}',
                                 "expected_flat": True, "delta_pct": d["delta_pct"]})
    if controls:
        res["assertions"].append(A.A8_control_present(controls).to_dict())

    # occupancy at each chunk, from the op's own work-unit math (A3)
    res["occupancy"] = {str(p["chunk"]): H.useful_occupancy(profile, p["chunk"]) for p in pairs}

    # who owns the per-chunk floor, three ways (their agreement is the evidence)
    if len(pairs) >= 2:
        rows_by_chunk = {}
        for p in pairs:
            tag = p["floor"].get("tag") or f'{p["name"]}_floor'
            rows_by_chunk[p["chunk"]] = {
                lt: H.load_ops(os.path.join(out_dir, f"{tag}_{lt}.csv")) for lt in layer_types}
        try:
            res["floor_attribution"] = floor_attribution(profile, rows_by_chunk)
        except (OSError, KeyError):
            res["floor_attribution"] = None
    return res


def level2_reconcile(profile, l2, l0):
    """A10: every per-op attribution must close against level 0 within ~15%.

    Two independent reconciliations per chunk size:
      - the per-chunk floor, summing each layer type's depth-0 cost x its layer count,
        against level 0's `a`;
      - the prefix slope, from the growing op's growth per chunk-index x the count of
        the layer type that owns it, against level 0's `slope`.

    Per-op sums OVERSTATE: the isolated-layer harness has no inter-layer overlap and
    pays staging ops the real model pays once per chunk. The residual is the point.
    """
    out = []
    counts = {k: v["count"] for k, v in profile["layers"]["types"].items()}
    for e in l2["pairs"]:
        row = next((r for r in l0["rows"] if r["chunk"] == e["chunk"]), None)
        if not row or row.get("a_ms") is None:
            continue
        perop_a = sum(counts[lt] * d["floor_ms"] for lt, d in e["layers"].items())
        out.append(A.A10_closes_against_level0(
            perop_a, row["a_ms"], 15.0,
            f'chunk {e["chunk"]} per-chunk floor (sum of per-op x layer count)').to_dict())

        prior = e.get("prior_ctx")
        if row.get("slope_ms") and prior:
            n_idx = prior / e["chunk"]
            implied = 0.0
            for lt, d in e["layers"].items():
                growth = d["growing_op_deep_ms"] - d["growing_op_floor_ms"]
                implied += counts[lt] * growth / n_idx
            out.append(A.A10_closes_against_level0(
                implied, row["slope_ms"], 20.0,
                f'chunk {e["chunk"]} prefix slope implied by {profile["growing_op"]["name"]}').to_dict())
    return out


def render_level2(profile, res):
    L = ["Level 2 - per-op, depth 0 vs depth D (Device Time sums; A2: Total % is unusable here)", ""]
    for e in res["pairs"]:
        L.append(f"chunk {e['chunk']}  ({e['name']})")
        for lt, d in e["layers"].items():
            L.append(f"  {lt:<8} layer {d['floor_ms']:7.3f} -> {d['deep_ms']:7.3f} ms  "
                     f"({d['delta_pct']:+6.1f}%)   {d['growing_op'].replace('DeviceOperation','')}: "
                     f"{d['growing_op_floor_ms']:6.3f} -> {d['growing_op_deep_ms']:6.3f} ms"
                     + (f"   growth share {d['growth_share_pct']:.1f}%"
                        if d["growth_share_pct"] is not None else "   [CONTROL: flat]"))
        occ = res.get("occupancy", {}).get(str(e["chunk"]))
        if occ:
            L.append(f"  useful occupancy {occ['useful_pct']:.0f}%  ({occ['work_units']} units / "
                     f"{occ['slots']} slots, depth {occ['depth']}) - the Cores column cannot show this")
        L.append("")
    fa = res.get("floor_attribution")
    if fa:
        dom = fa["dominant_layer_type"]
        n = profile["layers"]["types"][dom]["count"]
        lo, hi = fa["share_pct_range"]
        L.append(f"per-chunk floor: {lo:.0f}-{hi:.0f}% is the {n} {dom} layers, BY COUNT "
                 f"(three estimators over chunks {fa['basis_pair']}, agreeing to {fa['agreement_pts']:.1f} pts)")
        for name, e in fa["estimators"].items():
            per = ", ".join(f"{lt} {v:.2f} ms" for lt, v in e["per_layer_ms"].items())
            L.append(f"    {name:<16} model floor {e['model_total_ms']:6.1f} ms  "
                     f"{dom} share {e['share_pct'][dom]:.1f}%   ({per})")
        L.append("")
    if res.get("assertions"):
        L.append("assertions:")
        for a in res["assertions"]:
            L.append(f"  [{a['status'].upper():<4}] {a['id']} {a['name']}: {a['detail']}")
    return "\n".join(L)


def floor_attribution(profile, floor_rows_by_chunk):
    """Split the per-chunk floor across layer types, three ways, and report the spread.

    `floor_rows_by_chunk` is {chunk: {layer_type: [op rows]}} from depth-0 captures.

    Three estimators, because no single one is authoritative and their agreement IS the
    evidence (CHUNK_SIZE_ANATOMY s5.0b):

      excess_in_range   a(C_lo) - a(C_hi)/r per layer. In range, no extrapolation to
                        C = 0. The method doc's own recommendation.
      affine_layer      least-squares F of a(C) = F + k*C on the layer total. Extrapolates,
                        and a(C) is concave, so it reads high.
      per_op_clamped    the same fit PER OP with F clamped at >= 0, then summed. This is
                        what produced the published 1.94 / 1.87 ms and the 83% figure. The
                        clamp is a real upward bias on layers holding a strongly convex op.
    """
    chunks = sorted(floor_rows_by_chunk)
    if len(chunks) < 2:
        return None
    lo, hi = chunks[0], chunks[-1]
    ratio = hi / lo
    counts = {k: v["count"] for k, v in profile["layers"]["types"].items()}

    def _lsq(pts):
        n = len(pts)
        sx = sum(x for x, _ in pts)
        sy = sum(y for _, y in pts)
        sxx = sum(x * x for x, _ in pts)
        sxy = sum(x * y for x, y in pts)
        den = n * sxx - sx * sx
        if den == 0:
            return pts[0][1], 0.0
        k = (n * sxy - sx * sy) / den
        return (sy - k * sx) / n, k

    est = {}
    for name in ("excess_in_range", "affine_layer", "per_op_clamped"):
        per_layer = {}
        for lt in counts:
            tots = {c: H.total_device_us(floor_rows_by_chunk[c][lt]) / 1000.0 for c in chunks}
            if name == "excess_in_range":
                per_layer[lt] = tots[lo] - tots[hi] / ratio
            elif name == "affine_layer":
                per_layer[lt] = _lsq([(c, tots[c]) for c in chunks])[0]
            else:
                groups = {c: H.group_ops(floor_rows_by_chunk[c][lt]) for c in chunks}
                keys = {k for c in chunks for k in groups[c]}
                s = 0.0
                for k in keys:
                    pts = [(c, groups[c][k]["device_us"] / 1000.0) for c in chunks if k in groups[c]]
                    if len(pts) < 2:
                        continue
                    s += max(0.0, _lsq(pts)[0])
                per_layer[lt] = s
        total = sum(counts[lt] * per_layer[lt] for lt in counts)
        est[name] = {
            "per_layer_ms": per_layer,
            "model_total_ms": total,
            "share_pct": {lt: 100.0 * counts[lt] * per_layer[lt] / total for lt in counts} if total else {},
        }
    dom = max(counts, key=lambda lt: est["per_op_clamped"]["share_pct"].get(lt, 0))
    shares = [e["share_pct"].get(dom, 0.0) for e in est.values()]
    return {
        "basis_pair": [lo, hi],
        "estimators": est,
        "dominant_layer_type": dom,
        "share_pct_range": [min(shares), max(shares)],
        "agreement_pts": max(shares) - min(shares),
        "note": "three independent estimators; their agreement is the evidence. If they "
                "disagree by more than a few points, report the range, not one of them.",
    }
