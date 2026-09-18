#!/usr/bin/env python3
"""Shared parsing / fitting / per-op utilities for the prefill-perf-debug skill.

Nothing here touches a device. Everything takes a log file, a profiler CSV or a model
profile and returns numbers, so every level can be developed and regression-tested
offline against captures that already exist.

Two-term model used throughout:

    t_i = a + slope * i          per-chunk device time at chunk index i
    T(ISL, C) = N*a + slope*N*(N-1)/2     with N = ISL/C

`a` is TTFT and `slope` is what kills long-context throughput. They are the only two
numbers a deployment cares about, and every deeper level must reconcile back to them.
"""

from __future__ import annotations

import csv
import glob
import json
import math
import os
import re
import shutil
import subprocess
import sys
from collections import OrderedDict

SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
PROFILE_DIR = os.path.join(SKILL_DIR, "profiles")


# ── model profiles ───────────────────────────────────────────────────────────


def load_profile(name_or_path):
    """Load a model profile by short name (profiles/<name>.json) or by path."""
    cand = name_or_path
    if not os.path.exists(cand):
        cand = os.path.join(PROFILE_DIR, f"{name_or_path}.json")
    if not os.path.exists(cand):
        raise SystemExit(
            f"no such profile: {name_or_path}\n"
            f"available: {', '.join(sorted(list_profiles()))}\n"
            f"for a new model, copy {PROFILE_DIR}/TEMPLATE.json and fill it in."
        )
    with open(cand) as fh:
        prof = json.load(fh)
    prof["_path"] = os.path.abspath(cand)
    return prof


def list_profiles():
    return [
        os.path.splitext(os.path.basename(p))[0]
        for p in glob.glob(os.path.join(PROFILE_DIR, "*.json"))
        if not os.path.basename(p).startswith("TEMPLATE")
    ]


# ── level 0: whole-model per-chunk device times ──────────────────────────────


def parse_e2e_log(path, profile):
    """Parse one e2e run log into {chunk_size: [(index, ms), ...]}.

    A single log can hold several chunk sizes (a sweep driver appends to one file);
    they are keyed by the measured [start, end) span, not by a filename convention.
    """
    pat = re.compile(profile["e2e"]["per_chunk_re"])
    series = OrderedDict()
    with open(path, errors="replace") as fh:
        text = fh.read()
    for m in pat.finditer(text):
        g = m.groupdict()
        chunk = int(g["end"]) - int(g["start"])
        series.setdefault(chunk, []).append((int(g["i"]) - 1, float(g["ms"])))
    return series


def parse_e2e_summary(path, profile):
    """Device / staging / readback split from the run's summary line, if present."""
    pat = profile["e2e"].get("summary_re")
    if not pat:
        return None
    with open(path, errors="replace") as fh:
        m = re.search(pat, fh.read())
    return {k: float(v) if "." in v or k.endswith("_s") else int(v) for k, v in m.groupdict().items()} if m else None


def fit_two_term(points):
    """Least-squares fit of t_i = a + slope*i.

    Returns a dict. `slope` is None when fewer than 2 points: a one-point series
    pins `a` and says nothing about the prefix term, and inventing one is exactly
    the kind of silent extrapolation this skill exists to prevent.
    """
    pts = sorted(points)
    n = len(pts)
    if n == 0:
        return {"n": 0, "a_ms": None, "slope_ms": None, "r2": None}
    if n == 1:
        return {"n": 1, "a_ms": pts[0][1], "slope_ms": None, "r2": None,
                "note": "single chunk: slope not determinable, not extrapolated"}
    sx = sum(x for x, _ in pts)
    sy = sum(y for _, y in pts)
    sxx = sum(x * x for x, _ in pts)
    sxy = sum(x * y for x, y in pts)
    den = n * sxx - sx * sx
    slope = (n * sxy - sx * sy) / den
    a = (sy - slope * sx) / n
    ybar = sy / n
    ss_tot = sum((y - ybar) ** 2 for _, y in pts)
    ss_res = sum((y - (a + slope * x)) ** 2 for x, y in pts)
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 1.0
    return {
        "n": n,
        "a_ms": a,
        "slope_ms": slope,
        "r2": r2,
        "max_resid_ms": max(abs(y - (a + slope * x)) for x, y in pts),
        "index_range": [pts[0][0], pts[-1][0]],
    }


