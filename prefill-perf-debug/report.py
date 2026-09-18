#!/usr/bin/env python3
"""The output contract: one run directory per invocation.

    <workdir>/prefill-perf/<model>-<YYYY_MM_DD_HH_MM_SS>/
      manifest.json   model, branch, git sha, mesh, tier, goal, capability probe
      findings.json   machine-readable: a/slope per chunk, per-op attribution, assertions
      raw/            run logs; ops CSVs only (the 4.8 GB device CSVs are pruned by default)
      reports/        rendered tt-perf-report tables and side-by-side comparisons
      TLDR.md         the answer first. Forwardable. Links to REPORT.md
      REPORT.md       full record, every measurement, residuals, the traps that applied

TLDR.md rules, learned from the first writeup being called hard to parse:
  - lead with the ANSWER, not the method and not the optimization ideas
  - a 4-column table: term | A vs B | cause | whose
  - a "how this was obtained" section naming the method per finding
  - confine "how to make it faster" to ONE clearly-labelled section
  - state residuals and anything retracted
"""

from __future__ import annotations

import json
import os
import shutil
import time

import helpers as H


def new_run_dir(workdir, model):
    stamp = time.strftime("%Y_%m_%d_%H_%M_%S")
    d = os.path.join(workdir, "prefill-perf", f"{model}-{stamp}")
    for sub in ("raw", "reports"):
        os.makedirs(os.path.join(d, sub), exist_ok=True)
    return d


def record_sources(run_dir, logs, capture_dirs):
    """Copy the (small) run logs into raw/ and pin the provenance of every capture.

    The ops CSVs are ~37 MB each and the raw device CSVs ~4.8 GB, so they are NOT copied.
    What is recorded is enough to satisfy A6 later: the exact file, its size and its
    mtime, so a future comparison can tell whether the raw capture it needs still exists
    and is the same one.
    """
    raw = os.path.join(run_dir, "raw")
    os.makedirs(raw, exist_ok=True)
    lines = ["# provenance of every input to this run",
             "# logs are copied into raw/; captures are referenced, not copied "
             "(~37 MB ops CSV + ~4.8 GB device CSV each)", ""]
    for lg in logs or []:
        if lg and os.path.exists(lg):
            dest = os.path.join(raw, os.path.basename(os.path.dirname(lg)) + "_" + os.path.basename(lg))
            try:
                shutil.copy2(lg, dest)
                lines.append(f"log      {lg}  ->  raw/{os.path.basename(dest)}")
            except OSError as e:
                lines.append(f"log      {lg}  (copy failed: {e})")
    for d in capture_dirs or []:
        ops = H.find_ops_csv(d) if os.path.isdir(d) else d
        if ops and os.path.exists(ops):
            st = os.stat(ops)
            lines.append(f"capture  {ops}  {H.human_bytes(st.st_size)}  "
                         f"mtime {time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(st.st_mtime))}")
        else:
            lines.append(f"capture  {d}  MISSING - any cross-comparison against it is invalid (A6)")
    p = os.path.join(raw, "SOURCES.txt")
    with open(p, "w") as fh:
        fh.write("\n".join(lines) + "\n")
    return p


def write_manifest(run_dir, profile, tier, goal, caps, extra=None):
    git = H.git_info(profile.get("tree", "."))
    man = {
        "created": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "skill": "prefill-perf-debug",
        "skill_version": "1.0.0",
        "model": profile["model"],
        "profile": profile.get("_path"),
        "tree": profile.get("tree"),
        "branch": git["branch"],
        "git_sha": git["sha"],
        "tree_dirty": git["dirty"],
        "mesh": profile.get("mesh"),
        "tier": tier,
        "goal": goal,
        "tt_perf_report": H.perf_report_version(),
        "host": os.uname().nodename,
        "capability_probe": [c.to_dict() for c in caps] if caps else None,
    }
    if extra:
        man.update(extra)
    p = os.path.join(run_dir, "manifest.json")
    with open(p, "w") as fh:
        json.dump(man, fh, indent=2)
    return p


def write_findings(run_dir, findings):
    p = os.path.join(run_dir, "findings.json")
    with open(p, "w") as fh:
        json.dump(findings, fh, indent=2, default=str)
    return p


