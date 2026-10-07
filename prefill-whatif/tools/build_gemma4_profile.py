#!/usr/bin/env python3
"""Build the Gemma4-31B (BH Galaxy 8x4) what-if profile JSON from the layer-profile captures.

Inputs (all in the gemma4 perf_understand folder, default ~/prefill-docs/gemma4/perf_understand):
  - LAYER_PROFILES_3SETS.md: per-layer category split (matmul / SDPA / collectives / small ops) for
    set1 / set2 / set3 x chunk 2048 / 4096 / 8192 x first / depth x global / local.
  - harness/perf_vs_target/perf_vs_target.json: set3's per-op work (matmul GFLOP / DRAM MB / fidelity,
    SDPA GFLOP on the busiest device). The what-if model needs work, not just times.
  - harness/perf_vs_target/targets.txt: the "B" targets for collectives (in-tree reference fit) and
    small ops (layout ops removed).

Whole-model measured numbers (first chunk / ~100k / 256k) are written below with their sources;
they are shown next to the reconstruction, never mixed into it.

Usage: build_gemma4_profile.py [--docs DIR] --out profile.json
"""
import argparse
import json
import os
import re

SETS = {"set1": "baseline", "set2": "week1", "set3": "week2"}
CHUNKS = [2048, 4096, 8192]
CP = 8
SLIDING_WINDOW = 1024
HEADS_PER_DEVICE = 8

# Measured whole-model numbers. Cells: first chunk ms, mid-context wall s, 256k device s.
# set2 / set3: perf-journey 10-04 tracker rows R0 / R5 (bh-glx-120-c03u08, 130 W), mid = 100k wall
#   (102,400 tokens at 2k / 4k, 106,496 at 8k).
# set1: perf-journey week 1, "+ #57453" row (115 W TDP), mid = 106k wall. Not the same power or harness.
MEASURED = {
    "set1": {2048: (121.0, 7.86, 25.5), 4096: (156.1, 5.04, 16.4), 8192: (194.1, 3.23, 11.2)},
    "set2": {2048: (63.5, 3.845, 11.59), 4096: (82.6, 2.484, 7.71), 8192: (123.1, 2.086, 6.84)},
    "set3": {2048: (53.7, 3.331, 10.30), 4096: (74.7, 2.291, 7.29), 8192: (114.5, 1.966, 6.57)},
}
MEASURED_NOTE = {
    "set1": "Measured at 115 W TDP, mid-context = 106k wall (perf-journey week 1, '+ #57453' row). Other presets are 130 W.",
    "set2": "Measured: perf-journey 10-04 row R0 (main), bh-glx-120-c03u08, 130 W. Mid-context = 100k wall.",
    "set3": "Measured: perf-journey 10-04 row R5 (e429a8414c1), bh-glx-120-c03u08, 130 W. Mid-context = 100k wall.",
}
PRESET_LABEL = {
    "set1": ("Baseline", "Before week 1's PRs: perf-journey R1 stack (main 09-28 without #57454 / #57931, with #57453)."),
    "set2": ("Week 1", "main 6571688cf68: adds #57454, #57931, #57979, #57998, #58032, #58033, #58223, #58224 and others."),
    "set3": ("Week 1 + Week 2", "Week 1 plus P3 #59049, P4 #59195, P5 #59214, P6 #59221, P7 #59222 (e429a8414c1)."),
}


def num(s):
    return float(s.replace("*", "").replace(",", "").strip())


def parse_layer_tables(md_path):
    """{chunk: {set: {layer: {pos: {matmul,sdpa,collectives,small,device, index}}}}}"""
    out = {}
    chunk = None
    for line in open(md_path):
        m = re.match(r"^## Chunk (\d+)", line)
        if m:
            chunk = int(m.group(1))
            out.setdefault(chunk, {})
            continue
        if chunk is None or not line.startswith("| "):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 8 or cells[2] not in SETS:
            continue
        pos_cell, layer, st = cells[0], cells[1], cells[2]
        if pos_cell == "first":
            pos, idx = "first", 1
        elif pos_cell.startswith("depth"):
            pos, idx = "depth", int(pos_cell.split()[1])
        else:
            continue
        layer = "sliding" if layer == "local" else layer
        out[chunk].setdefault(st, {}).setdefault(layer, {})[pos] = {
            "index": idx,
            "device": num(cells[3]),
            "matmul": num(cells[4]),
            "sdpa": num(cells[5]),
            "collectives": num(cells[6]),
            "small": num(cells[7]),
        }
    return out