def project(a_ms, slope_ms, isl, chunk):
    """T(ISL, C) in seconds, split into its two terms. Returns None if slope is unknown."""
    if a_ms is None or slope_ms is None or chunk <= 0:
        return None
    n = isl // chunk
    per_chunk = n * a_ms
    prefix = slope_ms * n * (n - 1) / 2.0
    return {
        "n_chunks": n,
        "per_chunk_term_s": per_chunk / 1000.0,
        "prefix_term_s": prefix / 1000.0,
        "total_s": (per_chunk + prefix) / 1000.0,
    }


def affine_fit_a_vs_chunk(rows):
    """Fit a(C) = F + k*C over the given (chunk, a_ms) rows -> the chunk-invariant cost F.

    A11: F is the chunk-invariant cost. The *excess over ideal token scaling*,
    a(C_small) - a(C_big)/r, is a different number: exactly 3/4 of F for r=4.
    Both get reported, never one labelled as the other.
    """
    pts = [(c, a) for c, a in rows if a is not None]
    if len(pts) < 2:
        return None
    n = len(pts)
    sx = sum(c for c, _ in pts)
    sy = sum(a for _, a in pts)
    sxx = sum(c * c for c, _ in pts)
    sxy = sum(c * a for c, a in pts)
    den = n * sxx - sx * sx
    if den == 0:
        return None
    k = (n * sxy - sx * sy) / den
    F = (sy - k * sx) / n
    return {"F_ms": F, "k_ms_per_token": k, "chunks": [c for c, _ in pts]}


# ── level 1: per-layer-type depth curves ─────────────────────────────────────


def parse_layer_log(path, profile):
    """Parse the isolated-layer benchmark log -> {layer_type: [(chunk_idx, ms), ...]}."""
    pat = re.compile(profile["layer_bench"]["result_re"])
    curves = {}
    kv = {}
    with open(path, errors="replace") as fh:
        for m in pat.finditer(fh.read()):
            g = m.groupdict()
            curves.setdefault(g["lt"], []).append((int(g["idx"]), float(g["ms"])))
            kv.setdefault(g["lt"], {})[int(g["idx"])] = int(g["kv"])
    return curves, kv


def reconstruct_model_slope(curves, profile):
    """Sum per-layer-type slopes weighted by layer count -> predicted whole-model slope."""
    counts = {k: v["count"] for k, v in profile["layers"]["types"].items()}
    total = 0.0
    parts = {}
    for lt, pts in curves.items():
        if lt not in counts:
            continue
        f = fit_two_term(pts)
        parts[lt] = {"count": counts[lt], **f}
        if f["slope_ms"] is not None:
            total += counts[lt] * f["slope_ms"]
    return {"predicted_slope_ms": total, "by_layer_type": parts}


def layer_count_difference(a_by_n):
    """Solve a(N) = F + N*L from >=2 (layer_count, a_ms) points; test linearity if >=3.

    Returns every pairwise solution so the spread is visible. Linearity in N is
    something to test, not assume.
    """
    ns = sorted(a_by_n)
    sols = []
    for i in range(len(ns)):
        for j in range(i + 1, len(ns)):
            p, q = ns[i], ns[j]
            L = (a_by_n[q] - a_by_n[p]) / (q - p)
            F = a_by_n[p] - p * L
            sols.append({"pair": [p, q], "L_ms": L, "F_ms": F})
    if not sols:
        return None
    Ls = [s["L_ms"] for s in sols]
    Fs = [s["F_ms"] for s in sols]
    return {
        "solutions": sols,
        "L_ms": sum(Ls) / len(Ls),
        "F_ms": sum(Fs) / len(Fs),
        "L_spread_pct": (max(Ls) - min(Ls)) / abs(sum(Ls) / len(Ls)) * 100 if any(Ls) else 0.0,
        "F_spread_pct": (max(Fs) - min(Fs)) / abs(sum(Fs) / len(Fs)) * 100 if any(Fs) else 0.0,
    }


# ── level 2: profiler captures and per-op tables ─────────────────────────────


