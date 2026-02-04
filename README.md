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

## Setup

### Initial Setup (Primary Machine)

```bash
# Run interactive setup
cd ~/.claude/skills/skills-sync
./setup-skills-sync.sh
# Choose option 1, follow prompts
```

### Additional Machines

```bash
# Clone and symlink
git clone https://github.com/YOUR_USERNAME/claude-skills.git ~/code/claude-skills
ln -s ~/code/claude-skills ~/.claude/skills
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
├── setup-aliases.sh             # Optional shell aliases
├── skills-sync/                 # Git sync skill
│   ├── SKILL.md                 # Skill definition
│   ├── sync.sh                  # Implementation
│   └── setup-skills-sync.sh     # Setup wizard
└── hf-storage-estimate/         # Storage estimation skill
    ├── SKILL.md                 # Skill definition
    ├── estimate_storage.py      # Implementation
    └── README.md               # Additional docs
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
