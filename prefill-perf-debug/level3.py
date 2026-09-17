#!/usr/bin/env python3
"""Level 3 - ASSISTED ONLY. This module proposes and verifies; it never patches.

Ablation sites are model-specific (`ring_prefill.py`, `attention/__init__.py`,
`model_config.py` in Gemma4) and cannot be inferred for an unseen model.

Why this is not automated: an unsupervised patch/revert already cost three runs. A
`git checkout` of one file silently dropped an `import os` that an earlier diagnostic
patch had added, and the next run died with `NameError: name 'os' is not defined`
partway through. The fix is not "be careful" - it is to snapshot the working tree
BEFORE the patch and to diff it again after the revert, which is what this module does.

Protocol, in order:
  1. ppd.py level3 --list                     see what is measurable on this model
  2. write PREDICTION.md                      A7: competing predictions and what falsifies each
  3. ppd.py level3 --record-baseline DIR      snapshot the pre-patch working tree
  4. <user approves, then the patch is applied by hand or by Claude with approval>
  5. run the ablation, and a CONTROL that should not move (A8)
  6. ppd.py level3 --verify-revert DIR        the working tree must match the snapshot byte for byte
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import helpers as H
import assertions as A


def _git(tree, *args):
    return subprocess.run(["git", "-C", tree, *args], capture_output=True, text=True).stdout


def list_catalogue(profile):
    cat = profile.get("ablation_catalogue") or []
    if not cat:
        return (f"No ablation catalogue for {profile['model']}.\n"
                "Level 3 needs model-specific sites. Read the op's source, name ONE cost term "
                "you can vary while holding the rest fixed, and add it to the profile.")
    L = [f"Level 3 ablation catalogue - {profile['model']}  (ASSISTED: propose, approve, verify)", ""]
    L.append(f"{'knob':<32}{'varies':<26}{'measured':>10}  conclusion")
    L.append("-" * 104)
    for ab in cat:
        m = f"{ab['measured']:.3f}x" if ab.get("measured") is not None else "-"
        L.append(f"{ab.get('knob',''):<32}{ab.get('varies',''):<26}{m:>10}  {ab.get('conclusion','')}")
    L += ["", "sites (each needs a TEMPORARY edit, reverted and verified):"]
    for ab in cat:
        if ab.get("site"):
            L.append(f"  {ab.get('knob','')}: {ab['site']}")
    if profile.get("ablation_sites_note"):
        L += ["", profile["ablation_sites_note"]]
    L += ["", "Scope note (A1): an ablation refutes or supports exactly the term it varied.",
          "  e.g. bfp4 halves BYTES but not tile count, so it refutes byte-bandwidth bound,",
          "  not per-tile overhead. Only the fidelity response positively rules math IN."]
    return "\n".join(L)


def propose(profile, knob, run_dir=None):
    base = knob.split("=")[0]
    matches = [ab for ab in (profile.get("ablation_catalogue") or [])
               if ab.get("knob", "").split("=")[0] == base
               and (("=" not in knob) or ab.get("knob") == knob)]
    L = [f"PROPOSED ABLATION: {knob}", ""]
    if len(matches) > 1:
        L.append(f"  {len(matches)} settings of this knob are catalogued; "
                 f"a fidelity-style knob is only informative measured in BOTH directions:")
    for ab in matches:
        known = "" if ab.get("measured") is None else f" {ab['measured']:.3f}x"
        L += [f"  {ab.get('knob')}",
              f"    varies:      {ab.get('varies')}",
              f"    site:        {ab.get('site')}",
              f"    known result:{known} {ab.get('conclusion','')}",
              f"    scope:       {ab.get('scope_note', 'states only what this knob varied')}", ""]
    if not matches:
        L += [f"'{knob}' is not in {profile['model']}'s catalogue. Add it to the profile first, "
              f"naming the site and the single cost term it varies.", ""]
    L += ["Before it runs, all of these must be true:", ""]
    if run_dir:
        L.append("  " + str(A.A7_prediction_registered(run_dir, knob)))
    else:
        L.append("  [ ] A7  PREDICTION.md written: the competing predictions and what falsifies each")
    L += ["  [ ] A8  a CONTROL is measured alongside - something that should NOT move",
          "  [ ] baseline snapshot recorded (`ppd.py level3 --record-baseline <dir>`)",
          "  [ ] the user has approved the patch",
          "",
          "This tool does NOT apply the patch. After the run:",
          "  ppd.py level3 --verify-revert <dir>   # refuses to pass unless the tree is byte-identical",
          "",
          "A1 reminder: report the conclusion for the term you varied and nothing wider."]
    return "\n".join(L)


def _snapshot(tree):
    diff = _git(tree, "diff", "HEAD")
    untracked = _git(tree, "ls-files", "--others", "--exclude-standard")
    return {
        "tree": tree,
        "sha": _git(tree, "rev-parse", "HEAD").strip(),
        "branch": _git(tree, "rev-parse", "--abbrev-ref", "HEAD").strip(),
        "diff_sha256": hashlib.sha256(diff.encode()).hexdigest(),
        "diff_bytes": len(diff),
        "untracked": sorted(untracked.split()),
        "status": _git(tree, "status", "--porcelain"),
    }


def record_baseline(profile, run_dir):
    os.makedirs(run_dir, exist_ok=True)
    snap = _snapshot(profile["tree"])
    p = os.path.join(run_dir, "pre_patch_snapshot.json")
    with open(p, "w") as fh:
        json.dump(snap, fh, indent=2)
    with open(os.path.join(run_dir, "pre_patch.diff"), "w") as fh:
        fh.write(_git(profile["tree"], "diff", "HEAD"))
    return (f"baseline recorded: {p}\n"
            f"  sha {snap['sha'][:12]} on {snap['branch']}, "
            f"{snap['diff_bytes']} bytes of uncommitted diff, "
            f"{len(snap['untracked'])} untracked file(s)\n"
            f"  The revert check compares against THIS. If the tree had uncommitted work before "
            f"the patch - as it did when a `git checkout` dropped an `import os` - the check "
            f"catches its loss.")


def verify_revert(profile, run_dir):
    p = os.path.join(run_dir, "pre_patch_snapshot.json")
    if not os.path.exists(p):
        return 2, (f"no baseline snapshot at {p}. Without one the revert CANNOT be verified; "
                   f"record it before patching next time, and inspect `git diff` by hand now.")
    with open(p) as fh:
        before = json.load(fh)
    after = _snapshot(profile["tree"])
    problems = []
    if before["sha"] != after["sha"]:
        problems.append(f"HEAD moved: {before['sha'][:12]} -> {after['sha'][:12]}")
    if before["diff_sha256"] != after["diff_sha256"]:
        problems.append(f"working tree differs from the pre-patch snapshot "
                        f"({before['diff_bytes']} -> {after['diff_bytes']} bytes of diff)")
    lost = set(before["untracked"]) - set(after["untracked"])
    gained = set(after["untracked"]) - set(before["untracked"])
    if lost:
        problems.append(f"untracked files LOST: {sorted(lost)}")
    if gained:
        problems.append(f"untracked files added: {sorted(gained)}")
    if not problems:
        return 0, (f"REVERT VERIFIED: the tree is byte-identical to the pre-patch snapshot "
                   f"(sha {after['sha'][:12]}, {after['diff_bytes']} bytes of diff).")
    out = ["REVERT NOT CLEAN:"] + [f"  - {x}" for x in problems]
    out += ["", "Do NOT start the next run. `git diff` against pre_patch.diff in this run dir and "
            "restore anything the revert dropped. This is exactly the failure that cost three runs: "
            "a `git checkout` removed an `import os` a previous patch had added, and the next run "
            "died with NameError partway through."]
    return 2, "\n".join(out)
