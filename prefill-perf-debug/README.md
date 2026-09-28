# prefill-perf-debug

A method for finding and landing chunked-prefill perf wins on TT multi-chip models without fooling yourself,
with accuracy (PCC) as the gate. Written from the Gemma4-31B work on BH Galaxy 8x4, Sept 2026.

- **Humans: read [RUNBOOK.md](RUNBOOK.md)** (start with its TL;DR).
- [tools/](tools/): queue helpers, floor/slope fit, per-layer PCC compare, power sampler, SDPA accumulation sims.
- [SKILL.md](SKILL.md): a thin Claude Code skill that makes Claude read the runbook and hold to its gates.

To use the skill without the rest of this repo, copy this directory to `~/.claude/skills/prefill-perf-debug/`.

v1 (an automated level 0-3 funnel CLI, `ppd.py` and friends) was retired in favor of the runbook; it is in git
history at 734c314.
