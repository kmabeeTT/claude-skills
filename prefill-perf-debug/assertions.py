#!/usr/bin/env python3
"""A1-A12: the traps that cost real time, expressed as code instead of prose.

Every one of these exists because it already went wrong once in the Gemma4 prefill
investigation. The incident is recorded in each function's docstring, because an
assertion whose reason has been forgotten gets deleted the first time it is
inconvenient.

Each check returns an Assertion. `status` is one of:
    pass  - checked and satisfied
    fail  - checked and violated; the caller must not publish the claim
    warn  - satisfied but with a caveat worth printing
    na    - could not be checked (say so; never silently treat as pass)
"""

from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass, field, asdict

import helpers as H


@dataclass
class Assertion:
    id: str
    name: str
    status: str
    detail: str
    data: dict = field(default_factory=dict)

    def __str__(self):
        mark = {"pass": "PASS", "fail": "FAIL", "warn": "WARN", "na": "N/A "}[self.status]
        return f"[{mark}] {self.id} {self.name}: {self.detail}"

    def to_dict(self):
        return asdict(self)


def _a(id_, name, ok, detail, data=None, warn=False):
    status = "warn" if (ok and warn) else ("pass" if ok else "fail")
    return Assertion(id_, name, status, detail, data or {})


# ── A1 ───────────────────────────────────────────────────────────────────────

def A1_bound_claim(claim_term, ablations):
    """Refuse "bound by X" unless an ablation actually varied X.

    Incident: the investigation anchored the attention op's FLOPs against a dense
    matmul's per-core rate and attributed the 53% residual to fabric. Retracted. A
    FLOP-rate mismatch has many causes - here it was mostly structural core idleness.
    Only a causal ablation that moves X and holds the rest fixed licenses the claim.

    `ablations` is a list of dicts with at least {"varies": str, "measured": float}.
    """
    term = (claim_term or "").lower()
    hits = [ab for ab in (ablations or []) if term and term in (ab.get("varies", "") or "").lower()]
    moved = [ab for ab in hits if ab.get("measured") is not None and abs(ab["measured"] - 1.0) > 0.05]
    if not hits:
        return Assertion("A1", "bound-by needs an ablation", "fail",
                         f'no ablation in the record varied "{claim_term}". '
                         f'Measure it or drop the claim; a rate mismatch is not evidence.',
                         {"claim": claim_term, "ablations_seen": [a.get("varies") for a in (ablations or [])]})
    if not moved:
        return Assertion("A1", "bound-by needs an ablation", "fail",
                         f'ablations varying "{claim_term}" exist but none moved the cost '
                         f'(all within 5% of 1.0x) - that RULES OUT the bound, it does not establish it.',
                         {"claim": claim_term, "hits": hits})
    return _a("A1", "bound-by needs an ablation", True,
              f'"{claim_term}" varied by {[a.get("knob", a.get("varies")) for a in moved]} '
              f'-> {[a["measured"] for a in moved]}x. Claim licensed.',
              {"claim": claim_term, "evidence": moved})


# ── A2 ───────────────────────────────────────────────────────────────────────