def _dedupe(pairs):
    """Collapse the same assertion fired once per capture into one line."""
    seen = {}
    order = []
    for b, a in pairs:
        k = (a["id"], b)
        if k in seen:
            seen[k][1]["_n"] = seen[k][1].get("_n", 1) + 1
            continue
        a = dict(a)
        seen[k] = (b, a)
        order.append(k)
    out = []
    for k in order:
        b, a = seen[k]
        if a.get("_n", 1) > 1:
            a["_times"] = f" [fired on {a['_n']} captures]"
        out.append((b, a))
    return out


def _assert_lines(findings):
    """Every assertion in `findings`, wherever it sits.

    This used to read three fixed keys, one of which (`reconciliation`) nothing ever
    wrote, so an A10 FAILURE from level2_reconcile never reached TLDR.md - the exact
    thing this skill exists to surface. It now walks the structure instead, so a new
    level or a renamed key cannot silently drop a fired assertion again.
    """
    labels = {"level0": "level 0", "level1": "level 1", "level2": "level 2",
              "level2_reconcile": "reconciliation", "reconciliation": "reconciliation",
              "level3": "level 3"}

    def walk(node, block, out):
        if isinstance(node, dict):
            if "id" in node and "status" in node:
                out.append((block, node))
                return
            for k, v in node.items():
                walk(v, labels.get(k, block), out)
        elif isinstance(node, list):
            for v in node:
                walk(v, block, out)

    out = []
    for key in ("level0", "level1", "level2", "level2_reconcile", "reconciliation", "level3"):
        if key in findings:
            walk(findings[key], labels.get(key, key), out)
    return out


def write_tldr(run_dir, profile, findings, goal, residuals=None, retracted=None, levers=None):
    l0 = findings.get("level0") or {}
    rows = [r for r in l0.get("rows", []) if r.get("total_s")]
    lines = [f"# {profile['model']} prefill: {goal or 'where the time goes'}", ""]

    # ── the answer, first ────────────────────────────────────────────────────
    if len(rows) >= 2:
        ref = next((r for r in rows if r["chunk"] == l0.get("reference_chunk")),
                   min(rows, key=lambda r: r["total_s"]))
        worst = max((r for r in rows if r.get("vs_reference")),
                    key=lambda r: r["vs_reference"]["total"])
        v = worst["vs_reference"]
        lines += [
            f"**Chunk {worst['chunk']} is {v['total']:.2f}x slower than {ref['chunk']} over a "
            f"{l0['isl']//1024}k prompt.** It splits into two independent terms that live in "
            f"different layers and need different fixes.", "",
            "| term | " + f"{worst['chunk']} vs {ref['chunk']}" + " | cause | whose |",
            "|---|---|---|---|",
        ]
        owners = _owners(profile, findings)
        lines.append(f"| **per-chunk term** (= TTFT) | **{v['per_chunk_term']:.2f}x** | "
                     f"{_floor_cause(findings)} | {owners['floor']} |")
        if v.get("prefix_term"):
            lines.append(f"| **prefix term** | **{v['prefix_term']:.2f}x** | {_prefix_cause(profile, findings)} "
                         f"| {owners['prefix']} |")
        lines.append(f"| | **= {v['total']:.2f}x** | | |")
        lines.append("")
        lines += ["`T = N*a(C) + slope(C)*N(N-1)/2`, with `N = ISL/C`.", "",
                  "| chunk | N | `a` = per-chunk (ms) | `slope` (ms/index) | total |",
                  "|---:|---:|---:|---:|---:|"]
        for r in l0["rows"]:
            if r.get("total_s"):
                lines.append(f"| {r['chunk']} | {r['n_chunks']} | {r['a_ms']:.1f} | "
                             f"{r['slope_ms']:.3f} | {r['total_s']:.2f} s |")
            else:
                lines.append(f"| {r['chunk']} | - | {r['a_ms']:.1f} | **unverifiable** | - |")
        lines.append("")

    # ── how this was obtained ────────────────────────────────────────────────
    lines += ["## How this was obtained", "",
              "| finding | method |", "|---|---|"]
    lines.append("| the two-term split, `a` and `slope` | whole-model per-chunk device times, "
                 "least-squares fit of `t_i = a + slope*i`. No profiler. |")
    if findings.get("level1"):
        lines.append("| which layer type owns each term | per-layer-type depth curves over the "
                     "isolated-layer benchmark, reconstructed against the whole-model slope |")
    if findings.get("level2"):
        lines.append("| which op inside those layers | Tracy capture at depth 0 **and** at depth D, "
                     "rendered with `tt-perf-report`, subtracted, at **matched prior context** |")
    if findings.get("level3"):
        lines.append("| what the op is bound by | one-knob-at-a-time ablations, each re-measured "
                     "end to end against a pre-registered prediction |")
    lines.append("")

    # ── residuals and retractions ────────────────────────────────────────────
    fails = [(b, a) for b, a in _assert_lines(findings) if a["status"] == "fail"]
    warns = [(b, a) for b, a in _assert_lines(findings) if a["status"] == "warn"]
    if residuals or fails or warns or retracted:
        lines += ["## Residuals, caveats and anything retracted", ""]
        for r in residuals or []:
            lines.append(f"- {r}")
        for b, a in _dedupe(fails):
            lines.append(f"- **{a['id']} FAILED** ({b}){a.get('_times','')}: {a['detail']}")
        for b, a in _dedupe(warns):
            lines.append(f"- {a['id']} ({b}){a.get('_times','')}: {a['detail']}")
        for r in retracted or []:
            lines.append(f"- **Retracted:** {r}")
        for r in l0.get("rows", []):
            if r.get("unverifiable"):
                lines.append(f"- chunk {r['chunk']}: {r['unverifiable']}")
        lines.append("")

    # ── levers, in one clearly-labelled section ──────────────────────────────
    lines += ["## How to make it faster", "",
              "*The investigation's job is to explain. This section is the only place that "
              "proposes levers, and nothing here is verified unless it says so.*", ""]
    if levers:
        lines += ["| option | effect | status |", "|---|---|---|"]
        for lv in levers:
            lines.append(f"| {lv['option']} | {lv['effect']} | {lv['status']} |")
    else:
        lines.append("_None proposed: no ablation in this run varied a knob end to end._")
    lines += ["", f"Full record: [REPORT.md](REPORT.md) - every measurement, the assertions that "
              f"fired, and the commands.", ""]

    p = os.path.join(run_dir, "TLDR.md")
    with open(p, "w") as fh:
        fh.write("\n".join(lines))
    return p


