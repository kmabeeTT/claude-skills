#!/usr/bin/env python3
"""Render a prefill what-if profile JSON into one self-contained HTML page (for the Artifact tool).

Usage: render_whatif.py PROFILE.json OUT.html
The page embeds the profile; Chart.js loads from cdnjs. Nothing else is fetched.
"""
import html
import json
import os
import sys

REQUIRED = ["schema", "title", "model", "hardware", "layer_types", "components", "peaks", "dram_options", "fabric_gbs",
            "presets", "whatif_base", "chunks", "target_presets", "notes"]


def check(p):
    """Schema v2: presets[id].layers[L][first|depth][component id] = us; work[L][component id] = model inputs."""
    missing = [k for k in REQUIRED if k not in p]
    if missing:
        sys.exit(f"profile is missing keys: {missing}")
    if p.get("schema") != 2:
        sys.exit("profile must say \"schema\": 2 (per-component layer times)")
    comps = {c["id"]: c for c in p["components"]}
    need = {"roofline": ["ops"], "sdpa_rate": ["gflop_first", "gflop_depth"], "ref_ratio": ["ref_us"], "scale": ["target_us"]}
    for C, ch in p["chunks"].items():
        for pr in p["presets"]:
            layers = ch["presets"][pr["id"]]["layers"]
            for lt in p["layer_types"]:
                for pos in ("first", "depth"):
                    bad = set(layers[lt["id"]][pos]) - set(comps)
                    if bad:
                        sys.exit(f"chunk {C} preset {pr['id']} layer {lt['id']}: unknown components {bad}")
        for L, w in ch["work"].items():
            for cid, wc in w.items():
                for k in need[comps[cid]["model"]]:
                    if k not in wc:
                        sys.exit(f"chunk {C} work[{L}][{cid}] missing {k}")
    if p["whatif_base"] not in {pr["id"] for pr in p["presets"]}:
        sys.exit("whatif_base must be one of the presets")


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    prof = json.load(open(sys.argv[1]))
    check(prof)
    tpl = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "whatif_template.html")).read()
    data = json.dumps(prof, separators=(",", ":")).replace("</", "<\\/")
    out = tpl.replace("__TITLE__", html.escape(prof["title"])).replace("/*__PROFILE__*/null", data)
    open(sys.argv[2], "w").write(out)
    print(f"wrote {sys.argv[2]} ({len(out) // 1024} KB)")


if __name__ == "__main__":
    main()