def parse_targets(path):
    """B-level targets for collectives and small ops, first chunk: {chunk: {layer: {collectives, small}}}"""
    out = {}
    pat = re.compile(r"^(\d+) first (global|local): .*collectives: meas [\d.]+ A [\d.]+ B ([\d.]+).*small: meas [\d.]+ A [\d.]+ B ([\d.]+)")
    for line in open(path):
        m = pat.match(line)
        if m:
            layer = "sliding" if m.group(2) == "local" else "global"
            out.setdefault(int(m.group(1)), {})[layer] = {"collectives": float(m.group(3)), "small": float(m.group(4))}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--docs", default=next((d for d in (os.path.expanduser("~/prefill-docs/gemma4/perf_understand"), "/data/kmabee/prefill-docs-staging/gemma4/perf_understand") if os.path.isdir(d)), None))
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    layers = parse_layer_tables(os.path.join(a.docs, "LAYER_PROFILES_3SETS.md"))
    work = json.load(open(os.path.join(a.docs, "harness/perf_vs_target/perf_vs_target.json")))
    targets = parse_targets(os.path.join(a.docs, "harness/perf_vs_target/targets.txt"))

    chunks = {}
    for c in CHUNKS:
        slab = c // CP
        presets = {}
        for st, pid in SETS.items():
            fc, mid, full = MEASURED[st][c]
            presets[pid] = {
                "layers": {L: {pos: {"matmul": d["matmul"], ("gsdpa" if L == "global" else "lsdpa"): d["sdpa"],
                                     "coll": d["collectives"], "small": d["small"]}
                               for pos, d in layers[c][st][L].items()} for L in ("global", "sliding")},
                "measured": {"first_ms": fc, "mid_s": mid, "full_s": full},
            }
        depth_index = layers[c]["set3"]["global"]["depth"]["index"]
        w = {}
        for L, key in (("global", "global"), ("sliding", "local")):
            f, d = work[f"{c}|first"][key], work[f"{c}|depth"][key]
            mm = [{"name": m["name"], "gflop": m["gflop"], "mb": m["dram_mb"], "bw": "dram", "fid": m["fid"], "t_us": m["t_us"]}
                  for m in f["matmuls"]]
            if L == "sliding":
                g1 = gd = 4 * 256 * HEADS_PER_DEVICE * slab * SLIDING_WINDOW / 1e9  # busiest device: S x W pairs
            else:
                g1, gd = f["sdpa"]["gflop_maxdev"], d["sdpa"]["gflop_maxdev"]
            w[L] = {"matmul": {"ops": mm}, ("gsdpa" if L == "global" else "lsdpa"): {"gflop_first": g1, "gflop_depth": gd},
                    "coll": {"ref_us": targets[c][L]["collectives"]}, "small": {"target_us": targets[c][L]["small"]}}
        chunks[str(c)] = {
            "depth_index": depth_index,
            "checkpoints": [
                {"label": "TTFT (1 chunk)", "tokens": c, "measured_key": "first_ms", "unit": "ms"},
                {"label": "~100k", "tokens": 102400, "measured_key": "mid_s", "unit": "s"},
                {"label": "256k", "tokens": 262144, "measured_key": "full_s", "unit": "s"},
            ],
            "presets": presets,
            "work": w,
        }

    profile = {
        "schema": 2,
        "title": "Gemma4 Prefill What-If",
        "model": "Gemma4-31B-it chunked prefill",
        "hardware": "BH Galaxy 8x4 (CP=8 x TP=4, 32 chips), 130 W",
        "layer_types": [{"id": "global", "label": "Global attention", "count": 10},
                        {"id": "sliding", "label": "Sliding window", "count": 50}],
        "components": [
            {"id": "matmul", "label": "Matmuls", "model": "roofline", "color": "--c-matmul"},
            {"id": "gsdpa", "label": "Global SDPA", "model": "sdpa_rate", "peak": "sdpa_lofi", "color": "--c-gsdpa"},
            {"id": "lsdpa", "label": "Sliding SDPA", "model": "sdpa_rate", "peak": "sdpa_hifi2", "color": "--c-lsdpa"},
            {"id": "coll", "label": "Collectives", "model": "ref_ratio", "color": "--c-coll"},
            {"id": "small", "label": "Small ops", "model": "scale", "color": "--c-small", "hint": "Target removes layout-only ops"},
        ],
        # TFLOP/s at 1.35 GHz. Matmuls: 120 cores x 4,096 (LoFi) / 2,048 (HiFi2) FLOP/cycle.
        # Ring SDPA: 110 compute cores. Sliding SDPA runs HiFi2, global QK/PV LoFi.
        "peaks": {"LoFi": 663.6, "HiFi2": 331.8, "sdpa_lofi": 608.3, "sdpa_hifi2": 304.1},
        "dram_options": [{"label": "RevC 512 GB/s", "gbs": 512}, {"label": "RevB 384 GB/s", "gbs": 384}],
        "fabric_gbs": 50,
        # Fallback rate for an SDPA whose first and depth GFLOP are equal (sliding): cross-size fit
        # t = 110.5 us + 24.55 us/GFLOP -> 40.7 TFLOP/s marginal (PERF_VS_TARGET_GEMMA4.md 4.4).
        "sdpa_fallback_rate_tflops": {"lsdpa": 40.7},
        "target_presets": [
            {"label": "Target: 70% util", "values": {"matmul": {"util": 70}, "gsdpa": {"util": 70, "fixed": 0},
                                                      "lsdpa": {"util": 70, "fixed": 0}, "coll": {"eff": 100}, "small": {"pct": "target"}}},
        ],
        "presets": [{"id": SETS[s], "label": PRESET_LABEL[s][0], "desc": PRESET_LABEL[s][1], "measured_note": MEASURED_NOTE[s]}
                    for s in SETS],
        "whatif_base": "week2",
        "chunks": chunks,
        "notes": [
            "Times are reconstructed from per-layer captures (one global + one sliding layer, first chunk and near 256k depth), summed as 10 global + 50 sliding layers, linear in chunk index between the two captures. The reconstruction is within about 4% of measured end-to-end time.",
            "Captures: bh-glx-120-c03u02, 2026-10-05, RevB board at 130 W (LAYER_PROFILES_3SETS.md). Whole-model measured numbers come from the perf-journey trackers.",
            "Matmul util is % of the roofline: the slower of compute at the op's fidelity (120 cores, 1.35 GHz) and weight + activation DRAM traffic at the chosen bandwidth. At chunk 2048 (M = 256 rows per device) the matmuls are weight-streaming, so 70% FLOP util is out of reach there (max ~37% LoFi at full bandwidth).",
            "SDPA util is % of the ring SDPA's 110-core peak at the kernel's fidelity (LoFi global, HiFi2 sliding), applied to useful causal FLOPs on the busiest device. 'Fixed' is the per-layer cost that doesn't scale with work (halo, setup).",
            "Collectives: % of the in-tree Galaxy reference speed for the same bytes. Small ops: % of today's time; the target removes layout-only ops and half the global RoPE gather.",
            "Long context runs under the 130 W cap (late-chunk clock ~1.2-1.3 GHz); the model doesn't apply a clock change.",
        ],
        "sources": "~/prefill-docs/gemma4/perf_understand/: LAYER_PROFILES_3SETS.md, PERF_VS_TARGET_GEMMA4.md, harness/perf_vs_target/",
    }
    with open(a.out, "w") as f:
        json.dump(profile, f, indent=1)
    # Self-check: reconstruction of the latest preset vs measured.
    for c in CHUNKS:
        p = chunks[str(c)]["presets"]["week2"]["layers"]
        first = (sum(10 * v for v in p["global"]["first"].values()) + sum(50 * v for v in p["sliding"]["first"].values())) / 1e3
        print(f"chunk {c}: week2 first-chunk recon {first:.1f} ms vs measured {MEASURED['set3'][c][0]} ms")
    print("wrote", a.out)


if __name__ == "__main__":
    main()
