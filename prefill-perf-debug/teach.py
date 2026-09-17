#!/usr/bin/env python3
"""Teaching mode: at each level, the question, the prediction, the command, the result,
and WHY that comparison is valid - naming the assertion it honours.

The failures are the most instructive part, so they are surfaced rather than hidden.
Longer form, with the incidents, in METHOD.md.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import helpers as H

LESSONS = [
    {
        "level": 0,
        "title": "Which of the two cost terms is the problem?",
        "question": "Prefill time is N*a(C) + slope(C)*N(N-1)/2. Is the pain in `a` (paid once "
                    "per chunk, and therefore TTFT) or in `slope` (paid once per pair of "
                    "chunks, and therefore long-context throughput)?",
        "prediction": "Before running: write down which term you expect to dominate at the "
                      "context length you care about, and at what chunk size the other one "
                      "takes over. A fit that agrees with nothing you predicted is still data, "
                      "but you learn more from one that could have surprised you.",
        "command": "ppd.py run --what e2e --chunk C --ctx 32768 ... --launch   # once per chunk size\n"
                   "ppd.py level0 --log <log> --reference <C>",
        "result": "a/slope per chunk size, R^2, and the projection to your ISL split into the "
                  "two terms.",
        "why_valid": "The per-chunk device time is measured by the harness itself with no "
                     "profiler attached, so nothing here depends on Tracy being correct. t_i "
                     "is linear in i to R^2 >= 0.9996 on Gemma4, and the projection to 256k "
                     "lands within 1% of independent 256k runs - which is the check that the "
                     "model is the right shape, not just a good fit.",
        "assertions": ["A11 - the floor has two bases that differ by 4/3; both get printed, labelled"],
        "trap": "A slope fitted from ONE chunk is not a slope. level0 marks it UNVERIFIABLE "
                "and refuses to extrapolate. The published chunk-32768 slope on Gemma4 is "
                "exactly this case: it is not reproducible from any surviving log.",
    },
    {
        "level": 1,
        "title": "Which layers own each term?",
        "question": "A model is a stack of a few repeated layer types. Which type carries the "
                    "per-chunk floor, and which carries the growth with context?",
        "prediction": "A layer whose attention window is bounded CANNOT grow with context - its "
                      "slope should be indistinguishable from zero. Write that down first; it "
                      "is your control.",
        "command": "ppd.py level1 --curve <depth-curve.log> --level0-log <e2e.log>",
        "result": "a and slope per layer type, and the whole-model slope reconstructed as "
                  "sum(count * slope) - reconciled against level 0.",
        "why_valid": "Two independent measurements of the same quantity. The reconstruction "
                     "closes to 0.1-2.6% on Gemma4, which is what licenses saying 'the prefix "
                     "term IS the global layers' rather than 'the global layers are one "
                     "candidate'.",
        "assertions": ["A8 - the flat layer type is the control that makes the other one credible",
                       "A10 - the reconstruction must close against level 0; the residual is printed"],
        "trap": "Layer-count differencing is the other route and it is cleaner - no isolated-layer "
                "inflation, nothing missing from the graph. But on a model with no layer-count "
                "knob it needs a patch, so it is an ASSISTED path, not an automated one. Test "
                "linearity in N rather than assuming it: solve on two different pairs and "
                "compare.",
    },
    {
        "level": 2,
        "title": "Which ops inside those layers?",
        "question": "Within the layer that grows, what exactly is growing? And within the layer "
                    "that does not, what is the floor made of?",
        "prediction": "At MATCHED prior context, the prefix work is exactly proportional to the "
                      "chunk's token count. So a 4x smaller chunk does 0.25x the work. If the op "
                      "is efficiency-neutral it takes 0.25x the time; if it is occupancy-bound it "
                      "takes 0.50x. Write both numbers down BEFORE the capture. (Measured: 0.443x.)",
        "command": "ppd.py run --what capture --chunk C --chunk-idx I ... --launch   # depth 0 and depth D\n"
                   "ppd.py level2 --pairs pairs.json --level0-log <e2e.log>",
        "result": "per-op Device Time at both depths, the subtraction, the growth share, useful "
                  "occupancy, and the floor attributed three ways.",
        "why_valid": "The subtraction is between two captures of the SAME layer on the SAME "
                     "branch differing in one thing: prior context. And the chunk-size "
                     "comparison holds prior context fixed rather than chunk index, which is "
                     "what turns it from a comparison into a test with a predicted number.",
        "assertions": ["A9 - match prior context, not chunk index (idx 7 is 57k of history at "
                       "chunk 8192 and 14k at 2048)",
                       "A2 - Total % and Op-to-Op Gap are unusable here; Device Time only",
                       "A3 - Cores is grid size, not occupancy; compute occupancy from the op's "
                       "own work-unit math and print both",
                       "A4 - the utilization columns are empty; do not plan around them",
                       "A5 - never --device-trace-profiler",
                       "A10 - per-op sums overstate by ~13-15%; print the residual"],
        "trap": "The one comparison that CANNOT discriminate is 2048 vs 4096: both models predict "
                "0.5 there because both are depth-1. A valid test has to include the chunk size "
                "where the models disagree.",
    },
    {
        "level": 3,
        "title": "What is the expensive op bound by?",
        "question": "Bytes? Softmax? MAC throughput? Blocking? Something else?",
        "prediction": "One knob, one cost term, one prediction, each direction if the knob has "
                      "two. Halving the bytes should halve the time IF it is bandwidth-bound.",
        "command": "ppd.py level3 --list\nppd.py level3 --propose KNOB --run-dir <run>\n"
                   "ppd.py level3 --record-baseline <run>   # then patch, run, revert\n"
                   "ppd.py level3 --verify-revert <run>",
        "result": "a ratio per knob, each measured end to end on the whole model.",
        "why_valid": "Each ablation varies ONE cost term and holds the rest fixed. No FLOP "
                     "anchor, no spec-sheet bandwidth, no utilization column - none of which "
                     "can distinguish 'the math is slow' from 'the math is starved'.",
        "assertions": ["A1 - no 'bound by X' unless an ablation varied X",
                       "A7 - the prediction must pre-date the result",
                       "A8 - measure a control alongside",
                       "revert verification - snapshot the tree BEFORE the patch"],
        "trap": "Scope the conclusion to what the knob varied. Halving K/V dtype halves BYTES but "
                "not tile count, so 0.998x refutes byte-bandwidth bound - it says nothing about "
                "per-tile overhead. And do not fit a two-term model to an ablation that changed "
                "two things at once: that produced a '69% movement / 31% math' split that the "
                "next ablation contradicted.",
    },
]

FAILURES = [
    ("The false +21% regression (A6)",
     "A cross-branch check compared a value published in a writeup against a freshly rendered "
     "one and reported the op 21% slower. Re-rendering the SAME capture gave +1.9%. The "
     "per-device spread on that one op is 17% - larger than either delta. Re-render both "
     "sides from raw, with one tool, or report nothing."),
    ("The retracted fabric conclusion (A1)",
     "'The op runs at 47% of the same-layer matmul's per-core rate, so 53% is fabric.' A "
     "rate mismatch has many causes; here most of it was structural core idleness the same "
     "profiler could have shown. An anchor plus a residual is not a measurement of the "
     "residual."),
    ("Two numbers both called 'the floor' (A11)",
     "70 ms and 94 ms. The first is the excess over ideal token scaling, the second the "
     "chunk-invariant cost, and excess = 3/4 * F at a chunk ratio of 4. One was published "
     "as the other - a 33% error in the headline number."),
    ("A cost model extrapolated out of range (A11)",
     "a(C) is concave, not affine, so solving a 'fixed cost' by extrapolating to C = 0 gives "
     "a different answer for every pair you solve on - 39% apart for the matmul, and in one "
     "case a 'fixed' component larger than the op's entire measured cost at the small chunk. "
     "Use the in-range excess instead."),
    ("An unsupervised revert (level 3)",
     "A `git checkout` of one file silently dropped an `import os` a previous diagnostic "
     "patch had added. Three runs died with NameError before anyone noticed. Snapshot the "
     "tree before the patch and diff it after the revert."),
]


def render(level=None, profile=None):
    L = []
    for les in LESSONS:
        if level is not None and les["level"] != level:
            continue
        L += [f"{'=' * 78}", f"LEVEL {les['level']} - {les['title']}", "=" * 78, "",
              f"QUESTION\n  {_wrap(les['question'])}", "",
              f"PREDICTION (write this BEFORE running)\n  {_wrap(les['prediction'])}", "",
              "COMMAND"]
        L += [f"  {c}" for c in les["command"].split("\n")]
        L += ["", f"RESULT\n  {_wrap(les['result'])}", "",
              f"WHY THIS COMPARISON IS VALID\n  {_wrap(les['why_valid'])}", "",
              "ASSERTIONS IT HONOURS"]
        L += [f"  - {_wrap(a, 4)}" for a in les["assertions"]]
        L += ["", f"TRAP\n  {_wrap(les['trap'])}", ""]
    if level is None:
        L += ["=" * 78, "THE FAILURES WORTH KNOWING", "=" * 78, "",
              "These are not hypotheticals. Each one was published, then retracted.", ""]
        for title, body in FAILURES:
            L += [f"  {title}", f"    {_wrap(body, 4)}", ""]
        L += ["  The general lesson: every one came from comparing two things that differed",
              "  in more than one way. The assertions are ways of noticing that before you",
              "  publish. Full record in METHOD.md.", ""]
    return "\n".join(L)


def _wrap(text, indent=2, width=76):
    import textwrap
    return ("\n" + " " * indent).join(textwrap.wrap(text, width - indent))
