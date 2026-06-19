# My Claude Code Skills

Personal collection of [Claude Code](https://claude.ai/code) skills, synchronized across machines using Git.

## Quick Start

### On Your First Machine

```bash
# Run the setup script included in this repo
cd ~/.claude/skills/skills-sync
./setup-skills-sync.sh
```

Choose option 1 for primary machine setup. The script will guide you through creating the GitHub repository and setting up the sync.

### On Additional Machines

```bash
# Clone this repository
git clone https://github.com/YOUR_USERNAME/claude-skills.git ~/code/claude-skills

# Create symlink
ln -s ~/code/claude-skills ~/.claude/skills

# Verify it works
/skills-sync action=status
```

## Daily Usage

```bash
# Pull latest changes from other machines
/skills-sync action=pull

# Push your changes
/skills-sync action=push message="Updated XYZ skill"

# Check sync status
/skills-sync action=status
```

## Skills in This Repository

### skills-sync
**Git synchronization for Claude Code skills**

Automatically sync your skills across multiple machines using GitHub.

- `/skills-sync action=pull` - Pull latest changes
- `/skills-sync action=push` - Push your changes
- `/skills-sync action=status` - Check sync status

📖 [Full Documentation](skills-sync/SKILLS_SYNC_SOLUTION.md) | [Setup Guide](skills-sync/README.md)

### hf-storage-estimate
**HuggingFace model storage estimation**

Analyze test collection logs and estimate HuggingFace storage requirements for all models.

- `/hf-storage-estimate log_file=/path/to/logfile.log`

Generates comprehensive reports including:
- Total storage estimates with safety buffers
- Breakdown by model category (LLM, Vision, CNN, etc.)
- CSV export for spreadsheet analysis
- Visual breakdown charts

📖 [Documentation](hf-storage-estimate/README.md)

## Architecture

```
GitHub Repository (this repo)
    ↓
~/code/claude-skills/  ← Git repository (where changes are tracked)
    ↓ (symlink)
~/.claude/skills/      ← Claude Code reads/writes here
```

Claude Code modifies files in `~/.claude/skills/`, which is actually a symlink to the Git repository, so all changes are automatically tracked and can be synced across machines.

### Global CLAUDE.md (cross-machine working notes)

This repo also holds a root-level `CLAUDE.md` — global, always-loaded working notes
(operational pitfalls, machine/setup gotchas). It rides the same sync. On each machine,
symlink it into place once (in addition to the skills symlink):

```bash
ln -s "$(pwd)/CLAUDE.md" ~/.claude/CLAUDE.md   # run from the repo checkout
```

`skills-sync push` / `pull` keep it in sync like everything else (`sync.sh` does `git add .`).

## How It Works

1. **On any machine**: Claude Code (or you) modify a skill
2. **Changes tracked**: Git automatically tracks all changes
3. **Push**: `/skills-sync action=push message="Your change description"`
4. **On other machines**: `/skills-sync action=pull`
5. **Done**: All machines now have the updated skills

## Documentation

- **Complete Setup Guide**: [skills-sync/SKILLS_SYNC_SOLUTION.md](skills-sync/SKILLS_SYNC_SOLUTION.md)
- **Interactive Setup Script**: [skills-sync/setup-skills-sync.sh](skills-sync/setup-skills-sync.sh)
- **Skills Sync README**: [skills-sync/README.md](skills-sync/README.md)

## Benefits

✅ Skills available on all machines
✅ Version history with Git
✅ Easy rollback if something breaks
✅ Collaborate with others (share specific skills)
✅ Backup on GitHub
✅ Claude Code can modify files directly

## Adding New Skills

Just create a new directory with a `skill.json` file:

```bash
mkdir -p ~/.claude/skills/my-new-skill
cd ~/.claude/skills/my-new-skill

# Create skill.json
cat > skill.json << 'EOF'
{
  "name": "my-new-skill",
  "version": "1.0.0",
  "description": "What this skill does",
  "prompt": "Instructions for Claude...",
  "parameters": []
}
EOF

# Commit and push
/skills-sync action=push message="Added my-new-skill"
```

## Troubleshooting

### Symlink Issues
```bash
# Recreate symlink
rm ~/.claude/skills
ln -s ~/code/claude-skills ~/.claude/skills
```

### Git Conflicts
```bash
cd ~/.claude/skills
git status  # See what's conflicted
# Resolve conflicts, then:
git add .
git rebase --continue
git push
```

### Out of Sync
```bash
# Pull latest with automatic conflict resolution
/skills-sync action=pull

# If that fails, manually resolve:
cd ~/.claude/skills
git fetch origin
git rebase origin/main
```

## Repository Structure

```
claude-skills/
├── README.md                    # This file
├── .gitignore                   # Files to ignore
├── skills-sync/                 # Sync management skill
│   ├── skill.json
│   ├── sync.sh
│   ├── README.md
│   ├── SKILLS_SYNC_SOLUTION.md  # Comprehensive guide
│   └── setup-skills-sync.sh     # Interactive setup
├── hf-storage-estimate/         # Storage estimation skill
│   ├── skill.json
│   ├── estimate_storage.py
│   └── README.md
└── (your other skills)/
```

## Contributing

This is a personal skills repository, but feel free to fork and create your own! If you have improvements to specific skills, you can:

1. Fork this repository
2. Make your improvements
3. Use them in your own skills collection

## Security

- Keep sensitive data out of skills (use `.gitignore`)
- Consider using a private GitHub repository
- Use SSH keys for Git authentication

## License

Personal use. Skills are tools for productivity.

---

**Synced with**: `skills-sync` skill
**Last Updated**: Automatically maintained via Git
