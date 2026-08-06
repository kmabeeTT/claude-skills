---
name: debug-archive
description: This skill should be used when the user asks to "archive this debug session", "save debug context", "save this investigation", "write this up to debug-docs", "capture this session", or after a substantial debugging session that produced issues, PRs, branches, gists, or debug MD files worth preserving for future reference.
version: 1.0.0
---

# Debug Archive Skill

Preserve a debugging session in `~/debug-docs/` as a self-contained, per-investigation folder
so it can be found and trusted months later.

The goal is that a future reader (often the same person, with no memory of the session) can
answer in under a minute: *what broke, what was the answer, where are the tickets, where did it
run, and what should I not re-try.*

## Where things go

- Archive repo: `~/debug-docs/` (git, branch `main`)
- One folder per investigation: `~/debug-docs/<slug>-<issue-number>/`
  - `<slug>` = short snake_case topic, `<issue-number>` = primary tt-xla issue (or `noissue`)
  - e.g. `paged_fill_cache_128k_hang-5897/`, `kv_cache_bleed-4471/`
- Older docs in this repo live flat in the root. Do **not** move them; new investigations use
  folders. Both are linked from the root `README.md`.

## Folder contents

| File | Required | What it is |
|---|---|---|
| `README.md` | yes | The landing page — summary, links table, environment, timeline. Template below. |
| `<topic>_debug.md` | yes | The detailed working record (evidence, tables, dead ends). Usually an existing debug MD copied in. |
| `issue_*.md` / `comment_*.md` | if any | The exact text filed to GitHub, so the archive survives issue edits. |
| `repro_*.py` / `*.sh` | if any | Repro scripts or harnesses produced during the session. |
| `logs/` | optional | Only small, decisive excerpts. Never multi-MB run logs — link a gist instead. |

## Workflow

1. **Gather facts — do not guess.** Run these and use the real values:
   ```bash
   hostname                                   # machine the session ran on
   whoami
   tt-smi -ls 2>/dev/null | grep -oE "p[0-9]+[a-z]*" | sort -u | tr '\n' ' '   # board type
   nproc; free -g | awk 'NR==2{print $2" GiB RAM"}'
   git -C <repo> rev-parse --short HEAD       # commit(s) under test
   ```
   For each repo involved (tt-xla, tt-mlir, tt-metal) record the commit actually used.

   Also record the **Claude Code session name** (the `/rename` title, or ask the user for it)
   and the working directory. `hostname` may return a container id — if the user's shell prompt
   shows a different real host, record both.

2. **Collect the links.** Issues, PRs, branches, gists. Use `gh issue view <n> --json title,state`
   to get real titles/state rather than reciting from memory. Note whether gists are secret.

3. **Create the folder** and copy in the debug MD(s), issue/comment text, and scripts.
   Copy, do not move — leave the working tree intact.

4. **Write `README.md`** from the template below.

5. **Update the root `~/debug-docs/README.md`** — add a bullet under `## Contents` pointing at
   the folder, one line, with enough detail to be searchable.

6. **Commit** in `~/debug-docs` (see commit convention below). Do not push unless asked.

## README.md template

```markdown
# <Title: what broke, in one line>

**Status:** <Root caused / Workaround only / Open / Closed>
**Date:** <YYYY-MM-DD or range>
**Machine:** `<hostname>` — <board summary, e.g. QB2, 2x Blackhole p300c (4 ASICs)>
**Claude Code session:** `<session name>` — run on `<machine>`, working dir `<path>`

## TL;DR

<3-6 sentences. What broke, what the root cause turned out to be, what fixes/workarounds exist,
and what is still unknown. Lead with the answer, not the chronology.>

## Links

| What | Where | Status |
|---|---|---|
| tt-xla issue | [#NNNN](url) — title | open/closed |
| tt-metal issue | [#NNNN](url) — title | open |
| PR / branch | [`branch`](url) — what it contains | merged/open/unmerged |
| Gist: <what> | url | ⚠ secret / public |

## Environment

| Component | Version |
|---|---|
| tt-xla | `<sha>` (<date/subject>) |
| tt-mlir | `<sha>` |
| tt-metal | `<sha>` |
| other (vllm, etc) | `<version>` |

Any local patches applied during the session (cherry-picks, debug instrumentation) — list them,
including whether they were reverted afterwards.

## Repro

<The single cheapest command that reproduces it, plus expected symptom. If a standalone repro
exists, lead with that.>

## Files here

- [`<topic>_debug.md`](<topic>_debug.md) — full working record
- [`issue_body.md`](issue_body.md) — as filed
- [`repro_x.py`](repro_x.py) — standalone repro

## Dead ends / do not re-try

<Bulleted. This is often the highest-value section — it stops the next person (or you) burning
time on hypotheses already eliminated. Include *why* each was ruled out.>

## Open questions

<What is still unknown, and what would settle it.>
```

## Rules that matter

- **Record what was actually observed, including retractions.** If a conclusion was reversed
  mid-session, say so and say why. An archive that only lists the final tidy answer teaches
  nothing about the failure modes of the investigation.
- **Mark confidence.** Distinguish "3/3 runs" from "seen once". For flaky failures always record
  run counts, never bare pass/fail.
- **Never claim a link is public when it is secret.** Check gists with
  `gh gist view <id> --json public` (or note it as unverified).
- **Don't copy huge logs into the repo.** Gist them and link. Keep the repo cloneable.
- **Prefer the exact filed text** for issues/comments — GitHub content can be edited later; the
  archive should show what was said at the time.

## Commit convention

Match the repo's existing style — subject starts with the folder or file being added:

```
<folder>/ - add debug archive for <topic> (<issue refs>)

<1-3 line summary of what the investigation concluded.>

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
```

## When NOT to use this

- Trivial one-off fixes with no lasting lesson
- Anything already fully captured in a merged PR description
- Sessions where nothing was concluded and nothing was ruled out (there is no signal to save)
