# My Claude Code Skills

Personal collection of Claude Code skills, synchronized across machines using Git.

## ✅ Real Claude Code Skills

These are proper Claude Code skills that Claude will automatically use based on context!

### skills-sync
**Automatic Git synchronization**

Claude will automatically use this skill when you mention syncing, pushing, or pulling skills.

**Example phrases:**
- "Sync my skills"
- "Push my skills to GitHub"
- "Pull latest skills"
- "Check skill status"

📖 [Documentation](skills-sync/SKILL.md)

### hf-storage-estimate
**Automatic HuggingFace storage estimation**

Claude will automatically use this skill when you mention storage estimation or analyzing model logs.

**Example phrases:**
- "Estimate storage for this log file"
- "How much disk space do I need?"
- "Analyze models in entry_1_collect.log"

📖 [Documentation](hf-storage-estimate/SKILL.md)

### prefill-perf-debug
**Chunked-prefill performance on TT multi-chip, gated on accuracy**

A human-readable runbook (cost model, measurement hygiene, per-layer PCC gating, the localization funnel, a
lever catalogue with measured outcomes, SDPA kernel traps, and how to land the PR) plus small tools. The skill
makes Claude read the runbook and hold to its gates.

**Example phrases:**
- "Why is TTFT so high?"
- "Long-context throughput is bad — where does the time go?"
- "Compare chunk size 2048 vs 8192"
- "Is this a prefill perf regression?"

📖 [Runbook](prefill-perf-debug/RUNBOOK.md) · [Tools](prefill-perf-debug/tools/README.md)

### prefill-perf-charts
**Time-to-context line charts from `[traced_perf]` prefill logs, published as a gist**

Extracts per-chunk traced device time from prefill perf logs (local dirs or `*.tar.gz.b64` bundles in a gist), plots one curve per milestone x chunk size from a JSON config (by-chunk, compare, small multiples, per-chunk cost), writes `stats.md` with checkpoint values and a fixed + slope fit, and publishes a secret gist with the README listed first.

**Example phrases:**
- "Plot prefill time from first chunk to max context for 2k/4k/8k"
- "Baseline vs latest prefill curves on one graph"
- "Put the perf journey charts in a gist"

📖 [Skill](prefill-perf-charts/SKILL.md) · [Example config](prefill-perf-charts/examples/gemma4_journey_1006.json)

## How Skills Work

Skills use `SKILL.md` files with YAML frontmatter:

```markdown
---
name: skill-name
description: When Claude should use this skill...
version: 1.0.0
---

# Skill Content
Instructions and guidance for Claude...
```

## Install

Clone the repo anywhere, then run the installer from inside it:

```bash
git clone git@github.com:kmabeeTT/claude-skills.git ~/claude-skills
cd ~/claude-skills
./install.sh
```

That creates the symlinks this layout depends on, in `$CLAUDE_CONFIG_DIR` (if set) and `~/.claude`:

| Link | Purpose |
|------|---------|
| `<config>/skills` -> this repo | where Claude Code loads skills from |
| `<config>/CLAUDE.md` -> `./CLAUDE.md` | global, always-loaded working notes |
| `<config>/projects/<key>/memory` -> `./memory/<dir>` | per-project memory, one line per project in `memory/PROJECTS` (see below) |

Restart Claude Code (or start a new session) afterwards to pick the skills up.

`install.sh` resolves the repo location from its own path, so the clone can live anywhere —
`~/claude-skills`, `~/code/claude-skills`, whatever. It is idempotent: re-running when the
links are already correct reports `ok` and changes nothing.

**Options**

| Flag | Effect |
|------|--------|
| `--dry-run` | print what would happen, touch nothing |
| `--force` | repoint a symlink aimed elsewhere; move a real file/dir aside to `<name>.bak.<timestamp>` (a real memory dir is merged into the repo first) |
| `--skip-claude-md` | leave the global `CLAUDE.md` alone |
| `--skip-memory` | leave project memory dirs alone |
| `--config DIR` | only this config dir (repeatable) |
| `--help` | usage |

It never deletes anything. If `~/.claude/skills` is a real directory rather than a symlink,
it refuses and exits 1 instead of risking skills that exist only on that machine — `--force`
renames it out of the way rather than removing it.

Optional extras:

```bash
./setup-aliases.sh    # shell aliases: skills-push / skills-pull / skills-status (edits your shell rc)
```

### First-time sync setup

Only needed when creating the GitHub side from scratch, rather than cloning an existing repo:

