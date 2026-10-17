---
name: kernel-globals-trivial-init
description: "A tt-metal kernel global of a struct with member initializers fails JIT (dynamic initialization disallowed); kernel refactors are only checked on silicon, so canary them before a long queue"
metadata:
  type: feedback
---

2026-10-14: a /simplify cleanup (done by a subagent with no build) changed the ring_joint_sdpa compute kernel's `inline LaneTable table;` to hold `KVPadRotationContext` structs. Those have default member initializers, so the global needs dynamic initialization: `error: dynamic initialization or destruction of static-storage 'lanes::table' is disallowed in this environment` on trisc0/1/2. Every ring_joint_sdpa program failed (52/52 op tests), and with it every Gemma4 sliding layer; the queue burned 30 min before I saw it.

**Why:** kernels JIT at run start, so a host build that succeeds says nothing about kernel edits; refactors that look equivalent in C++ can be illegal in the kernel environment.

**How to apply:** kernel globals must be plain aggregates (no member initializers, no constructors). After any kernel-source edit (yours or an agent's), run a 2-minute canary (one op test that compiles the kernel) before queuing hours of device work. Related: [[kernel-source-edits-break-queued-runs]].
