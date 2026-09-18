#!/usr/bin/env python3
"""prefill-perf-debug CLI. Every subcommand except `run` is offline and device-free.

  ppd.py probe    --profile gemma4                 capability probe; run this first
  ppd.py budget   --tier standard                  cost/disk estimate + device preflight
  ppd.py level0   --profile gemma4 --log L...      fit a/slope per chunk size
  ppd.py level1   --profile gemma4 --curve L...    per-layer-type depth curves
  ppd.py level2   --profile gemma4 [--pairs J]     per-op, depth 0 vs depth D
  ppd.py check    --profile gemma4 --csv C --chunk N       assertions over one capture
  ppd.py compare  --a A.csv --b B.csv --a-raw D --b-raw D  A6-guarded cross-branch diff
  ppd.py validate --profile gemma4                 the SPEC s6 regression test, offline
  ppd.py teach    [--level 0|1|2|3]                        the method, with the traps
  ppd.py level3   --list | --propose KNOB                  ASSISTED ablations (never auto-patched)
  ppd.py analyze  --profile gemma4 --goal "..."            every level + the output contract
  ppd.py run      --profile gemma4 --what e2e|capture ...  build + launch a device run
  ppd.py report   --run-dir D                      (re)emit TLDR.md / REPORT.md
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import helpers as H          # noqa: E402
import assertions as A       # noqa: E402
import levels as LV          # noqa: E402
import probe as PR           # noqa: E402
import report as RP          # noqa: E402

TIERS = {
    "triage":   {"desc": "level 0 at the legal chunk sizes", "e2e_points": 5, "captures": 0},
    "standard": {"desc": "+ level 1, + level 2 at two depths x two chunk sizes",
                 "e2e_points": 11, "captures": 4},
    "deep":     {"desc": "+ assisted level-3 ablations", "e2e_points": 17, "captures": 6},
}


# ── commands ─────────────────────────────────────────────────────────────────


def cmd_probe(args):
    prof = H.load_profile(args.profile)
    sample_log = args.log or (prof.get("validation", {}).get("level0", {}) or {}).get("log")
    caps = PR.probe(prof, sample_capture=args.capture, sample_log=sample_log)
    print(PR.render(caps, prof))
    if args.json:
        with open(args.json, "w") as fh:
            json.dump([c.to_dict() for c in caps], fh, indent=2)
    return 0 if all(c.present or not c.blocking for c in caps) else 2


def cmd_budget(args):
    prof = H.load_profile(args.profile) if args.profile else None
    t = TIERS[args.tier]
    n_e2e = args.e2e_points if args.e2e_points is not None else t["e2e_points"]
    n_cap = args.captures if args.captures is not None else t["captures"]
    m_e2e = (prof or {}).get("e2e", {}).get("minutes_per_point", 3)
    m_cap = (prof or {}).get("layer_bench", {}).get("minutes_per_capture", 12)
    gb_cap = (prof or {}).get("layer_bench", {}).get("gb_per_capture", 5)
    minutes = n_e2e * m_e2e + n_cap * m_cap
    gb = n_cap * gb_cap

    print(f"Budget tier: {args.tier} - {t['desc']}")
    print(f"  {n_e2e} e2e point(s) x ~{m_e2e} min      = ~{n_e2e*m_e2e} min")
    print(f"  {n_cap} profiler capture(s) x ~{m_cap} min = ~{n_cap*m_cap} min, ~{gb} GB raw")
    print(f"  TOTAL ~{minutes//60}h {minutes%60}m device time, ~{gb} GB disk")
    print()
    where = _workdir(args, prof)
    free = LV.disk_free(where)
    print(f"Disk at {where}: {H.human_bytes(free)} free; need ~{gb} GB "
          f"({'OK' if free > gb * 1.2 * 2**30 else 'TIGHT - prune as you go'})")
    print("  Only the ~37 MB ops CSV is needed after rendering. The ~4.8 GB "
          "profile_log_device.csv per capture can be pruned (`ppd.py prune`).")
    print()
    d = LV.device_busy()
    held = {dev: pids for dev, pids in d["holders"].items() if pids}
    print(f"Devices: {len(d['devices'])} node(s), {len(held)} with a visible holder")
    for dev, pids in sorted(held.items()):
        print(f"  {dev}: held by pid {','.join(pids)}")
    print(f"  CAVEAT: {d['caveat']}")
    print()
    print("Runs serialise. NEVER parallelise device runs. Get consent before starting a sweep.")
    return 0


def cmd_level0(args):
    prof = H.load_profile(args.profile)
    logs = args.log or [(prof.get("validation", {}).get("level0", {}) or {}).get("log")]
    logs = [l for l in logs if l and os.path.exists(l)]
    if not logs:
        raise SystemExit("no readable --log given, and the profile has no validation level0 log")
    res = LV.level0(prof, logs, isl=args.isl, reference_chunk=args.reference, goal=args.goal)
    print(LV.render_level0(res))
    if args.json:
        with open(args.json, "w") as fh:
            json.dump(res, fh, indent=2)
    return 0


def cmd_level1(args):
    prof = H.load_profile(args.profile)
    l0 = None
    if args.level0_log:
        l0 = LV.level0(prof, [args.level0_log], isl=args.isl)
    curves = args.curve or list((prof.get("artifacts", {}).get("level1_logs") or {}).values())
    curves = [c for c in curves if c and os.path.exists(c)]
    if curves:
        res = LV.level1_depth_curves(prof, curves, l0)
        print(LV.render_level1(res))
    if args.layer_counts or (args.use_profile_layer_counts and prof.get("artifacts", {}).get("layer_count_logs")):
        spec = json.loads(args.layer_counts) if args.layer_counts else prof["artifacts"]["layer_count_logs"]
        res2 = LV.level1_layer_counts(prof, spec)
        print()
        print(LV.render_level1(res2))
    return 0


def _pairs_from_profile(prof):
    """Build floor/deep pairs from the captures the profile knows about."""
    arts = prof.get("artifacts", {})
    base = arts.get("runs_dir", "")
    caps = arts.get("captures", {})
    by_chunk = {}
    for tag, meta in caps.items():
        by_chunk.setdefault(meta["chunk"], {})[("floor" if meta["prior_ctx"] == 0 else "deep")] = \
            {"tag": tag, "dir": os.path.join(base, tag), **meta}
    pairs = []
    for chunk, sides in sorted(by_chunk.items()):
        if "floor" in sides and "deep" in sides:
            pairs.append({"name": f"c{chunk}", "chunk": chunk, "floor": sides["floor"], "deep": sides["deep"]})
    return pairs


def cmd_level2(args):
    prof = H.load_profile(args.profile)
    pairs = json.load(open(args.pairs)) if args.pairs else _pairs_from_profile(prof)
    if not pairs:
        raise SystemExit("no floor/deep capture pairs: pass --pairs <json> or fill "
                         "artifacts.captures in the profile")
    out_dir = args.out or os.path.join(os.getcwd(), "prefill-perf-level2")
    os.makedirs(out_dir, exist_ok=True)
    res = LV.level2(prof, pairs, out_dir)
    print(LV.render_level2(prof, res))
    if args.level0_log:
        l0 = LV.level0(prof, [args.level0_log], isl=args.isl)
        rec = LV.level2_reconcile(prof, res, l0)
        print("\nreconciliation against level 0 (A10):")
        for a in rec:
            print(f"  [{a['status'].upper():<4}] {a['id']}: {a['detail']}")
        res["reconciliation"] = rec
    if args.json:
        with open(args.json, "w") as fh:
            json.dump(res, fh, indent=2)
    return 0


def cmd_check(args):
    prof = H.load_profile(args.profile)
    rows = H.load_ops(args.csv)
    out = A.run_capture_checks(rows, prof, args.chunk, capture_cmd=args.cmd)
    for a in out:
        print(a)
    return 0 if A.gate(out) else 2


def cmd_compare(args):
    """A6/A12-guarded cross-branch per-op comparison."""
    prof = H.load_profile(args.profile) if args.profile else None
    side_a = {"label": args.a_label or os.path.basename(args.a), "raw_capture": args.a_raw,
              "rendered_from_raw": bool(args.a_raw), "tool_version": H.perf_report_version(),
              "build": args.a_build}
    side_b = {"label": args.b_label or os.path.basename(args.b), "raw_capture": args.b_raw,
              "rendered_from_raw": bool(args.b_raw), "tool_version": H.perf_report_version(),
              "build": args.b_build}
    checks = [A.A6_rerendered_both_sides(side_a, side_b),
              A.A12_same_build(side_a, side_b, allow_cross_build=args.cross_build)]
    for c in checks:
        print(c)
    if not A.gate(checks):
        print("\nREFUSED: fix the above before reporting any delta. A number lifted from an old "
              "writeup produced a false +21% regression once; per-device spread on one op is ~17%.")
        return 2
    ga = H.group_ops(H.load_ops(args.a))
    gb = H.group_ops(H.load_ops(args.b))
    keys = sorted(set(ga) | set(gb), key=lambda k: -max(ga.get(k, {"device_us": 0})["device_us"],
                                                        gb.get(k, {"device_us": 0})["device_us"]))
    print(f"\n{'op':<44}{side_a['label'][:12]:>13}{side_b['label'][:12]:>13}{'delta':>10}")
    print("-" * 80)
    ta = tb = 0.0
    for k in keys:
        a = ga.get(k, {"device_us": 0.0})["device_us"]
        b = gb.get(k, {"device_us": 0.0})["device_us"]
        ta += a
        tb += b
        d = f"{100*(b-a)/a:+.1f}%" if a else "new"
        print(f"{k:<44}{a:>13.1f}{b:>13.1f}{d:>10}")
    print("-" * 80)
    print(f"{'TOTAL (sum of Device Time, us)':<44}{ta:>13.1f}{tb:>13.1f}"
          f"{(100*(tb-ta)/ta if ta else 0):>9.1f}%")
    return 0


def cmd_run(args):
    prof = H.load_profile(args.profile)
    if args.what == "e2e":
        cmd = LV.build_e2e_cmd(prof, args.chunk, args.ctx, extra_env=json.loads(args.env) if args.env else None)
    else:
        cmd = LV.build_capture_cmd(prof, args.chunk, args.chunk_idx, args.layer_type, args.ctx,
                                   args.out or os.getcwd())
    chk = A.A5_no_device_trace_profiler(cmd)
    print(chk)
    if chk.status == "fail":
        return 2
    print(f"\ncommand:\n  {cmd}\n")
    if not args.launch:
        print("Not launched. Re-run with --launch after checking the device is free "
              "(`ppd.py budget`) and the user has consented to the cost.")
        return 0
    d = LV.device_busy()
    held = {k: v for k, v in d["holders"].items() if v}
    if held and not args.force:
        print(f"Device appears held: {held}. Re-run with --force if that is your own run.")
        return 2
    info = LV.launch_detached(prof, cmd, args.log or os.path.join(args.out or os.getcwd(), "run.log"))
    print(f"launched detached pid={info['pid']}  log={info['log']}")
    print("Poll the log; do NOT kill it. A SIGKILL mid-fabric makes the next mesh open fail with "
          "'Timed out while waiting for active ethernet core ... to become active again' "
          "(recover with tt-smi -r).")
    return 0


def _workdir(args, prof):
    """Where run directories go.

    NOT the cwd by default: the natural cwd for this work is the model checkout, and
    dropping a prefill-perf/ tree into someone's git repo is not acceptable. Order:
    --workdir, $PPD_WORKDIR, the profile's artifacts.runs_dir, then cwd as a last resort.
    """
    for cand in (args.workdir if hasattr(args, "workdir") else None,
                 os.environ.get("PPD_WORKDIR"),
                 (prof.get("artifacts") or {}).get("runs_dir")):
        if cand and os.path.isdir(cand):
            return cand
    cwd = os.getcwd()
    if os.path.isdir(os.path.join(cwd, ".git")):
        print(f"NOTE: {cwd} is a git repo and no --workdir/$PPD_WORKDIR/profile runs_dir "
              f"is set; writing run artifacts here would pollute it.", file=sys.stderr)
    return cwd


def cmd_teach(args):
    import teach as T
    print(T.render(args.level, args.profile))
    return 0


def cmd_level3(args):
    import level3 as L3
    prof = H.load_profile(args.profile)
    if args.list:
        print(L3.list_catalogue(prof))
        return 0
    if args.propose:
        print(L3.propose(prof, args.propose, args.run_dir))
        return 0
    if args.record_baseline:
        print(L3.record_baseline(prof, args.record_baseline))
        return 0
    if args.verify_revert:
        rc, msg = L3.verify_revert(prof, args.verify_revert)
        print(msg)
        return rc
    print(L3.list_catalogue(prof))
    return 0


def cmd_analyze(args):
    """Run every level that has data, emit the output contract, print the TLDR."""
    prof = H.load_profile(args.profile)
    run_dir = args.run_dir or RP.new_run_dir(_workdir(args, prof), prof["model"])
    rendered_text, findings = {}, {}

    caps = PR.probe(prof, sample_log=args.level0_log or
                    (prof.get("validation", {}).get("level0", {}) or {}).get("log"))
    rendered_text["probe"] = PR.render(caps, prof)

    l0log = args.level0_log or (prof.get("validation", {}).get("level0", {}) or {}).get("log")
    l0 = None
    if l0log and os.path.exists(l0log):
        l0 = LV.level0(prof, [l0log], isl=args.isl, reference_chunk=args.reference,
                       goal=args.goal)
        findings["level0"] = l0
        rendered_text["level0"] = LV.render_level0(l0)

    curves = args.curve or [c for c in (prof.get("artifacts", {}).get("level1_logs") or {}).values()
                            if os.path.exists(c)]
    if curves:
        l1 = LV.level1_depth_curves(prof, curves, l0)
        findings["level1"] = l1
        rendered_text["level1"] = LV.render_level1(l1)

    pairs = json.load(open(args.pairs)) if args.pairs else _pairs_from_profile(prof)
    if pairs and not args.skip_level2:
        l2 = LV.level2(prof, pairs, os.path.join(run_dir, "reports"))
        findings["level2"] = l2
        rendered_text["level2"] = LV.render_level2(prof, l2)
        if l0:
            findings["reconciliation"] = LV.level2_reconcile(prof, l2, l0)

    findings["traps"] = [a["detail"] for blk in ("level0", "level2")
                         for a in (findings.get(blk, {}).get("assertions") or [])
                         if a["status"] in ("warn", "fail")]
    findings["_rendered"] = rendered_text

    src_logs = [l for l in ([l0log] + list(curves)) if l]
    src_caps = [p[side]["dir"] for p in (pairs or []) for side in ("floor", "deep")
                if p.get(side, {}).get("dir")]
    RP.record_sources(run_dir, src_logs, src_caps if not args.skip_level2 else [])
    RP.write_manifest(run_dir, prof, args.tier, args.goal, caps,
                      extra={"sources": {"logs": src_logs, "captures": src_caps}})
    RP.write_findings(run_dir, findings)
    RP.write_tldr(run_dir, prof, findings, args.goal, levers=args.levers and json.loads(args.levers))
    RP.write_report(run_dir, prof, findings, caps, rendered_text)
    print(rendered_text.get("probe", ""))
    for k in ("level0", "level1", "level2"):
        if k in rendered_text:
            print("\n" + rendered_text[k])
    print(f"\nrun directory: {run_dir}"
          f"\n  (override with --workdir or $PPD_WORKDIR)")
    print(f"  TLDR.md  REPORT.md  manifest.json  findings.json  reports/")
    return 0


def cmd_prune(args):
    res = RP.prune_raw(args.dir, dry_run=not args.yes)
    print(f"{len(res['files'])} raw device CSV(s), {res['human']}"
          + (" DELETED" if res["deleted"] else " would be deleted (pass --yes)"))
    for f in res["files"][:20]:
        print("  " + f)
    return 0


def cmd_validate(args):
    import validate as V
    return V.main(args.profile, verbose=not args.quiet, tolerance=args.tolerance)


def cmd_report(args):
    prof = H.load_profile(args.profile)
    findings = json.load(open(os.path.join(args.run_dir, "findings.json")))
    RP.write_tldr(args.run_dir, prof, findings, args.goal)
    RP.write_report(args.run_dir, prof, findings, None, findings.get("_rendered", {}))
    print(f"wrote {args.run_dir}/TLDR.md and REPORT.md")
    return 0


# ── argument parsing ─────────────────────────────────────────────────────────


def main(argv=None):
    ap = argparse.ArgumentParser(prog="ppd.py", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("probe", help="capability probe")
    p.add_argument("--profile", default="gemma4")
    p.add_argument("--log", help="a sample e2e run log (stronger evidence than source grepping)")
    p.add_argument("--capture", help="a sample capture dir or ops CSV (for the utilization check)")
    p.add_argument("--json")
    p.set_defaults(fn=cmd_probe)

    p = sub.add_parser("budget", help="cost / disk / device preflight")
    p.add_argument("--tier", choices=list(TIERS), default="triage")
    p.add_argument("--profile", default="gemma4")
    p.add_argument("--e2e-points", type=int)
    p.add_argument("--captures", type=int)
    p.add_argument("--workdir")
    p.set_defaults(fn=cmd_budget)

    p = sub.add_parser("level0", help="fit a/slope per chunk size")
    p.add_argument("--profile", default="gemma4")
    p.add_argument("--log", action="append")
    p.add_argument("--isl", type=int)
    p.add_argument("--reference", type=int,
                   help="chunk size to quote ratios against (default: parsed from --goal, "
                        "else the best total)")
    p.add_argument("--goal", help="the user's question; two chunk sizes in it set --reference")
    p.add_argument("--json")
    p.set_defaults(fn=cmd_level0)

    p = sub.add_parser("level1", help="per-layer-type depth curves / layer-count differencing")
    p.add_argument("--profile", default="gemma4")
    p.add_argument("--curve", action="append", help="isolated-layer benchmark log(s)")
    p.add_argument("--level0-log", help="e2e log to reconcile the reconstructed slope against")
    p.add_argument("--layer-counts", help='JSON {"chunk": {"60": log, "12": log}}')
    p.add_argument("--use-profile-layer-counts", action="store_true")
    p.add_argument("--isl", type=int)
    p.set_defaults(fn=cmd_level1)

    p = sub.add_parser("level2", help="per-op attribution, depth 0 vs depth D")
    p.add_argument("--profile", default="gemma4")
    p.add_argument("--pairs", help="JSON list of floor/deep pairs; defaults to the profile's captures")
    p.add_argument("--out", help="where to write the re-rendered CSVs/tables")
    p.add_argument("--level0-log", help="reconcile per-op sums against level 0 (A10)")
    p.add_argument("--isl", type=int)
    p.add_argument("--json")
    p.set_defaults(fn=cmd_level2)

    p = sub.add_parser("check", help="assertions over one rendered capture")
    p.add_argument("--profile", default="gemma4")
    p.add_argument("--csv", required=True)
    p.add_argument("--chunk", type=int, required=True)
    p.add_argument("--cmd", help="the capture command, checked for A5")
    p.set_defaults(fn=cmd_check)

    p = sub.add_parser("compare", help="A6-guarded per-op comparison of two rendered captures")
    p.add_argument("--profile")
    p.add_argument("--a", required=True)
    p.add_argument("--b", required=True)
    p.add_argument("--a-raw", help="the raw ops CSV / capture dir side A was rendered from")
    p.add_argument("--b-raw")
    p.add_argument("--a-label")
    p.add_argument("--b-label")
    p.add_argument("--a-build")
    p.add_argument("--b-build")
    p.add_argument("--cross-build", action="store_true",
                   help="declare this a deliberate cross-branch check (A12 becomes a warning)")
    p.set_defaults(fn=cmd_compare)

    p = sub.add_parser("run", help="build (and optionally launch) a device run")
    p.add_argument("--profile", default="gemma4")
    p.add_argument("--what", choices=["e2e", "capture"], default="e2e")
    p.add_argument("--chunk", type=int, required=True)
    p.add_argument("--ctx", type=int, default=32768)
    p.add_argument("--chunk-idx", type=int, default=0)
    p.add_argument("--layer-type", default="both")
    p.add_argument("--out")
    p.add_argument("--log")
    p.add_argument("--env", help="JSON dict of extra env vars")
    p.add_argument("--launch", action="store_true")
    p.add_argument("--force", action="store_true")
    p.set_defaults(fn=cmd_run)

    p = sub.add_parser("teach", help="explain as you go: question, prediction, command, why valid")
    p.add_argument("--profile", default="gemma4")
    p.add_argument("--level", type=int, choices=[0, 1, 2, 3])
    p.set_defaults(fn=cmd_teach)

    p = sub.add_parser("level3", help="ASSISTED ablations: propose, snapshot, verify the revert")
    p.add_argument("--profile", default="gemma4")
    p.add_argument("--list", action="store_true")
    p.add_argument("--propose", metavar="KNOB")
    p.add_argument("--record-baseline", metavar="DIR")
    p.add_argument("--verify-revert", metavar="DIR")
    p.add_argument("--run-dir")
    p.set_defaults(fn=cmd_level3)

    p = sub.add_parser("analyze", help="run every level that has data and emit the output contract")
    p.add_argument("--profile", default="gemma4")
    p.add_argument("--goal", help="what the user asked (routes the report's headline)")
    p.add_argument("--tier", choices=list(TIERS), default="triage")
    p.add_argument("--workdir")
    p.add_argument("--run-dir")
    p.add_argument("--level0-log")
    p.add_argument("--curve", action="append")
    p.add_argument("--pairs")
    p.add_argument("--skip-level2", action="store_true")
    p.add_argument("--reference", type=int)
    p.add_argument("--isl", type=int)
    p.add_argument("--levers", help="JSON list of {option, effect, status}")
    p.set_defaults(fn=cmd_analyze)

    p = sub.add_parser("prune", help="delete the ~4.8 GB raw device CSVs of finished captures")
    p.add_argument("dir", nargs="+")
    p.add_argument("--yes", action="store_true")
    p.set_defaults(fn=cmd_prune)

    p = sub.add_parser("validate", help="the SPEC s6 regression test (offline, no device)")
    p.add_argument("--profile", default="gemma4")
    p.add_argument("--tolerance", type=float)
    p.add_argument("--quiet", action="store_true")
    p.set_defaults(fn=cmd_validate)

    p = sub.add_parser("report", help="(re)emit TLDR.md / REPORT.md from findings.json")
    p.add_argument("--profile", default="gemma4")
    p.add_argument("--run-dir", required=True)
    p.add_argument("--goal")
    p.set_defaults(fn=cmd_report)

    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