def A2_gap_and_total_pct(rows, factor=100.0):
    """Ignore `Total %` and `Op-to-Op Gap` when one op's gap exceeds ~100x the median.

    Incident: each trace replay's first op carries a host gap measured from *before*
    the signpost - 1,121,464 us in one capture. That single number swamps the
    percentage column, which then showed an 8.27 ms op as `0.7 %`. Use Device Time.
    """
    gaps = sorted(r["gap_us"] for r in rows if r["gap_us"] is not None)
    if not gaps:
        return Assertion("A2", "Total %/gap usability", "na", "no Op-to-Op Gap column in this CSV")
    med = gaps[len(gaps) // 2]
    worst = max(gaps)
    offenders = [r for r in rows if r["gap_us"] is not None and r["gap_us"] > factor * max(med, 1e-9)]
    if offenders:
        o = max(offenders, key=lambda r: r["gap_us"])
        return Assertion(
            "A2", "Total %/gap usability", "warn",
            f"gap outlier {o['op']} = {o['gap_us']:,.0f} us vs median {med:.2f} us "
            f"({o['gap_us']/max(med,1e-9):,.0f}x). Total % and Op-to-Op Gap are UNUSABLE on this "
            f"capture - use Device Time. (Enforced: this module never sums Total %.)",
            {"median_gap_us": med, "max_gap_us": worst,
             "offenders": [{"op": r["op"], "gap_us": r["gap_us"]} for r in offenders]})
    return _a("A2", "Total %/gap usability", True,
              f"no gap outlier (median {med:.2f} us, max {worst:.2f} us); Device Time used regardless",
              {"median_gap_us": med, "max_gap_us": worst})


# ── A3 ───────────────────────────────────────────────────────────────────────

def A3_cores_is_not_occupancy(rows, profile, chunk, op_fragment=None):
    """Never report `Cores` as occupancy. Compute useful occupancy and print both.

    Incident: the global SDPA reports 114 cores at every chunk size, including where
    only 32 of ~110 cores hold a work unit - the rest run padded handshake iterations.
    Useful occupancy ranges 29% -> 93% and is invisible in that column.
    """
    frag = op_fragment or profile.get("growing_op", {}).get("name", "")
    reported = sorted({r["cores"] for r in rows if frag and frag in r["op"] and r["cores"]})
    occ = H.useful_occupancy(profile, chunk)
    if occ is None:
        return Assertion("A3", "Cores != occupancy", "na",
                         "profile has no growing_op.occupancy work-unit math; cannot compute useful occupancy")
    detail = (f"Cores column reads {reported or 'n/a'} - that is grid size, NOT occupancy. "
              f"Useful occupancy at chunk {chunk} = {occ['useful_pct']:.0f}% "
              f"({occ['work_units']} work units over {occ['slots']} slots, depth {occ['depth']}).")
    return Assertion("A3", "Cores != occupancy", "pass", detail,
                     {"cores_reported": reported, "occupancy": occ})


# ── A4 ───────────────────────────────────────────────────────────────────────

UTIL_COLS = ("NOC UTIL (%)", "DRAM BW UTIL (%)", "ETH BW UTIL (%)", "DEVICE COMPUTE CB WAIT FRONT [ns]")


def A4_utilization_columns(rows):
    """Assert utilization columns are non-empty before using them.

    They are empty on this path: they need `--analyze-noc-traces` plus a built tt-npe,
    and ETH BW UTIL is modelled from NoC traces even then. Their ABSENCE is also not
    evidence of anything - do not infer from it.
    """
    if not rows:
        return Assertion("A4", "utilization columns", "na", "no rows")
    raw = rows[0]["raw"]
    present = [c for c in UTIL_COLS if c in raw]
    if not present:
        return Assertion("A4", "utilization columns", "warn",
                         "utilization columns are not in this CSV at all. Do not plan around "
                         "NOC/DRAM/ETH UTIL, and do not infer anything from their absence.")
    populated = [c for c in present
                 if any(str(r["raw"].get(c, "")).strip() not in ("", "nan", "None") for r in rows)]
    if not populated:
        return Assertion("A4", "utilization columns", "warn",
                         f"{len(present)} utilization column(s) present but ENTIRELY EMPTY. "
                         f"Needs --analyze-noc-traces plus a built tt-npe. Any claim resting on them is void; "
                         f"their emptiness is not evidence either way.",
                         {"present": present})
    return _a("A4", "utilization columns", True, f"populated: {populated}", {"populated": populated})


# ── A5 ───────────────────────────────────────────────────────────────────────

def A5_no_device_trace_profiler(cmd):
    """Never pass --device-trace-profiler.

    It profiles only trace regions, empties OP NAME and kills post-processing with
    `AssertionError: Device data missing`.
    """
    s = cmd if isinstance(cmd, str) else " ".join(cmd)
    bad = "--device-trace-profiler" in s
    return Assertion("A5", "no --device-trace-profiler", "fail" if bad else "pass",
                     "command contains --device-trace-profiler; it empties OP NAME and breaks "
                     "post-processing (AssertionError: Device data missing)" if bad
                     else "capture command is clean", {"cmd": s})


# ── A6 / A12 ─────────────────────────────────────────────────────────────────

def A6_rerendered_both_sides(side_a, side_b):
    """Any cross-branch / build / date comparison must re-render BOTH sides from the
    raw captures with the same tool. Refuse if one side's raw capture is gone.

    Incident: per-device spread on ONE op was 17% (min 382.9 / median 434.5 / max
    446.8 us). A number lifted from an old writeup produced a false +21% regression
    report; re-rendering the same capture gave +1.9%.

    Each side is a dict: {"label", "raw_capture" (path or None), "rendered_from_raw": bool,
    "tool_version": str}.
    """
    problems = []
    for s in (side_a, side_b):
        if not s.get("rendered_from_raw"):
            problems.append(f'{s.get("label","?")}: not re-rendered from a raw capture '
                            f'(value lifted from a table/summary) - REFUSED')
        raw = s.get("raw_capture")
        if raw and not os.path.exists(raw):
            problems.append(f'{s.get("label","?")}: raw capture missing at {raw} - comparison impossible')
        elif not raw:
            problems.append(f'{s.get("label","?")}: no raw capture recorded')
    va, vb = side_a.get("tool_version"), side_b.get("tool_version")
    if va and vb and va != vb:
        problems.append(f"rendered with different tool versions ({va} vs {vb})")
    if problems:
        return Assertion("A6", "cross-branch compare re-rendered", "fail", "; ".join(problems),
                         {"a": side_a, "b": side_b})
    return _a("A6", "cross-branch compare re-rendered", True,
              f'both sides re-rendered from raw with tt-perf-report {va}', {"a": side_a, "b": side_b})


def A12_same_build(side_a, side_b, allow_cross_build=False):
    """Never compare per-op timings across builds without A6.

    Incident: "rms_norm is exactly chunk-invariant" came from comparing a 2026-09-09
    capture against this branch, where the SAME norm on the SAME shape and core count
    took 99.3 us instead of 134.2 us. Same-branch it is 1.22x, not 0.98x.
    """
    a, b = side_a.get("build") or side_a.get("branch"), side_b.get("build") or side_b.get("branch")
    if a and b and a == b:
        return _a("A12", "same build", True, f"both sides on {a}")
    if not allow_cross_build:
        return Assertion("A12", "same build", "fail",
                         f"cross-build per-op comparison ({a} vs {b}). A same-shape, same-core-count op "
                         f"is NOT a safe cross-build anchor. Either re-profile the baseline on the branch "
                         f"under test, or declare this a deliberate cross-branch check under A6.",
                         {"a": a, "b": b})
    return Assertion("A12", "same build", "warn",
                     f"deliberate cross-build comparison ({a} vs {b}), allowed only because both sides "
                     f"were re-rendered from raw (A6). Report it as cross-build in the writeup.",
                     {"a": a, "b": b})


# ── A7 ───────────────────────────────────────────────────────────────────────

def A7_prediction_registered(run_dir, label):
    """Require a pre-registered prediction before an ablation or discriminating comparison.

    Incident, positive: writing down "0.50x if occupancy-bound, 0.25x if neutral"
    BEFORE the deep captures is what made the measured 0.443x mean something. A
    prediction written afterwards means nothing.
    """
    path = os.path.join(run_dir, "PREDICTION.md")
    if not os.path.exists(path):
        return Assertion("A7", "pre-registered prediction", "fail",
                         f"no PREDICTION.md in {run_dir}. Write the competing predictions and what would "
                         f"falsify each BEFORE running, or the result is not a test.", {"path": path})
    with open(path) as fh:
        body = fh.read()
    if label and label.lower() not in body.lower():
        return Assertion("A7", "pre-registered prediction", "warn",
                         f'PREDICTION.md exists but does not mention "{label}"; check it covers this comparison',
                         {"path": path})
    falsifiable = any(w in body.lower() for w in ("falsifi", "if ", "predict"))
    return Assertion("A7", "pre-registered prediction", "pass" if falsifiable else "warn",
                     f"PREDICTION.md present ({len(body)} chars)"
                     + ("" if falsifiable else "; it states no falsifiable alternative"),
                     {"path": path})


# ── A8 ───────────────────────────────────────────────────────────────────────

def A8_control_present(controls, tol_pct=2.0):
    """Require a control - a quantity that should NOT move.

    Incident, positive: the sliding layer being flat to 0.8% is what made the global
    layer's +119% credible rather than a harness artifact.

    `controls` is a list of {"name", "expected_flat": bool, "delta_pct": float}.
    """
    if not controls:
        return Assertion("A8", "control quantity", "fail",
                         "no control measured. Name something that should NOT move and measure it, "
                         "or the effect is indistinguishable from a harness artifact.")
    bad = [c for c in controls if c.get("expected_flat") and abs(c.get("delta_pct", 0)) > tol_pct]
    if bad:
        return Assertion("A8", "control quantity", "fail",
                         f"control(s) moved: " + ", ".join(f'{c["name"]} {c["delta_pct"]:+.1f}%' for c in bad)
                         + f" (tolerance {tol_pct}%). The harness, not the effect, may be what you measured.",
                         {"controls": controls})
    return _a("A8", "control quantity", True,
              "controls flat: " + ", ".join(f'{c["name"]} {c.get("delta_pct",0):+.1f}%' for c in controls),
              {"controls": controls})


# ── A9 ───────────────────────────────────────────────────────────────────────

def A9_matched_prior_context(points):
    """When comparing chunk sizes at depth, hold PRIOR CONTEXT fixed, not chunk index.

    Chunk index 7 is 57k of history at chunk 8192 and 14k at 2048. Matching prior
    context makes the prefix work exactly proportional to chunk size, which turns the
    comparison into a test with a predicted number.

    `points` is a list of {"chunk", "chunk_idx", "prior_ctx"}.
    """
    if len(points) < 2:
        return Assertion("A9", "matched prior context", "na", "fewer than 2 points to compare")
    ctxs = {p["prior_ctx"] for p in points}
    idxs = {p["chunk_idx"] for p in points}
    if len(ctxs) == 1:
        return _a("A9", "matched prior context", True,
                  f"all {len(points)} points at prior context {ctxs.pop():,} tokens "
                  f"(chunk indices {sorted(idxs)}) - prefix work is proportional to chunk size",
                  {"points": points})
    return Assertion("A9", "matched prior context", "fail",
                     f"prior contexts differ: {sorted(ctxs)}. Matching chunk INDEX across chunk sizes "
                     f"compares different amounts of history and confounds the measurement. "
                     f"Pick indices so chunk*idx is equal.", {"points": points})


# ── A10 ──────────────────────────────────────────────────────────────────────

def A10_closes_against_level0(perop_ms, level0_ms, tol_pct=15.0, what=""):
    """Every per-op attribution must close against level 0 within ~15%; state the residual.

    Per-op sums overstate: the isolated-layer harness has no inter-layer overlap and
    pays staging ops the real model pays once per chunk. A level that does not close
    is a finding, not something to paper over.
    """
    if perop_ms is None or level0_ms in (None, 0):
        return Assertion("A10", "closes against level 0", "na", "missing one side of the reconciliation")
    err = H.pct_err(perop_ms, level0_ms)
    ok = abs(err) <= tol_pct
    return Assertion("A10", "closes against level 0", "pass" if ok else "fail",
                     f"{what or 'per-op'} {perop_ms:.3f} ms vs level-0 {level0_ms:.3f} ms -> "
                     f"residual {err:+.1f}% (tolerance {tol_pct}%)"
                     + ("" if ok else ". Report the gap; do not present a clean split over it."),
                     {"perop_ms": perop_ms, "level0_ms": level0_ms, "residual_pct": err, "tol_pct": tol_pct})


# ── A11 ──────────────────────────────────────────────────────────────────────

def A11_floor_basis(excess_ms=None, invariant_ms=None, ratio=4):
    """Distinguish "excess over ideal scaling" from "chunk-invariant cost".

    For cost = F + k*tokens compared at a chunk-size ratio r, the excess
    a(C) - a(rC)/r is exactly (1 - 1/r)*F. At r=4 that is 3/4*F, so the two numbers
    differ by 4/3. The Gemma4 floor was published as ~70 ms (the excess); the
    chunk-invariant cost is ~94 ms. Quoting one as the other is a 33% error.
    """
    k = 1.0 - 1.0 / ratio
    if excess_ms is not None and invariant_ms is None:
        return Assertion("A11", "floor basis", "warn",
                         f"excess over ideal scaling = {excess_ms:.1f} ms. The CHUNK-INVARIANT cost is "
                         f"{excess_ms/k:.1f} ms (excess = {k:.2f}*F at ratio {ratio}). Label which you mean.",
                         {"excess_ms": excess_ms, "implied_invariant_ms": excess_ms / k})
    if invariant_ms is not None and excess_ms is None:
        return Assertion("A11", "floor basis", "warn",
                         f"chunk-invariant cost F = {invariant_ms:.1f} ms; the excess over ideal scaling at "
                         f"ratio {ratio} is {invariant_ms*k:.1f} ms. Label which you mean.",
                         {"invariant_ms": invariant_ms, "implied_excess_ms": invariant_ms * k})
    if excess_ms is None and invariant_ms is None:
        return Assertion("A11", "floor basis", "na", "no floor figure supplied")
    consistent = abs(excess_ms - k * invariant_ms) / max(k * invariant_ms, 1e-9) < 0.15
    return Assertion("A11", "floor basis", "pass" if consistent else "warn",
                     f"excess {excess_ms:.1f} ms and chunk-invariant {invariant_ms:.1f} ms "
                     f"(expected excess = {k*invariant_ms:.1f} ms)"
                     + ("" if consistent else " - these are inconsistent; one of them is mislabelled"),
                     {"excess_ms": excess_ms, "invariant_ms": invariant_ms, "expected_excess_ms": k * invariant_ms})


# ── batch runner ─────────────────────────────────────────────────────────────

def run_capture_checks(rows, profile, chunk, capture_cmd=None):
    """The checks that apply to any single per-op capture."""
    out = [A2_gap_and_total_pct(rows), A3_cores_is_not_occupancy(rows, profile, chunk), A4_utilization_columns(rows)]
    if capture_cmd is not None:
        out.append(A5_no_device_trace_profiler(capture_cmd))
    return out


def summarize(assertions):
    counts = {"pass": 0, "fail": 0, "warn": 0, "na": 0}
    for a in assertions:
        counts[a.status] += 1
    return counts


def gate(assertions):
    """True if nothing failed. A warn is informational; a fail blocks the claim."""
    return all(a.status != "fail" for a in assertions)
