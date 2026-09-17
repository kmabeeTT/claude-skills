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
**Chunked-prefill performance, as a repeatable funnel**

Finds whether prefill time is going into the per-chunk cost or the prefix cost, which
layers own each, which ops inside them, and — with approval — what those ops are bound
by. Enforces twelve assertions (A1–A12) drawn from claims that were published and then
retracted, so it refuses to say more than was measured.

**Example phrases:**
- "Why is TTFT so high?"
- "Long-context throughput is bad — where does the time go?"
- "Compare chunk size 2048 vs 8192"
- "Is this a prefill perf regression?"

Levels 0–2 are automated; level 3 (ablations) is assisted only. `validate.py` reproduces
the published Gemma4 results offline as a regression test — 102 checks, no device time.

📖 [Documentation](prefill-perf-debug/README.md) · [Method and traps](prefill-perf-debug/METHOD.md)

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

That creates the two symlinks this layout depends on:

| Link | Purpose |
|------|---------|
| `~/.claude/skills` -> this repo | where Claude Code loads skills from |
| `~/.claude/CLAUDE.md` -> `./CLAUDE.md` | global, always-loaded working notes |

Restart Claude Code (or start a new session) afterwards to pick the skills up.

`install.sh` resolves the repo location from its own path, so the clone can live anywhere —
`~/claude-skills`, `~/code/claude-skills`, whatever. It is idempotent: re-running when both
links are already correct reports `ok` and changes nothing.

**Options**

| Flag | Effect |
|------|--------|
| `--dry-run` | print what would happen, touch nothing |
| `--force` | repoint a symlink aimed elsewhere; move a real file/dir aside to `<name>.bak.<timestamp>` |
| `--skip-claude-md` | install skills only, leave the global `CLAUDE.md` alone |
| `--help` | usage |

It never deletes anything. If `~/.claude/skills` is a real directory rather than a symlink,
it refuses and exits 1 instead of risking skills that exist only on that machine — `--force`
renames it out of the way rather than removing it. Honors `CLAUDE_CONFIG_DIR` if Claude's
config lives somewhere other than `~/.claude`.

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
├── install.sh                   # Wire this checkout into ~/.claude (symlinks)
├── setup-aliases.sh             # Optional shell aliases
├── skills-sync/                 # Git sync skill
│   ├── SKILL.md                 # Skill definition
│   ├── sync.sh                  # Implementation
│   └── setup-skills-sync.sh     # Setup wizard
├── hf-storage-estimate/         # Storage estimation skill
│   ├── SKILL.md                 # Skill definition
│   ├── estimate_storage.py      # Implementation
│   └── README.md                # Additional docs
└── prefill-perf-debug/          # Chunked-prefill perf funnel
    ├── SKILL.md                 # The procedure Claude follows
    ├── METHOD.md                # Why each assertion exists
    ├── EXAMPLES.md              # Worked examples, real output
    ├── ppd.py                   # CLI (probe/budget/level0-3/check/compare/analyze)
    ├── assertions.py            # A1-A12 as checkable code
    ├── validate.py              # Offline regression test vs published results
    ├── profiles/                # Per-model harness descriptions
    └── tests/run_tests.sh       # validate + CLI smoke + unit checks
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
