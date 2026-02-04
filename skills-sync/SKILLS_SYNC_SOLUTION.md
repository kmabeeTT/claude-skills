# Claude Code Skills Sync - Complete Solution

## Problem Statement

You work across multiple machines at different sites with non-shared home directories and want to:
- Keep your Claude Code skills synchronized across all machines
- Allow Claude Code to update skills and push changes
- Maintain a clean, version-controlled workflow

## Solution Overview

**Git + GitHub + Symlinks**

```
┌─────────────────────────────────────────────────────┐
│                    GitHub                            │
│         your-username/claude-skills                  │
└──────────────┬──────────────────────┬────────────────┘
               │                      │
         git pull/push          git pull/push
               │                      │
        ┌──────▼──────┐        ┌──────▼──────┐
        │  Machine A   │        │  Machine B   │
        │              │        │              │
        │ ~/code/      │        │ ~/code/      │
        │ claude-      │        │ claude-      │
        │ skills/      │        │ skills/      │
        │   (Git repo) │        │   (Git repo) │
        │      ▲       │        │      ▲       │
        │      │       │        │      │       │
        │   symlink    │        │   symlink    │
        │      │       │        │      │       │
        │ ~/.claude/   │        │ ~/.claude/   │
        │ skills/      │        │ skills/      │
        │              │        │              │
        │ Claude Code  │        │ Claude Code  │
        │ reads/writes │        │ reads/writes │
        │ here         │        │ here         │
        └──────────────┘        └──────────────┘
```

## What I've Created for You

### 1. **skills-sync Skill**
Located at: `~/.claude/skills/skills-sync/`

A complete skill for managing Git synchronization:
- Pull latest changes from GitHub
- Push your changes to GitHub
- Check sync status
- Initial setup automation

### 2. **Interactive Setup Script**
Located at: `scratchpad/setup-skills-sync.sh`

A user-friendly script that walks you through:
- Primary machine setup (first time)
- Additional machine setup (subsequent machines)
- GitHub repository creation
- Symlink configuration

### 3. **Documentation**
- Setup guide: `scratchpad/skills-sync-guide.md`
- Skill README: `~/.claude/skills/skills-sync/README.md`

## Quick Start

### On Your Primary Machine (Machine A)

```bash
# Run the interactive setup
./scratchpad/setup-skills-sync.sh

# Follow the prompts - it will:
# 1. Create Git repo at ~/code/claude-skills
# 2. Copy your existing skills
# 3. Initialize Git
# 4. Create GitHub repo
# 5. Push to GitHub
# 6. Create symlink
```

### On Additional Machines (Machine B, C, etc.)

```bash
# Option 1: Use the interactive script
./setup-skills-sync.sh
# Choose option 2 "Additional machine"

# Option 2: Manual setup
git clone https://github.com/YOUR_USERNAME/claude-skills.git ~/code/claude-skills
mv ~/.claude/skills ~/.claude/skills.backup 2>/dev/null || true
ln -s ~/code/claude-skills ~/.claude/skills
```

## Daily Usage

### Pushing Changes (When you modify a skill)

```bash
# Simple push with auto-generated commit message
/skills-sync action=push

# Push with custom message
/skills-sync action=push message="Added XYZ feature to hf-storage-estimate"
```

### Pulling Changes (Get updates from other machines)

```bash
/skills-sync action=pull
```

### Check Status

```bash
/skills-sync action=status
```

## How Claude Code Fits In

### When Claude Code Modifies a Skill

1. **Claude reads from**: `~/.claude/skills/some-skill/`
2. **This is actually**: `~/code/claude-skills/some-skill/` (via symlink)
3. **Claude writes to**: Same location
4. **Git tracks**: Changes automatically
5. **You push**: `/skills-sync action=push message="Claude improved XYZ"`

### Workflow Example

**On Machine A:**
```
You: "Claude, improve the hf-storage-estimate skill to handle JSON files"
Claude: [edits files in ~/.claude/skills/hf-storage-estimate/]
You: /skills-sync action=push message="Added JSON support"
```

**On Machine B:**
```
You: /skills-sync action=pull
Claude: [now has access to updated skill]
```

## Benefits

✅ **Automatic Sync**: One command to sync (`/skills-sync action=pull/push`)
✅ **Version Control**: Full Git history of all changes
✅ **Rollback**: Easy to revert to previous versions
✅ **Backup**: Skills backed up on GitHub
✅ **Collaboration**: Share skills with teammates
✅ **Clean**: No complex cloud sync, just Git
✅ **Claude-Friendly**: Claude Code can read/write directly

## Architecture Details

### Directory Structure

```
Machine A & B (identical):

~/.claude/
  └── skills/  → symlink to ~/code/claude-skills/

~/code/
  └── claude-skills/          # Git repository
      ├── .git/               # Git metadata
      ├── .gitignore
      ├── README.md
      ├── hf-storage-estimate/
      │   ├── skill.json
      │   ├── estimate_storage.py
      │   └── README.md
      ├── skills-sync/
      │   ├── skill.json
      │   ├── sync.sh
      │   └── README.md
      └── (other skills)/
```

### Why Symlinks?

