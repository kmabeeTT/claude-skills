#!/usr/bin/env python3
"""Capability probe. Run this BEFORE promising anything.

The funnel assumes harness features a new model may not have. Probe, report, and
degrade - never fabricate a level you cannot measure. The output is a table; a model
missing fake-depth is still worth a level-0 pass.
"""

from __future__ import annotations

import csv
import os
import re
import shutil

import helpers as H
from assertions import UTIL_COLS


def _literal_prefix(pattern):
    """The leading literal of a regex, for grepping source. '\\[traced_perf\\] chunk (?P<i>..' -> '[traced_perf] chunk'."""
    out = []
    i = 0
    while i < len(pattern):
        c = pattern[i]
        if c == "\\" and i + 1 < len(pattern):
            out.append(pattern[i + 1])
            i += 2
            continue
        if c in "([?*+{|":
            break
        out.append(c)
        i += 1
    return "".join(out).strip()


def _read(path):
    try:
        with open(path, errors="replace") as fh:
            return fh.read()
    except OSError:
        return None


class Cap:
    def __init__(self, key, name, present, detail, consequence, blocking=False):
        self.key, self.name, self.present = key, name, present
        self.detail, self.consequence, self.blocking = detail, consequence, blocking

    def to_dict(self):
        return {"capability": self.name, "present": self.present, "detail": self.detail,
                "if_absent": self.consequence, "blocking": self.blocking}


def probe(profile, sample_capture=None, sample_log=None):
    tree = profile.get("tree", ".")
    caps = []

    # 1. e2e chunked-prefill test emitting PER-CHUNK device times -- everything rests on this
    e2e = profile.get("e2e", {})
    src = _read(os.path.join(tree, e2e.get("test_file", ""))) if e2e.get("test_file") else None
    tag = _literal_prefix(e2e.get("per_chunk_re", ""))
    have_test = bool(src) and e2e.get("test_name", "\0") in src
    have_line = bool(src) and bool(tag) and tag in src
    # a real log is stronger evidence than source grepping
    log_pts = None
    if sample_log and os.path.exists(sample_log):
        log_pts = H.parse_e2e_log(sample_log, profile)
    ok = (have_test and have_line) or bool(log_pts)
    caps.append(Cap(
        "e2e_per_chunk", "e2e chunked-prefill test with per-chunk device times", ok,
        (f"{e2e.get('test_name')} in {e2e.get('test_file')}; emits '{tag}'"
         + (f"; sample log has {sum(len(v) for v in log_pts.values())} chunk rows across "
            f"{sorted(log_pts)}" if log_pts else "")) if ok else
        f"test={have_test} per-chunk-line={have_line} in {e2e.get('test_file')}",
        "STOP. Levels 0-3 all rest on this. Add a test parametrized by chunk size that logs "
        "one line per chunk with the device time.", blocking=True))

    # 2. device / staging / readback separated
    sep = bool(e2e.get("separates_device_staging_readback")) and bool(src) and "readback" in (src or "")
    caps.append(Cap(
        "device_staging_readback", "device / staging / readback timings separated", sep,
        "summary line distinguishes them" if sep else "summary conflates host and device time",
        "Usable, but WARN in every report: conflating them understates device throughput ~2x."))

    # 3. per-layer isolated benchmark
    lb = profile.get("layer_bench", {})
    lsrc = _read(os.path.join(tree, lb.get("test_file", ""))) if lb.get("test_file") else None
    have_lb = bool(lsrc) and lb.get("test_name", "\0") in lsrc
    caps.append(Cap(
        "layer_bench", "per-layer isolated benchmark (layer type x chunk index)", have_lb,
        f"{lb.get('test_name')} takes layer_type={lb.get('layer_type_values')}" if have_lb else "not found",
        "Levels 0-1 only; skip level 2 (no way to window the profiler to one layer)."))

    # 4. fake-depth (pre-filled cache + a valid-KV-length metadata field)
    fd = lb.get("fake_depth_field")
    have_fd = bool(lsrc) and bool(fd) and fd in lsrc
    caps.append(Cap(
        "fake_depth", "fake-depth mechanism (pre-filled cache + valid-KV-length field)", have_fd,
        f"sets {fd}" if have_fd else f"no {fd!r} in {lb.get('test_file')}",
        "Depth sweeps cost a real prefill each; drop to 2 depths."))

    # 5. signposts around the measured region
    have_sp = bool(lsrc) and "signpost" in lsrc
    sp_example = None
    if have_sp and lb.get("signpost"):
        sp_example = H.signpost_names(profile, list(profile["layers"]["types"])[0], 0)
    caps.append(Cap(
        "signposts", "signposts around the measured region", have_sp,
        f"e.g. {sp_example[0]} .. {sp_example[1]}" if sp_example else ("signpost() called" if have_sp else "none"),
        "Cannot window the profiler; LEVEL 2 UNAVAILABLE."))

    # 6. tt-perf-report
    ver = H.perf_report_version()
    caps.append(Cap("tt_perf_report", "tt-perf-report installed", bool(shutil.which("tt-perf-report")),
                    f"v{ver} at {shutil.which('tt-perf-report')}" if ver else "not on PATH",
                    "pip install tt-perf-report"))

    # 7. profiler utilization columns -- expected ABSENT; the point is to stop anyone planning around them
    util = _probe_util(profile, sample_capture)
    caps.append(util)

    # 8. layer-count override (level 1 route B)
    lco = profile.get("layer_count_override", {})
    caps.append(Cap("layer_count_override", "layer-count override for layer differencing",
                    bool(lco.get("available")),
                    lco.get("reason", "") if not lco.get("available") else lco.get("how", "available"),
                    "Level 1 falls back to per-layer-type depth curves (in-tree). Layer-count "
                    "differencing needs a temporary patch -> ASSISTED path only, like level 3."))

    return caps