def find_ops_csv(capture_dir):
    """Locate a capture's ops_perf_results CSV. Handles both layouts seen in practice:
    <dir>/profiler/reports/<ts>/ops_perf_results_*.csv  and  <dir>/ops_perf_results_*.csv
    """
    for pattern in (
        os.path.join(capture_dir, "profiler", "reports", "*", "ops_perf_results_*.csv"),
        os.path.join(capture_dir, "reports", "*", "ops_perf_results_*.csv"),
        os.path.join(capture_dir, "ops_perf_results_*.csv"),
    ):
        hits = sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)
        if hits:
            return hits[0]
    return None


def capture_build(capture_dir):
    """The git sha/branch a capture was taken on, from the run log the driver writes.

    Without this, level 2 can silently subtract two captures taken on different builds -
    which is exactly what A12 forbids, and which re-rendering cannot fix, because the
    difference is in the hardware runs and not in the rendering.
    """
    for name in ("run.log", "capture.log"):
        p = os.path.join(capture_dir, name)
        if not os.path.exists(p):
            continue
        with open(p, errors="replace") as fh:
            for line in fh:
                m = re.match(r"###\s*git:\s*([0-9a-f]{7,40})\s*(\S+)?", line)
                if m:
                    return {"sha": m.group(1), "branch": m.group(2), "source": p}
                if line.startswith("2026-") or line.startswith("202"):
                    break   # past the header
    return {"sha": None, "branch": None, "source": None}


def perf_report_version():
    exe = shutil.which("tt-perf-report")
    if not exe:
        return None
    for args in (["--version"], ["-V"]):
        try:
            out = subprocess.run([exe] + args, capture_output=True, text=True, timeout=30)
            m = re.search(r"\d+\.\d+\.\d+", (out.stdout or "") + (out.stderr or ""))
            if m:
                return m.group(0)
        except Exception:
            pass
    try:
        import importlib.metadata as md
        return md.version("tt-perf-report")
    except Exception:
        return "unknown"


def signpost_names(profile, layer_type, chunk_idx):
    tmpl = profile["layer_bench"]["signpost"]
    return tuple(
        tmpl.format(layer_type=layer_type, idx=chunk_idx, phase=p)
        for p in profile["layer_bench"]["signpost_phases"]
    )


def render_ops(ops_csv, start_signpost, end_signpost, out_csv, extra=()):
    """Run tt-perf-report over a raw capture into a CSV. A5: never --device-trace-profiler.

    --csv diverts the table out of stdout, so a human-readable table needs its own call;
    `render_table` below does that.
    """
    exe = shutil.which("tt-perf-report")
    if not exe:
        raise SystemExit("tt-perf-report not found on PATH. `pip install tt-perf-report`")
    cmd = [exe, "--no-color", "--no-summary",
           "--start-signpost", start_signpost, "--end-signpost", end_signpost,
           "--csv", out_csv, *extra, ops_csv]
    assert "--device-trace-profiler" not in cmd, "A5: --device-trace-profiler is never valid here"
    r = subprocess.run(cmd, capture_output=True, text=True)
    if not os.path.exists(out_csv):
        raise SystemExit(f"tt-perf-report produced no CSV\ncmd: {' '.join(cmd)}\n{r.stdout}\n{r.stderr}")
    return {"cmd": cmd, "out_csv": out_csv, "tool_version": perf_report_version()}


def render_table(ops_csv, start_signpost, end_signpost, out_txt, extra=()):
    exe = shutil.which("tt-perf-report")
    cmd = [exe, "--no-color", "--no-summary",
           "--start-signpost", start_signpost, "--end-signpost", end_signpost, *extra, ops_csv]
    r = subprocess.run(cmd, capture_output=True, text=True)
    with open(out_txt, "w") as fh:
        fh.write(r.stdout or r.stderr)
    return out_txt


def _f(x):
    try:
        return float(str(x).replace(",", ""))
    except (TypeError, ValueError):
        return None


MATMUL_RE = re.compile(r"(Matmul\w*) (\d+) x (\d+) x (\d+)")


