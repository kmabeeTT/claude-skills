#!/usr/bin/env python3
"""Build the Mistral Small 4 (BH Galaxy 8x4, single rank SP=8 x TP=4, chunk 5120) what-if profile JSON.

Input: harness/perf_vs_target/perf_vs_target_m4.json in the mistral4 perf_understand folder (made by
compute.py from the layer-profile captures). It holds per-op times and work (GFLOP, MB, roofline floor,
reference time) for baseline and asif_alina x layer 0 / layer 18 x chunk 1 / chunk 50, captured on
bh-glx-110-d07u02 (RevC, 130 W) on 2026-10-07.

Reconstruction follows target.py there: layer 0 (first rank, embeds) + 35 x layer 18 (representative),
linear in chunk index between the chunk-1 and chunk-50 captures, plus an explicit bucket for the time
outside the layers (measured per-chunk time minus the layers).

Usage: build_mistral4_profile.py [--docs DIR] --out profile.json
"""
import argparse
import json
import math
import os

VARIANTS = {"baseline": "baseline", "asif_alina": "asif_alina"}
LAYERS = 36
CHUNK = 5120
N_CHUNKS = 51
LAYOUT_OPS = ("Typecast", "Slice", "Concat", "Tilize", "Sharded", "Reshape", "Permute")
MOE_MOVE_OPS = ("Dispatch", "Combine")

# Whole-model measurements, same box and session as the captures (target.py MEAS / PER_CHUNK_MEAS).
MEAS = {
    "asif_alina": dict(first=136.9, w100=3.74, t256=13.77, sha="6fd8974f5c9"),
    "baseline": dict(first=157.2, w100=4.20, t256=15.64, sha="3c93c8b7c8b"),
}
PER_CHUNK_MEAS = {"asif_alina": {1: 141.9, 50: 404.4}, "baseline": {1: 163.0, 50: 464.8}}


def comp_of(o):
    """Map one captured op to a page component id."""
    c = o["cat"]
    if c == "moe":
        return "moe_move" if any(o["op"].startswith(k) for k in MOE_MOVE_OPS) else "moe_ffn"
    if c in ("small", "norm"):
        return "small"
    return {"sdpa": "sdpa", "matmul": "matmul", "collectives": "coll"}[c]


def fid_of(o):
    f = o.get("fid")
    if not isinstance(f, str):
        return None
    f = f.split()[0].rstrip(",")
    return f if f in ("LoFi", "HiFi2", "HiFi3", "HiFi4") else "HiFi4"


def is_nan(x):
    return isinstance(x, float) and math.isnan(x)