def _probe_util(profile, sample_capture):
    path = None
    if sample_capture:
        path = H.find_ops_csv(sample_capture) if os.path.isdir(sample_capture) else sample_capture
    if not path or not os.path.exists(path):
        cap_dir = (profile.get("artifacts", {}) or {}).get("runs_dir")
        tags = (profile.get("artifacts", {}) or {}).get("captures", {})
        if cap_dir and tags:
            path = H.find_ops_csv(os.path.join(cap_dir, sorted(tags)[0]))
    if not path or not os.path.exists(path):
        return Cap("util_columns", "profiler utilization columns populated", False,
                   "no capture available to check", "Assert before use; they are empty on this path.")
    hdr, populated = [], []
    with open(path) as fh:
        rd = csv.DictReader(fh)
        hdr = rd.fieldnames or []
        present = [c for c in UTIL_COLS if c in hdr]
        seen = {c: False for c in present}
        for i, row in enumerate(rd):
            for c in present:
                if str(row.get(c, "")).strip() not in ("", "nan", "None"):
                    seen[c] = True
            if i > 5000:
                break
        populated = [c for c, v in seen.items() if v]
    return Cap("util_columns", "profiler utilization columns populated", bool(populated),
               (f"populated: {populated}" if populated else
                f"present but EMPTY: {[c for c in UTIL_COLS if c in hdr]} (checked {os.path.basename(path)})"),
               "Do NOT use them, and do NOT infer anything from their absence. They need "
               "--analyze-noc-traces plus a built tt-npe; ETH BW UTIL is modelled even then.")


def render(caps, profile):
    w = max(len(c.name) for c in caps) + 2
    lines = [f"Capability probe: {profile['model']}  (profile {os.path.basename(profile.get('_path',''))})", ""]
    lines.append(f"{'capability':<{w}}{'status':<10}detail")
    lines.append("-" * (w + 10 + 40))
    for c in caps:
        mark = "PRESENT" if c.present else ("BLOCKING" if c.blocking else "MISSING")
        detail = c.detail if len(c.detail) <= 88 else c.detail[:85] + "..."
        lines.append(f"{c.name:<{w}}{mark:<10}{detail}")
    missing = [c for c in caps if not c.present]
    if missing:
        lines.append("")
        lines.append("Degradations:")
        for c in missing:
            lines.append(f"  - {c.name}: {c.consequence}")
    blocked = [c for c in caps if c.blocking and not c.present]
    lines.append("")
    if blocked:
        lines.append("VERDICT: BLOCKED. " + "; ".join(c.consequence for c in blocked))
    else:
        avail = ["0"]
        by = {c.key: c.present for c in caps}
        if by.get("layer_bench"):
            avail.append("1")
        if by.get("layer_bench") and by.get("signposts") and by.get("tt_perf_report"):
            avail.append("2")
        avail.append("3 (assisted only)")
        lines.append(f"VERDICT: levels available -> {', '.join(avail)}")
    return "\n".join(lines)
