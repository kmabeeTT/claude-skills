#!/usr/bin/env python3
"""Plot prefill time-to-context curves from per_chunk.csv, driven by a JSON config.

Usage:
  plot_prefill_curves.py --csv per_chunk.csv --config charts.json --out OUT_DIR [--only FILE ...]

Writes the PNGs the config lists, plus:
  plotted_series.csv  every point that was plotted, with its source run
  stats.md            per milestone and chunk size: first chunk, cumulative time at checkpoints,
                      and a linear fit of per-chunk time = fixed + slope * prefix. Paste from it
                      into the README instead of retyping numbers.

Config (see examples/gemma4_journey_1006.json):
  subtitle      one line under every title (model, hardware, metric)
  chunks        chunk sizes to draw, in colour order (first three are the validated slots)
  checkpoints_k context points for stats.md, in k tokens (1k = 1024)
  milestones    key -> {name, style: solid|dashed|dotted|dashdot,
                        runs: {chunk: [source, row] or [source, row, pass]}, note?}
                A milestone may omit chunk sizes it has no run for.
  charts        list of {type, file, title, ...}:
                  by_chunk         one milestone, every chunk size        (milestone)
                  compare          several milestones, every chunk size   (milestones)
                  per_chunk        like compare, y = this chunk's time    (milestones)
                  small_multiples  one panel per chunk size               (milestones)
                Optional per chart: subtitle (overrides), note (appended to the subtitle).

Colour = chunk size, line style = milestone, final value labelled at each line's end.
Charts in one config share a y range so they compare by eye.
"""
import argparse, csv, json, sys
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

SURF, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
# categorical slots in fixed order; slots 1-3 pass the all-pairs CVD check on the light surface
SLOTS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]
STYLES = {"solid": "solid", "dashed": (0, (6, 3)), "dotted": (0, (2, 2)), "dashdot": (0, (6, 2, 1.5, 2))}


def chunk_label(c):
    return f"{c // 1024}k chunk" if c % 1024 == 0 else f"{c} chunk"


def k_label(k):
    return "0" if k == 0 else f"{k:g}k"


class Data:
    def __init__(self, csv_path, cfg):
        self.cfg = cfg
        self.runs = defaultdict(list)
        for r in csv.DictReader(open(csv_path)):
            self.runs[(r["source"], r["row"], int(r["chunk_size"]), int(r["pass"]))].append(r)
        self.chunks = [int(c) for c in cfg["chunks"]]
        self.color = {c: SLOTS[i] for i, c in enumerate(self.chunks)}
        if len(self.chunks) > 3:
            print("warn: more than 3 chunk sizes; slots 4+ are not CVD-safe as a set, keep the end labels",
                  file=sys.stderr)
        self.series = {}
        for key, ms in cfg["milestones"].items():
            for c, run in ms["runs"].items():
                src, row, *p = run
                rows = self.runs.get((src, row, int(c), p[0] if p else 1))
                if not rows:
                    sys.exit(f"milestone {key}: no run {src}/{row} chunk {c} pass {p[0] if p else 1} in the CSV")
                if rows[-1]["chunk_idx"] != rows[-1]["n_chunks"]:
                    print(f"warn: {key} chunk {c}: run stops at chunk {rows[-1]['chunk_idx']}/{rows[-1]['n_chunks']}",
                          file=sys.stderr)
                self.series[(key, int(c))] = dict(
                    x=[int(r["end_tok"]) / 1024 for r in rows],
                    prefix=[int(r["start_tok"]) / 1024 for r in rows],
                    cum=[float(r["cum_device_ms"]) / 1000 for r in rows],
                    dev=[float(r["device_ms"]) for r in rows],
                    src=(src, row, p[0] if p else 1))
        self.xmax = max(s["x"][-1] for s in self.series.values())
        self.ymax = max(s["cum"][-1] for s in self.series.values()) * 1.06

    def get(self, ms, c):
        return self.series.get((ms, c))