def _owners(profile, findings):
    """Who owns each term. The floor share comes from floor_attribution's three
    estimators, reported as a RANGE - none of them is authoritative alone."""
    l2 = findings.get("level2") or {}
    counts = {k: v["count"] for k, v in profile["layers"]["types"].items()}
    floor_owner, prefix_owner = "-", "-"

    fa = l2.get("floor_attribution")
    if fa:
        dom = fa["dominant_layer_type"]
        lo, hi = fa["share_pct_range"]
        floor_owner = (f"~{lo:.0f}-{hi:.0f}% the {counts[dom]} **{dom}** layers, by count"
                       if hi - lo > 1 else f"~{hi:.0f}% the {counts[dom]} **{dom}** layers, by count")

    for e in l2.get("pairs", []):
        grower = max(e["layers"], key=lambda lt: e["layers"][lt]["delta_ms"])
        g = e["layers"][grower]
        if g.get("growth_share_pct"):
            prefix_owner = f"**{g['growth_share_pct']:.0f}%** the {counts[grower]} **{grower}** layers"
        break

    l1 = findings.get("level1") or {}
    if l1.get("by_chunk"):
        e = list(l1["by_chunk"].values())[0]
        flat = [lt for lt, p in e["by_layer_type"].items()
                if p.get("slope_ms") is not None and abs(p["slope_ms"]) < 0.01]
        grow = [lt for lt, p in e["by_layer_type"].items()
                if p.get("slope_ms") is not None and abs(p["slope_ms"]) >= 0.01]
        if prefix_owner == "-" and grow:
            prefix_owner = f"the **{'/'.join(grow)}** layers"
        if floor_owner == "-" and flat:
            floor_owner = f"mostly the **{'/'.join(flat)}** layers, by count"
    return {"floor": floor_owner, "prefix": prefix_owner}


def _floor_cause(findings):
    f = (findings.get("level0") or {}).get("floor") or {}
    if f.get("chunk_invariant_cost_ms"):
        return (f"a **~{f['chunk_invariant_cost_ms']:.0f} ms chunk-invariant cost** paid once per "
                f"chunk, so a smaller chunk pays it more often")
    return "a cost that does not shrink with the chunk"


