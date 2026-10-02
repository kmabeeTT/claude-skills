---
name: allcaps-names-for-reference-docs
description: "kmabee wants ALL_CAPS filenames for docs he refers to often (OPTIMIZATION_LEADS.md), not the snake_case used for one-off writeups"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 61e9cb32-a815-42b5-b7e2-d459066fef96
  modified: 2026-09-07T20:31:34.116Z
---

Docs kmabee expects to **refer back to often** get **ALL_CAPS** filenames — e.g.
`~/debug-docs/OPTIMIZATION_LEADS.md`. This is distinct from the snake_case convention in
`~/debug-docs/CLAUDE.md`, which applies to one-off investigation writeups
(`vllm_sampling_graph_comparison.md`) and archive folders (`<slug>-<issue>/`).

Read it as a two-tier scheme: **ALL_CAPS = living/working doc you open repeatedly**;
snake_case = a record of something that happened.

**Why:** the caps make the handful of active working docs jump out in `ls` against dozens of
archived writeups. I first named this one `gemma4_optimization_leads.md` to follow the repo's
documented snake_case rule and had to be corrected — the repo convention does not override this
preference for working docs.

**How to apply:** when creating a doc meant to be a recurring reference (a backlog, a runbook, a
tracker), use ALL_CAPS even if the surrounding repo is snake_case. Don't prefix it with the
project name unless asked — he named `OPTIMIZATION_LEADS.md` bare. Keep using snake_case for
investigation records.