def normalize_op_code(code):
    """Strip a matmul's M from its op code so the same matmul lines up across chunk sizes.

    M scales with the chunk, so the raw code differs per chunk size and the rows would
    never match. K x N is kept, since that identifies the weight.
    """
    code = (code or "").strip()
    m = MATMUL_RE.match(code)
    if m:
        return f"{m.group(1)} _x{m.group(3)}x{m.group(4)}"
    return code


def load_ops(path):
    """Load a tt-perf-report --csv output into rows of dicts with parsed numbers."""
    rows = []
    with open(path) as fh:
        for r in csv.DictReader(fh):
            rows.append({
                "op": (r.get("OP Code") or "").strip(),
                "key": normalize_op_code(r.get("OP Code")),
                "device_us": _f(r.get("Device Time")) or 0.0,
                "gap_us": _f(r.get("Op-to-Op Gap")),
                "total_pct": _f(r.get("Total %")),
                "cores": r.get("Cores"),
                "fidelity": (r.get("Math Fidelity") or "").strip(),
                "device": r.get("Device"),
                "raw": r,
            })
    return rows


def group_ops(rows):
    """Sum Device Time per normalized op code. A2: Device Time only, never Total %."""
    out = OrderedDict()
    for r in rows:
        e = out.setdefault(r["key"], {"n": 0, "device_us": 0.0, "cores": set(), "fidelity": set()})
        e["n"] += 1
        e["device_us"] += r["device_us"]
        if r["cores"]:
            e["cores"].add(r["cores"])
        if r["fidelity"]:
            e["fidelity"].add(r["fidelity"].split()[0])
    for e in out.values():
        e["cores"] = sorted(e["cores"], key=lambda c: -(int(c) if str(c).isdigit() else 0))
        e["fidelity"] = sorted(e["fidelity"])
    return out


def total_device_us(rows):
    return sum(r["device_us"] for r in rows)


def op_device_us(rows, name_fragment):
    return sum(r["device_us"] for r in rows if name_fragment in r["op"])


def subtract(deep, floor):
    """Per-op growth between two captures of the same layer at different prior context."""
    keys = set(deep) | set(floor)
    out = []
    for k in keys:
        d = deep.get(k, {"device_us": 0.0})["device_us"]
        f = floor.get(k, {"device_us": 0.0})["device_us"]
        out.append({"op": k, "floor_us": f, "deep_us": d, "delta_us": d - f})
    out.sort(key=lambda e: -abs(e["delta_us"]))
    return out


# ── the occupancy math the Cores column hides (A3) ───────────────────────────


def useful_occupancy(profile, chunk):
    """Work-unit occupancy of the growing op, computed from its own source math.

    This is the number the profiler cannot show: idle cores are not skipped, so
    `Cores` reads the full grid at every chunk size.
    """
    g = ((profile.get("growing_op") or {}).get("occupancy")
         or (profile.get("occupancy_model") or {}).get("occupancy"))
    if not g:
        return None
    cp = profile["mesh"]["cp"]
    rows = chunk // cp
    q_chunks = math.ceil(rows / g["q_chunk"])
    units = g["batch"] * g["n_q_heads_local"] * q_chunks
    grid = g["grid_cores"]
    depth = math.ceil(units / grid)
    return {
        "chunk": chunk,
        "rows_per_device": rows,
        "q_chunks": q_chunks,
        "work_units": units,
        "depth": depth,
        "slots": depth * grid,
        "useful_pct": 100.0 * units / (depth * grid),
        "grid_cores": grid,
        "idle_cores_skipped": g.get("idle_cores_skipped", False),
    }


# ── misc ─────────────────────────────────────────────────────────────────────


def pct_err(got, ref):
    if ref in (None, 0) or got is None:
        return None
    return 100.0 * (got - ref) / ref


def within(got, ref, tol_pct):
    e = pct_err(got, ref)
    return e is not None and abs(e) <= tol_pct


def git_info(tree):
    def run(*a):
        try:
            return subprocess.run(["git", "-C", tree, *a], capture_output=True, text=True, timeout=20).stdout.strip()
        except Exception:
            return ""
    return {"sha": run("rev-parse", "--short", "HEAD"),
            "branch": run("rev-parse", "--abbrev-ref", "HEAD"),
            "dirty": bool(run("status", "--porcelain"))}


def human_bytes(n):
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.1f} {unit}"
        n /= 1024.0