def _prefix_cause(profile, findings):
    l2 = findings.get("level2") or {}
    occ = l2.get("occupancy") or {}
    if occ:
        ks = sorted(occ, key=lambda k: int(k))
        lo = occ[ks[0]]
        if lo:
            return (f"the growing op leaves **{100-lo['useful_pct']:.0f}% of the core grid idle** at "
                    f"chunk {ks[0]} ({lo['work_units']} work units on ~{lo['grid_cores']} cores) and "
                    f"pays more steps")
    return "the one op that grows with context"


def write_report(run_dir, profile, findings, caps, rendered_text):
    L = [f"# {profile['model']} prefill perf - full record", "",
         f"Generated by the `prefill-perf-debug` skill on {time.strftime('%Y-%m-%d %H:%M')}.",
         f"Tree `{profile.get('tree')}`, branch `{H.git_info(profile.get('tree','.'))['branch']}`, "
         f"mesh {profile.get('mesh',{}).get('id')}.", "",
         "Read [TLDR.md](TLDR.md) first; this is the record behind it.", ""]

    if caps:
        L += ["## Capability probe", "", "| capability | present | detail |", "|---|---|---|"]
        for c in caps:
            L.append(f"| {c.name} | {'yes' if c.present else '**no**'} | {c.detail} |")
        L.append("")
        for c in caps:
            if not c.present:
                L.append(f"- **{c.name} absent** -> {c.consequence}")
        L.append("")

    for key, title in (("level0", "Level 0 - which cost term"),
                       ("level1", "Level 1 - which layers"),
                       ("level2", "Level 2 - which ops"),
                       ("level3", "Level 3 - what it is bound by (assisted)")):
        if key in rendered_text:
            L += [f"## {title}", "", "```", rendered_text[key].rstrip(), "```", ""]

    rec = findings.get("reconciliation") or []
    if rec:
        L += ["## Reconciliation between levels", "",
              "Every level must reconcile to the level above it. A level that does not close is "
              "a finding, not something to paper over.", "",
              "| assertion | status | detail |", "|---|---|---|"]
        for a in rec:
            L.append(f"| {a['id']} | {a['status'].upper()} | {a['detail']} |")
        L.append("")

    fired = _assert_lines(findings)
    if fired:
        L += ["## Assertions that fired", "", "| where | id | status | detail |", "|---|---|---|---|"]
        for b, a in fired:
            L.append(f"| {b} | {a['id']} | {a['status'].upper()} | {a['detail']} |")
        L.append("")

    L += ["## Traps that applied to this run", ""]
    L += [f"- {t}" for t in findings.get("traps", [])] or ["- (none recorded)"]
    L += ["", "## Artifacts", "",
          "```", _tree(run_dir), "```", ""]
    p = os.path.join(run_dir, "REPORT.md")
    with open(p, "w") as fh:
        fh.write("\n".join(L))
    return p


def _tree(root, limit=60):
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        rel = os.path.relpath(dirpath, root)
        if rel != ".":
            out.append(f"{rel}/")
        for f in sorted(filenames):
            out.append(os.path.join("" if rel == "." else rel, f))
        if len(out) > limit:
            out.append("...")
            break
    return "\n".join(out)


def prune_raw(capture_dirs, dry_run=True):
    """Delete the ~4.8 GB per-capture raw device CSVs. Only the ops CSV is needed afterwards."""
    # os.walk, NOT glob("**"): the biggest copies live in `profiler/.logs/`, and glob
    # skips dot-directories, so a glob-based prune silently left ~10 GB per capture.
    names = {"profile_log_device.csv", "tracy_ops_times.csv", "tracy_ops_data.csv"}
    targets = []
    for d in capture_dirs:
        for root, _dirs, files in os.walk(d):
            for name in files:
                if name in names:
                    fp = os.path.join(root, name)
                    targets.append((fp, os.path.getsize(fp)))
    total = sum(s for _, s in targets)
    if not dry_run:
        for p, _ in targets:
            os.remove(p)
    return {"files": [p for p, _ in targets], "bytes": total,
            "human": H.human_bytes(total), "deleted": not dry_run}
