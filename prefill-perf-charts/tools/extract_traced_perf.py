#!/usr/bin/env python3
"""Extract per-chunk [traced_perf] lines from prefill perf logs into one tidy CSV.

Usage:
  extract_traced_perf.py --src LABEL=DIR [--src LABEL=DIR ...] --out per_chunk.csv

Every *.log under DIR (recursive) that has [traced_perf] chunk lines is read. A row is the
log's directory relative to DIR ("R1_57453", "breakdown/p6_abc"), so one folder per build.
A chunk size starting again at chunk 1 begins a new pass; passes are numbered per
(source, row, chunk_size) across that row's logs in filename order, which is chronological
for timestamped names.

Columns: source,row,log,pass,chunk_size,chunk_idx,n_chunks,start_tok,end_tok,device_ms,
cum_device_ms,wall_s. cum_device_ms is the running sum of per-chunk device ms, because
some log formats print the running total rounded to 0.1 s. wall_s is the log's own
running wall total.

Line format matched (gemma4_d_p text_demo_prefill, both the per-chunk-size test and the sweep):
  [traced_perf] chunk 3/32 [16384, 24576) device=132.0ms (62066 tok/s) | total device=370.0ms wall=376.4ms
"""
import argparse, csv, re, sys
from pathlib import Path

LINE = re.compile(r"\[traced_perf\] chunk (\d+)/(\d+) \[(\d+), (\d+)\) device=([\d.]+)(ms|s)\b.*?wall=([\d.]+)(ms|s)\b")
FIELDS = ["source", "row", "log", "pass", "chunk_size", "chunk_idx", "n_chunks", "start_tok",
          "end_tok", "device_ms", "cum_device_ms", "wall_s"]


def ms(v, unit):
    return float(v) * (1000.0 if unit == "s" else 1.0)


def parse(path, source, row, passes):
    # chunk 1 of a pass fixes its chunk size; later chunks (including a short last one)
    # belong to the pass with the same chunk count
    size_for_n, cum, out = {}, {}, []
    for line in path.read_text(errors="replace").splitlines():
        m = LINE.search(line)
        if not m:
            continue
        idx, n, s, e = (int(x) for x in m.group(1, 2, 3, 4))
        if idx == 1:
            size_for_n[n] = e - s
            key = (source, row, e - s)
            passes[key] = passes.get(key, 0) + 1
            cum[n] = 0.0
        if n not in size_for_n:
            print(f"warn: {path}: chunk {idx}/{n} without a chunk 1, skipped", file=sys.stderr)
            continue
        cs = size_for_n[n]
        cum[n] += ms(m.group(5), m.group(6))
        out.append(dict(source=source, row=row, log=path.name, **{"pass": passes[(source, row, cs)]},
                        chunk_size=cs, chunk_idx=idx, n_chunks=n, start_tok=s, end_tok=e,
                        device_ms=round(ms(m.group(5), m.group(6)), 3), cum_device_ms=round(cum[n], 3),
                        wall_s=round(ms(m.group(7), m.group(8)) / 1000.0, 4)))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", action="append", required=True, metavar="LABEL=DIR")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    recs, passes = [], {}
    for spec in a.src:
        label, _, d = spec.partition("=")
        root = Path(d)
        if not root.is_dir():
            sys.exit(f"--src {spec}: not a directory")
        for p in sorted(root.rglob("*.log")):
            row = str(p.parent.relative_to(root)) or "."
            recs += parse(p, label, row, passes)
    if not recs:
        sys.exit("no [traced_perf] chunk lines found")
    with open(a.out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(recs)
    # one summary line per run so the caller can match rows to milestones
    runs = {}
    for r in recs:
        k = (r["source"], r["row"], r["chunk_size"], r["pass"])
        runs.setdefault(k, []).append(r)
    print(f"wrote {len(recs)} rows -> {a.out}\n")
    print("source  row  chunk  pass  chunks  first_ms  max_ctx  cum_device_s")
    for k, v in sorted(runs.items()):
        print(*k, f"{len(v)}/{v[0]['n_chunks']}", v[0]["device_ms"], v[-1]["end_tok"],
              f"{v[-1]['cum_device_ms'] / 1000:.2f}", sep="  ")


if __name__ == "__main__":
    main()
