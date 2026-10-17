---
name: overnight-1015-state
description: 10-15 overnight done; read ~/debug-docs/gemma4_batching_poc-noissue/MORNING_BRIEF_1015.md first (hang re-dug, sim calibration patch, PR/issue game plan, decisions pending)
metadata:
  type: project
---

Overnight 2026-10-15 on bh-glx-120-c05u08 is finished. Start from ~/debug-docs/gemma4_batching_poc-noissue/MORNING_BRIEF_1015.md (TL;DR, reading order, opening order + who to tag, decisions for Kyle). Details: HANG_4K_LANES_1015.md (4k-lane hang = PR 2 lanes call at 4k + sync CCL, dispatch worker-count wait; NOT semaphores), SIM_ACCURACY_1015.md (proposed PR 4 calibration patch ~/runs_agentx/depth/pr4_component_calibration.patch, not applied), ISSUE_DRAFT_TRACE_HANG_4K_LANES.md.

Kyle 2026-10-15: sim recalibration went onto PR 4 (c6d02a1b9e3) + combined (9d688f75d80), #60408 numbers regenerated, prefill-docs pushed through c623b80. Workaround 9eebf4c535e is PR 5's tip (fast-forward) and on combined as a7a506cfce6 (Kyle OK 10-15); put the hang issue number in its comment once filed (issue draft ISSUE_DRAFT_TRACE_HANG_4K_LANES.md, file after PR 2, before PR 5). Nothing opened, no CI dispatched, PR 4 and PR 5 fast-forwarded only. Related: [[batching-agentx-prs-handoff-1014]], [[gemma4-batching-poc-traps]].

10-15 evening (Kyle OK): PR 4 force-pushed to the squashed, simplified sim with the tail fix `5b32659c548` (851 lines; srpt/--scale/--host-ms/agentx_sweep/compare removed, calibration built in); combined `5ea594f71b7` matches it. PR_DRAFT_AGENTX_SIM.md is that version's description (v1 kept as _V1). #60408 numbers now from sweeps/J_v2*.jsonl: ceilings FCFS 28.2k / pack 26.7k (1.65-1.75x 8k), pack heavy >16K p99 468 s. prefill-docs d3e89de, debug-docs 7956e0d.

10-16 (Kyle OK): filed umbrella #60861 and AgentX simulator #60862 (sub-issue of #60408, which stays open next to #60802; PR 4 closes #60862, not #60408). Both kmabeeTT, labels `model: gemma-4` + `perf`. Rows 1/2/3/5 of the umbrella and the d-gen end-to-end issue (ISSUE_DRAFT_AGENTX_DGEN_E2E.md, Asif; real prefill first, decode once tt-d-gen has KV migration) are not filed yet. The 4k hang is #60338, fix #60339 (#60817 closed as its duplicate). Design-doc `<link>` and draft file names are kept out of public text (Kyle: private).

10-16: PR 4 branch is now `136fd465ffc` (README expanded; was 14d7dabc506) (one commit: the simulator + fallback for configs without a silicon fit, marked `*`; README "Other configurations"); combined `9e30a1a2b26` has the same agentx_sim/. Still no PR opened.

10-16: filed #60866 (window-sized KV cache for the sliding layers; unassigned, @-invites Alina; sliding K/V is 435 of 462 KB per token, ~5-8 slots per Galaxy today vs ~60-90). Linked from #60861 follow-ups.

10-16: PR 4 opened as DRAFT #60867 (branch 78b14ff2583, title "gemma4_d_p: add a host-only AgentX simulator for prefill chunk designs"), Copilot review requested, #60861 row 4 links it. Follow-up comment posted (issuecomment-6207766642). Now a PR exists: no more force pushes on PR 4 without asking.

10-16: overview gist 0ada00b3 updated (commit 4f33167): combined 9e30a1a2b26, PR 4 draft #60867 @ 78b14ff2583, hang = #60338/#60339, #60866 cache capacity, stale `--calibrated` flag removed from the sim command.

10-16: combined rebuilt (force-push with lease, Kyle OK): tip 91fe18d0ed8 = main + 10 commits, PR 4 as one commit 09c82d74479, workaround 91fe18d0ed8 (was a7a506cfce6). Tree identical to old tip 9e30a1a2b26. Gist b8f7569.

10-16: filed #60869 (AgentX end to end through tt-d-gen on silicon; assignee mmanzoorTT, no cc) as a sub-issue of #60408. #60408 now has #60802, #60862, #60869.

10-16: #60408 reply POSTED (issuecomment-6208227661): concise, sub-issues #60802/#60862/#60869, metrics table, silicon line, cache capacity #60866, credits Alina and Andrew. prefill-docs a4f13a7 + posted-marker commit.

10-16: filed umbrella sub-issues #60871 (KV row window, PR1), #60872 (ring SDPA lanes, PR2), #60873 (step message, PR3), #60874 (continuous batching, PR5); kmabeeTT, roles not names. #60861 table + PR drafts updated. Next: open PR1/PR3 (rebase first), PR2 rebase + device re-test then draft, PR5 last.

10-16 overnight (c01u02, 75 W): every unopened branch rebased onto main f53ef8d99f1 and force-pushed (pr1 6181116ccc9, pr2 2a8c1675d40, pr3 a9268e8aaca, deps 79c10876101, pr5 7a84fb71ce7, combined 47a8bd99b4f). Re-test identical except traced batched KV for middle lanes, root-caused to the #60338 prefetcher race (fixed by #60339; PR 5 lands after it). Read debug-docs MORNING_BRIEF_1016.md first. Gist update prepared not pushed; #60339 comment drafted not posted.

10-16 evening (b08u02, 130 W): all unopened branches rebased onto main dbea30ec333 (has #60339), workaround dropped, re-measured; pushed (pr1 4ba11aaf801, pr2 75d6b96c252, pr3 f9e471f5ceb, deps 484bbf39487, pr5 fe47cd7f513, combined 423d0ad03ce). Gist ec7468d, umbrella edited. Log: debug-docs REBASE_1016B_B08U02.md. PR 4 review fixes 6f0ff80b6ce local, awaiting OK.

10-16 ~23:45: PR 4 review fixes pushed (`6f0ff80b6ce` on #60867; raw-array trace cache instead of pickle), 6 bot threads answered + resolved, combined now `2ca64ea590c`.

10-17: ack-loss hang = #58136 (D2H reader exact-count wait); PR 5 now has host acks for multi-lane steps (`59e69cb04ef`, TODO(#58136)); combined `ee2e03f6de5`; gist 3d78e35; umbrella follow-up added. Removal issue drafted (ISSUE_DRAFT_REMOVE_HOST_ACK_WORKAROUND.md), open after PR 5 merges.

10-17 ~04:35: stability campaign running detached: /data/kmabee/runs_stability_1017/ (queue.sh, SUMMARY); pass criteria in debug-docs REBASE_1016B_B08U02.md last section. After it: report, then PRs ready to open (order in PR_GUIDE_AND_INTERFACES.md section 6).

10-17 11:50: stability + standalone PR testing DONE, all green (failures pre-existing on main). Read debug-docs PR_READINESS_1017.md first; next = Kyle opens PRs, then fill PR numbers into #60861/gist. Worktrees wt-pr1-1017/wt-pr2-1017/wt-pr3-1017 (pr3 one is a scratch checkout).
