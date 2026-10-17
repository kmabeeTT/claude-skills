---
name: agentx-workload-private-until-alina
description: "AgentX workload characterisation (2026-10-15) is kept in private debug-docs until Alina's independent run on tt-metal#60802 is compared; don't share or move to prefill-docs before that"
metadata:
  node_type: memory
  type: project
  originSessionId: 881cbbd5-38f9-4611-a392-1a19264327cc
  modified: 2026-10-15T19:07:17.239Z
---

The AgentX 256k workload characterisation (per-request table, percentiles, LRU hit-vs-capacity curve) lives in `~/debug-docs/gemma4_agentx_workload-60802/` (pushed to the private debug-docs repo on 2026-10-15). It was first committed to prefill-docs as 9bb5632, then backed out before it was pushed.

**Why:** Kyle had already given Alina (alinakhanTT) the same P0 task before this work. He filed tt-metal#60802 for it with the original scope only, so that her results are independent and can be checked against ours.

**How to apply:**
- Don't push it to prefill-docs, mention it on #60802 or #60408, or show it to the team until Kyle has seen Alina's branch and findings.
- After that, compare her numbers with ours item by item.

Data: `/data/kmabee/datasets/agentx/256k/agentx_256k_*`. Related: [[batching-agentx-prs-handoff-1014]].