```bash
cd ~/claude-skills/skills-sync
./setup-skills-sync.sh     # choose option 1, follow the prompts
```

## Git Sync Workflow

Once set up, skills are automatically synced via Git:

**On any machine:**
1. Claude modifies skills (or you edit them)
2. Say: "Push my skills" → Claude runs the sync
3. On other machines, say: "Pull latest skills"

## Architecture

```
GitHub Repository
    ↓
~/code/claude-skills/  ← Git repository
    ↓ (symlink)
~/.claude/skills/      ← Claude Code loads skills from here
```

## Creating New Skills

```bash
mkdir -p ~/.claude/skills/my-new-skill

cat > ~/.claude/skills/my-new-skill/SKILL.md << 'SKILL_EOF'
---
name: my-new-skill
description: This skill should be used when the user asks to "trigger phrase" or discusses relevant-topic.
version: 1.0.0
---

# My New Skill

Instructions for Claude on how to handle this skill...
SKILL_EOF

# Claude Code will auto-detect the new skill!
```

Then say: "Push my skills" and Claude will sync it to GitHub.

## Directory Structure

```
~/.claude/skills/
├── README.md                    # This file
├── install.sh                   # Wire this checkout into the Claude config dirs (symlinks)
├── memory/                      # Per-project memory; memory/PROJECTS maps project keys to dirs
├── setup-aliases.sh             # Optional shell aliases
├── skills-sync/                 # Git sync skill
│   ├── SKILL.md                 # Skill definition
│   ├── sync.sh                  # Implementation
│   └── setup-skills-sync.sh     # Setup wizard
├── hf-storage-estimate/         # Storage estimation skill
│   ├── SKILL.md                 # Skill definition
│   ├── estimate_storage.py      # Implementation
│   └── README.md                # Additional docs
└── prefill-perf-debug/          # Chunked-prefill perf runbook + skill
    ├── SKILL.md                 # Thin loader: read the runbook, follow its gates
    ├── RUNBOOK.md               # The method (humans start here)
    └── tools/                   # Queue helpers, fit, PCC compare, power sampler, accum sims
```

## Benefits

✅ **Automatic activation** - Claude uses skills based on context
✅ **Git-backed** - Version control and sync across machines
✅ **Claude-editable** - Claude can modify skills directly
✅ **No special invocation** - Just describe what you want
✅ **Shareable** - Others can clone your skills repo

## Tips

- **Testing skills**: Say something that matches the skill's description triggers
- **Updating skills**: Edit `SKILL.md` files, Claude will use the updated version
- **Sync often**: Push/pull skills regularly to keep machines in sync
- **Clear descriptions**: Skill descriptions determine when Claude activates them

## Troubleshooting

### Skill not activating

Check the `description` field in `SKILL.md` - it needs phrases that match what users say.

### Skills not syncing

```bash
cd ~/.claude/skills
git status  # Check if it's a git repo
ls -la ~/.claude/skills  # Check if symlink is valid
```

Or just say: "Check skill status" and Claude will use the skills-sync skill!

---

**Format**: `SKILL.md` with YAML frontmatter
**Synced via**: Git/GitHub
**Activated**: Automatically by Claude based on context

## Claude Code memory (`memory/`) and where notes go

Two homes, one place per note (the rule Claude follows is in `CLAUDE.md`, "Where notes go"):

- **Rules that apply in every project** go in `CLAUDE.md`, which `install.sh` links into each config dir.
- **Notes about one repo** go in that project's auto-memory dir. Claude Code keeps it at `<config>/projects/<key>/memory/`, where `<key>` is the repo path with `/` turned into `-` (worktrees and subdirectories share their repo's key). `install.sh` links each `<key>` listed in `memory/PROJECTS` to `memory/<dir>/` here, in `$CLAUDE_CONFIG_DIR` and `~/.claude`. Several keys can share a dir: the three tt-metal clones all use `memory/tt-metal/`.

To give a new project tracked memory, add `<key> <dir>` to `memory/PROJECTS` and run `./install.sh`. It creates `memory/<dir>/` if needed. If Claude already made a real memory dir there, `./install.sh --force` merges its notes in (new files copied, new index lines appended) and moves the original to `memory.bak.<stamp>`. A note of the same name with different content is a CONFLICT: nothing is copied for that project until you resolve it.

Each dir's `MEMORY.md` is the index (one line per note); each note has `name`/`description`/`metadata.type` frontmatter and links others as `[[name]]`. Other Claude sessions write here concurrently, so commit only your own paths. Notes must not contain secrets.