- Claude Code always looks in `~/.claude/skills/`
- Symlink redirects to `~/code/claude-skills/` (Git repo)
- Claude Code doesn't know/care it's a symlink
- You get version control without changing Claude Code's behavior

### Why This Location?

- `~/code/` is a common, predictable location
- Easy to find on all machines
- Not tied to specific projects
- Separate from Claude Code's internal structure

## Advanced Usage

### Share a Skill with Someone

```bash
# They fork your repo
git clone https://github.com/THEIR_USERNAME/claude-skills.git
cd claude-skills

# Cherry-pick just one skill
git checkout -b just-hf-estimate
git filter-branch --subdirectory-filter hf-storage-estimate HEAD
git push origin just-hf-estimate
```

### Use Different Branches per Machine

```bash
# Machine A (development)
cd ~/.claude/skills
git checkout -b machine-a-dev

# Machine B (stable)
cd ~/.claude/skills
git checkout main
```

### Automated Sync on Login

Add to `~/.bashrc` or `~/.zshrc`:
```bash
# Auto-pull skills on shell startup (once per day)
if [ -d ~/.claude/skills/.git ]; then
    LAST_PULL_FILE=~/.claude/skills/.last_pull
    if [ ! -f "$LAST_PULL_FILE" ] || [ $(find "$LAST_PULL_FILE" -mtime +1) ]; then
        echo "Syncing Claude Code skills..."
        cd ~/.claude/skills && git pull --quiet && touch "$LAST_PULL_FILE"
    fi
fi
```

### CI/CD for Skills

Create `.github/workflows/test-skills.yml`:
```yaml
name: Test Skills
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Validate skill.json files
        run: |
          for skill in */skill.json; do
            echo "Validating $skill"
            python -m json.tool "$skill" > /dev/null
          done
```

## Troubleshooting

### Problem: "Skills not syncing"

```bash
# Check symlink
ls -la ~/.claude/skills

# Should show: ~/.claude/skills -> /home/user/code/claude-skills

# If broken, recreate:
rm ~/.claude/skills
ln -s ~/code/claude-skills ~/.claude/skills
```

### Problem: "Git conflicts"

```bash
cd ~/.claude/skills
git status  # See what's conflicted

# Option 1: Keep remote version
git checkout --theirs path/to/file
git add .
git rebase --continue

# Option 2: Keep local version
git checkout --ours path/to/file
git add .
git rebase --continue

# Option 3: Manual edit
vim path/to/file  # Resolve conflicts
git add .
git rebase --continue
```

### Problem: "Forgot to push from Machine A"

```bash
# On Machine B (where you are now)
/skills-sync action=status  # Shows "behind"

# On Machine A (later)
/skills-sync action=push

# Back on Machine B
/skills-sync action=pull
```

### Problem: "Want to start over"

```bash
# Backup current state
cp -r ~/.claude/skills ~/.claude/skills.backup.manual

# Remove symlink
rm ~/.claude/skills

# Remove git repo
rm -rf ~/code/claude-skills

# Re-run setup
./setup-skills-sync.sh
```

## Security Considerations

### Private Skills

Use a private GitHub repository:
```bash
gh repo create claude-skills --private
```

### Sensitive Data

Add to `.gitignore`:
```
# Sensitive
**/secrets.json
**/credentials.yaml
**/.env
**/api_keys.txt
```

### SSH Keys

For better security, use SSH instead of HTTPS:
```bash
cd ~/.claude/skills
git remote set-url origin git@github.com:YOUR_USERNAME/claude-skills.git
```

## Migration Guide

### From Manual Copying

If you currently manually copy skills:

1. **Stop manual copying**
2. **Run setup script** on primary machine
3. **Git will track** all future changes
4. **On other machines**: Just clone and symlink

### From Cloud Sync (Dropbox, etc.)

1. **Stop cloud sync** for `~/.claude/skills/`
2. **Copy skills** to non-synced location
3. **Run setup script**
4. **Remove from cloud sync**

## Files Reference

All created files:

```
~/.claude/skills/
├── skills-sync/
│   ├── skill.json              # Skill manifest
│   ├── sync.sh                 # Main sync script
│   └── README.md              # Skill documentation
└── hf-storage-estimate/
    ├── skill.json
    ├── estimate_storage.py
    └── README.md

~/scratchpad/
├── setup-skills-sync.sh        # Interactive setup wizard
├── skills-sync-guide.md        # Setup guide
└── SKILLS_SYNC_SOLUTION.md    # This file
```

## Next Steps

1. **Run the setup script**: `./scratchpad/setup-skills-sync.sh`
2. **Create GitHub repository**: Follow script prompts
3. **Test on current machine**: `/skills-sync action=status`
4. **Setup on other machines**: Run script, choose option 2
5. **Use daily**: `/skills-sync action=pull` and `push`

## Support

If you encounter issues:

1. Check `/skills-sync action=status`
2. Review the README: `cat ~/.claude/skills/skills-sync/README.md`
3. Check Git status: `cd ~/.claude/skills && git status`
4. Ask Claude Code for help with specific errors

---

**Version**: 1.0.0
**Created**: 2026-02-04
**Author**: Claude Code