def xticks(xmax):
    step = next(s for s in (1, 2, 4, 8, 16, 32, 64, 128, 256) if xmax / s <= 9)
    return [i * step for i in range(int(xmax // step) + 1)]


def style_ax(ax, d, ylabel, ticks=None):
    ax.set_facecolor(SURF)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.tick_params(colors=INK2, labelsize=10)
    ax.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    t = ticks or xticks(d.xmax)
    ax.set_xlim(0, d.xmax * 1.02)
    ax.set_xticks(t)
    ax.set_xticklabels([k_label(v) for v in t])
    ax.set_xlabel("Context length (tokens)", color=INK2, fontsize=11)
    ax.set_ylabel(ylabel, color=INK2, fontsize=11)


def end_labels(ax, d, items, gap_frac=0.045):
    """items: (y_end, text). Stacks labels upward so none collide; a leader line marks a moved one."""
    lo, hi = ax.get_ylim()
    gap, x0, placed = (hi - lo) * gap_frac, d.xmax, []
    for y, t in sorted(items):
        yy = max(y, placed[-1] + gap) if placed else y
        placed.append(yy)
        ax.annotate(t, xy=(x0, y), xytext=(x0 * 1.035, yy), textcoords="data", va="center", fontsize=9.5,
                    color=INK, annotation_clip=False,
                    arrowprops=dict(arrowstyle="-", color=GRID, lw=0.8) if yy != y else None)


def header(fig, title, subs, x=0.07, step=0.035):
    """Title plus one line per subtitle entry; returns how far the plot top must drop."""
    fig.text(x, 0.955, title, fontsize=15, weight="bold", color=INK, ha="left")
    for i, sub in enumerate(subs):
        fig.text(x, 0.915 - step * i, sub, fontsize=10, color=INK2, ha="left")
    return step * (len(subs) - 1)


def subtitle(cfg, ch):
    """The chart's subtitle and, on its own line, its note (a note on the same line runs off the edge)."""
    return [ch.get("subtitle", cfg["subtitle"])] + ([ch["note"]] if ch.get("note") else [])


def fig_ax():
    fig, ax = plt.subplots(figsize=(10, 6), dpi=150)
    fig.patch.set_facecolor(SURF)
    return fig, ax


def chart_by_chunk(d, ch, out):
    ms = ch["milestone"]
    fig, ax = fig_ax()
    style_ax(ax, d, "Cumulative device time (s)")
    ax.set_ylim(0, d.ymax)
    labs = []
    for c in d.chunks:
        s = d.get(ms, c)
        if not s:
            continue
        ax.plot(s["x"], s["cum"], color=d.color[c], lw=2, label=chunk_label(c))
        labs.append((s["cum"][-1], f"{chunk_label(c)}: {s['cum'][-1]:.2f} s"))
    end_labels(ax, d, labs)
    ax.legend(frameon=False, loc="upper left", fontsize=10, labelcolor=INK)
    drop = header(fig, ch["title"], subtitle(d.cfg, ch))
    fig.subplots_adjust(left=0.07, right=0.84, top=0.87 - drop, bottom=0.1)
    fig.savefig(out, facecolor=SURF)
    plt.close(fig)


def chart_compare(d, ch, out, per_chunk=False):
    mss = ch["milestones"]
    fig, ax = fig_ax()
    style_ax(ax, d, "Device time for this chunk (ms)" if per_chunk else "Cumulative device time (s)")
    labs, ys = [], []
    for ms in mss:
        for c in d.chunks:
            s = d.get(ms, c)
            if not s:
                continue
            y = s["dev"] if per_chunk else s["cum"]
            ys.append(max(y))
            ax.plot(s["x"], y, color=d.color[c], lw=2, linestyle=STYLES[d.cfg["milestones"][ms]["style"]])
            v = f"{y[-1]:.0f} ms" if per_chunk else f"{y[-1]:.2f} s"
            labs.append((y[-1], f"{chunk_label(c).split()[0]} {d.cfg['milestones'][ms].get('short', ms)}: {v}"))
    ax.set_ylim(0, max(ys) * 1.08 if per_chunk else d.ymax)
    end_labels(ax, d, labs)
    hs = [Line2D([], [], color=d.color[c], lw=2) for c in d.chunks] + \
         [Line2D([], [], color=INK2, lw=2, linestyle=STYLES[d.cfg["milestones"][m]["style"]]) for m in mss]
    ax.legend(hs, [chunk_label(c) for c in d.chunks] + [d.cfg["milestones"][m]["name"] for m in mss],
              frameon=False, loc="upper left", fontsize=9.5, labelcolor=INK, handlelength=3.5)
    drop = header(fig, ch["title"], subtitle(d.cfg, ch), x=0.08)
    fig.subplots_adjust(left=0.08, right=0.79, top=0.87 - drop, bottom=0.1)
    fig.savefig(out, facecolor=SURF)
    plt.close(fig)


def chart_small_multiples(d, ch, out):
    mss = ch["milestones"]
    n = len(d.chunks)
    fig, axes = plt.subplots(1, n, figsize=(5 * n, 5.2), dpi=150, sharey=True, squeeze=False)
    fig.patch.set_facecolor(SURF)
    t = [v for v in xticks(d.xmax)][::2] or None
    for ax, c in zip(axes[0], d.chunks):
        style_ax(ax, d, "Cumulative device time (s)" if c == d.chunks[0] else "", ticks=t)
        ax.set_ylim(0, d.ymax)
        ends = []
        for ms in mss:
            s = d.get(ms, c)
            if not s:
                continue
            ax.plot(s["x"], s["cum"], color=d.color[c], lw=2, linestyle=STYLES[d.cfg["milestones"][ms]["style"]])
            ends.append(s["cum"][-1])
        placed = []
        for y in sorted(ends):
            yy = max(y, placed[-1] + d.ymax * 0.05) if placed else y
            placed.append(yy)
            ax.annotate(f"{y:.2f} s", xy=(d.xmax, y), xytext=(d.xmax * 1.03, yy), textcoords="data",
                        va="center", fontsize=9, color=INK, annotation_clip=False)
        ax.set_title(chunk_label(c), color=INK, fontsize=12, loc="left", weight="bold")
    fig.legend([Line2D([], [], color=INK2, lw=2, linestyle=STYLES[d.cfg["milestones"][m]["style"]]) for m in mss],
               [d.cfg["milestones"][m]["name"] for m in mss], frameon=False, loc="lower center",
               ncol=len(mss), fontsize=10, labelcolor=INK, handlelength=4)
    drop = header(fig, ch["title"], subtitle(d.cfg, ch), x=0.05, step=0.04)
    fig.subplots_adjust(left=0.05, right=0.96, top=0.83 - drop, bottom=0.2, wspace=0.16)
    fig.savefig(out, facecolor=SURF)
    plt.close(fig)


def linfit(xs, ys):
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx if sxx else 0.0
    a = my - b * mx
    return a, b, max(abs(y - (a + b * x)) for x, y in zip(xs, ys))


def write_stats(d, out_dir):
    cps = d.cfg.get("checkpoints_k", [32, 64, 128, 256])
    lines = [f"# Stats (cumulative device time, s; checkpoints {', '.join(k_label(k) for k in cps)})", ""]
    lines.append("## Cumulative time at checkpoints")
    for c in d.chunks:
        parts = []
        for ms in d.cfg["milestones"]:
            s = d.get(ms, c)
            if not s:
                continue
            vals = [next((y for x, y in zip(s["x"], s["cum"]) if x >= k), None) for k in cps]
            parts.append(f"{d.cfg['milestones'][ms].get('short', ms)} " +
                         " / ".join("—" if v is None else f"{v:.2f}" for v in vals))
        lines.append(f"- {chunk_label(c)}: " + ", ".join(parts))
    lines += ["", "## First chunk (ms) and fit: per-chunk ms = fixed + slope x prefix (ms per 1k tokens)"]
    for c in d.chunks:
        parts = []
        for ms in d.cfg["milestones"]:
            s = d.get(ms, c)
            if not s:
                continue
            a, b, res = linfit(s["prefix"], s["dev"])
            parts.append(f"{d.cfg['milestones'][ms].get('short', ms)} first {s['dev'][0]:.1f}, "
                         f"fit {a:.1f} + {b:.3f} (max resid {res:.1f})")
        lines.append(f"- {chunk_label(c)}: " + "; ".join(parts))
    lines += ["", "## Sources", ""]
    for (ms, c), s in sorted(d.series.items(), key=lambda kv: (list(d.cfg["milestones"]).index(kv[0][0]), kv[0][1])):
        lines.append(f"- {ms} {chunk_label(c)}: {s['src'][0]}/{s['src'][1]} pass {s['src'][2]}, "
                     f"{len(s['x'])} chunks to {s['x'][-1]:g}k")
    (out_dir / "stats.md").write_text("\n".join(lines) + "\n")
    with open(out_dir / "plotted_series.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["milestone", "chunk_size", "source", "row", "pass", "context_k_tokens", "chunk_device_ms",
                    "cum_device_s"])
        for (ms, c), s in d.series.items():
            for x, dv, y in zip(s["x"], s["dev"], s["cum"]):
                w.writerow([ms, c, *s["src"], x, dv, round(y, 4)])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", required=True)
    ap.add_argument("--config", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--only", nargs="*", help="render only these chart files")
    a = ap.parse_args()
    cfg = json.load(open(a.config))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    d = Data(a.csv, cfg)
    fns = {"by_chunk": chart_by_chunk, "compare": chart_compare, "small_multiples": chart_small_multiples,
           "per_chunk": lambda d, ch, o: chart_compare(d, ch, o, per_chunk=True)}
    for ch in cfg["charts"]:
        if a.only and ch["file"] not in a.only:
            continue
        fns[ch["type"]](d, ch, out / ch["file"])
        print("wrote", out / ch["file"])
    write_stats(d, out)
    print("wrote", out / "stats.md", "and", out / "plotted_series.csv")


if __name__ == "__main__":
    main()