def main():
    ap = argparse.ArgumentParser()
    default_docs = next((d for d in (os.path.expanduser("~/prefill-docs/mistral4/perf_understand"),
                                      "/data/kmabee/prefill-docs-staging/mistral4/perf_understand") if os.path.isdir(d)), None)
    ap.add_argument("--docs", default=default_docs)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    R = json.load(open(os.path.join(a.docs, "harness/perf_vs_target/perf_vs_target_m4.json")))

    def comp_times(variant, layer, idx):
        out = {}
        for o in R[f"{variant}|L{layer}|c{idx}"]["ops"]:
            cid = comp_of(o)
            out[cid] = out.get(cid, 0.0) + o["t_us"]
        return out

    def layers_sum(variant, idx):
        return sum(comp_times(variant, 0, idx).values()) + (LAYERS - 1) * sum(comp_times(variant, 18, idx).values())

    presets = {}
    for v in VARIANTS:
        layers = {}
        for lid, cap in (("L0", 0), ("L18", 18)):
            layers[lid] = {"first": comp_times(v, cap, 1), "depth": comp_times(v, cap, 50)}
        layers["host"] = {pos: {"host": PER_CHUNK_MEAS[v][idx] * 1e3 - layers_sum(v, idx)} for pos, idx in (("first", 1), ("depth", 50))}
        m = MEAS[v]
        presets[v] = {"layers": layers, "measured": {"first_ms": m["first"], "mid_s": m["w100"], "full_s": m["t256"]}}

    # what-if inputs from the base variant's captures (asif_alina); chunk-50 ops for the per-op work
    base = "asif_alina"
    work = {}
    for lid, cap in (("L0", 0), ("L18", 18)):
        w = {"matmul": {"ops": []}, "moe_move": {"ops": []}, "moe_ffn": {"ops": []}, "coll": {"ref_us": 0.0}, "small": {"target_us": 0.0}}
        for o in R[f"{base}|L{cap}|c50"]["ops"]:
            cid = comp_of(o)
            if cid == "matmul":
                w["matmul"]["ops"].append({"name": f"{o.get('M')}x{o.get('K')}x{o.get('N')}", "gflop": o["gflop"], "fid": fid_of(o),
                                           "mb": o["mbytes"], "bw": "dram", "t_us": o["t_us"]})
            elif cid == "moe_move" and "mbytes" in o:
                w["moe_move"]["ops"].append({"name": o["op"], "mb": o["mbytes"], "bw": "fabric", "t_us": o["t_us"]})
            elif cid == "moe_ffn" and o.get("gflop"):
                w["moe_ffn"]["ops"].append({"name": o["op"], "gflop": o["gflop"], "fid": fid_of(o), "t_us": o["t_us"]})
            elif cid == "coll":
                w["coll"]["ref_us"] += o.get("ref_us", o["t_us"])
            elif cid == "small":
                if not any(k in o["op"] for k in LAYOUT_OPS):
                    w["small"]["target_us"] += o["t_us"]
        w["sdpa"] = {"gflop_first": sum(o["gflop"] for o in R[f"{base}|L{cap}|c1"]["ops"] if o["cat"] == "sdpa"),
                     "gflop_depth": sum(o["gflop"] for o in R[f"{base}|L{cap}|c50"]["ops"] if o["cat"] == "sdpa")}
        work[lid] = w
    # outside the layers: no gain claimed (mechanism unidentified), so the target is today's value
    work["host"] = {"host": {"target_us": presets[base]["layers"]["host"]["first"]["host"]}}

    profile = {
        "schema": 2,
        "title": "Mistral4 Prefill What-If",
        "model": "Mistral-Small-4-119B chunked prefill (absorbed MLA, 128-expert MoE)",
        "hardware": "BH Galaxy 8x4, single rank SP=8 x TP=4, chunk 5,120; measured on bh-glx-110-d07u02 (RevC, 130 W)",
        "layer_types": [
            {"id": "L0", "label": "Layer 0 (first rank, embeds)", "count": 1},
            {"id": "L18", "label": "Layers 1-35 (layer 18 captured)", "count": LAYERS - 1},
            {"id": "host", "label": "Outside the layers", "count": 1},
        ],
        "components": [
            {"id": "sdpa", "label": "SDPA (ring MLA)", "model": "sdpa_rate", "peak": "sdpa_lofi", "color": "--c-gsdpa"},
            {"id": "moe_move", "label": "MoE dispatch + combine", "model": "roofline", "color": "--c-lsdpa",
             "hint": "Roofline = fabric bytes at 50 GB/s"},
            {"id": "moe_ffn", "label": "MoE expert FFN + routing", "model": "roofline", "color": "--c-extra2",
             "hint": "Expert FFN is modelled; routing ops stay at today's"},
            {"id": "coll", "label": "Collectives", "model": "ref_ratio", "color": "--c-coll"},
            {"id": "matmul", "label": "Matmuls (MLA)", "model": "roofline", "color": "--c-matmul"},
            {"id": "small", "label": "Norms + small ops", "model": "scale", "color": "--c-small", "hint": "Target removes layout-only ops"},
            {"id": "host", "label": "Outside the layers", "model": "scale", "color": "--c-host",
             "hint": "Measured per-chunk time minus the layers; mechanism not identified"},
        ],
        # TFLOP/s at 1.35 GHz. Matmuls and the expert FFN: 120 cores. Ring SDPA: 110 compute cores, LoFi.
        "peaks": {"LoFi": 663.6, "HiFi2": 331.8, "HiFi3": 221.2, "HiFi4": 165.9, "sdpa_lofi": 608.3, "sdpa_hifi2": 304.1},
        "dram_options": [{"label": "RevC 512 GB/s", "gbs": 512}, {"label": "RevB 384 GB/s", "gbs": 384}],
        "fabric_gbs": 50,
        "target_presets": [
            {"label": "Target: 70% util", "values": {"sdpa": {"util": 70, "fixed": 0}, "moe_move": {"util": 70}, "moe_ffn": {"util": 70},
                                                      "matmul": {"util": 70}, "coll": {"eff": 100}, "small": {"pct": "target"}, "host": {"pct": 100}}},
        ],
        "presets": [
            {"id": "baseline", "label": "Baseline", "desc": "PR #56307 Mistral4 pipeline prefill (3c93c8b7c8b) on main a30a6a1b15d.",
             "measured_note": "Measured on bh-glx-110-d07u02 (RevC, 130 W), same session as the captures. 256k = 261,120 tokens, one chunk extrapolated."},
            {"id": "asif_alina", "label": "+ Asif + Alina", "desc": "Baseline + Asif's MLA / norm / MoE-op tuning + Alina's LoFi ring SDPA matmuls, 8256 B fabric packets, padding-aware gate (6fd8974f5c9).",
             "measured_note": "Measured on bh-glx-110-d07u02 (RevC, 130 W), same session as the captures. 256k = 261,120 tokens, one chunk extrapolated."},
        ],
        "whatif_base": base,
        "chunks": {str(CHUNK): {
            # captures are 0-based chunks 1 and 50 (KV 10,240 and 261,120) = 1-based chunks 2 and 51
            "first_index": 2,
            "depth_index": 51,
            "checkpoints": [
                {"label": "TTFT (1 chunk)", "tokens": CHUNK, "measured_key": "first_ms", "unit": "ms"},
                {"label": "100k", "tokens": 102400, "measured_key": "mid_s", "unit": "s"},
                {"label": "256k", "tokens": N_CHUNKS * CHUNK, "measured_key": "full_s", "unit": "s"},
            ],
            "presets": presets,
            "work": work,
        }},
        "notes": [
            "Reconstructed from per-layer captures: layer 0 + 35 x layer 18, at chunk 1 (KV 10,240) and chunk 50 (KV 261,120), linear in chunk index between them, plus the time outside the layers. It lands within ~1.5% of measured, partly by construction: the outside-the-layers bucket is measured per-chunk time minus the layers.",
            "Captures and whole-model numbers: bh-glx-110-d07u02, RevC (512 GB/s DRAM), 130 W, 2026-10-07. Sustained clock ~1.28-1.30 GHz; percentages assume 1.35 GHz.",
            "Roofline util is the slower of compute at the op's fidelity (120 cores, 1.35 GHz) and bytes over the bandwidth: DRAM for the MLA matmuls, fabric (50 GB/s) for MoE dispatch and combine. MoE routing ops and other unmodelled ops stay at today's time.",
            "SDPA util is % of the ring SDPA's LoFi peak on 110 cores, applied to the absorbed-MLA FLOPs (QK width 320, PV width 256) on one device. Baseline ran SDPA at HiFi2; the what-if starts from Asif + Alina (LoFi).",
            "Collectives: % of the in-tree Galaxy reference for the same bytes. The ReduceScatter after the MoE combine runs ~10x its reference; much of that is waiting for slower peers, not the collective itself.",
            "Outside the layers: host staging, trace replay and MoE sub-device swaps (~53 ms per chunk at depth in the baseline, ~11 ms in Asif + Alina). The 70% target claims no gain there.",
        ],
        "sources": "prefill-docs mistral4/perf_understand: PERF_VS_TARGET_MISTRAL4.md, README.md section 4b, harness/perf_vs_target/ (target.py, perf_vs_target_m4.json)",
    }
    with open(a.out, "w") as f:
        json.dump(profile, f, indent=1)

    # Self-check against target.py's reconstruction (first ms / 256k s).
    for v in VARIANTS:
        L = presets[v]["layers"]

        def chunk(k):
            t = 0.0
            for lid, n in (("L0", 1), ("L18", LAYERS - 1), ("host", 1)):
                f, d = sum(L[lid]["first"].values()), sum(L[lid]["depth"].values())
                t += n * (f + (d - f) * (k - 2) / 49)
            return t
        pcs = [chunk(k) for k in range(1, N_CHUNKS + 1)]
        print(f"{v}: recon first {pcs[0]/1e3:.1f} ms, 100k {sum(pcs[:20])/1e6:.2f} s, 256k {sum(pcs)/1e6:.2f} s"
              f" | measured {MEAS[v]['first']} / {MEAS[v]['w100']} / {MEAS[v]['t256']}")
    print("wrote", a.out)


if __name__ == "__main__":
    main()
