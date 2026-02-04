# Skills Sync

Automatically sync your Claude Code skills across multiple machines using Git and GitHub.

## Overview

This skill manages a Git repository of your Claude Code skills, making it easy to:
- ✅ Keep skills synchronized across multiple machines
- ✅ Version control your skills
- ✅ Collaborate and share specific skills
- ✅ Backup skills to GitHub
- ✅ Roll back changes if needed

## Architecture

```
GitHub Repo: your-username/claude-skills
    ↓ (git clone)
~/code/claude-skills/  ← Git repository (where changes are tracked)
    ↓ (symlink)
~/.claude/skills/      ← Claude Code looks here
```

## Initial Setup

### On Your Primary Machine

1. **Setup Git repository:**
   ```bash
   /skills-sync action=setup
   ```

2. **Create GitHub repository:**
   ```bash
   cd ~/code/claude-skills
   gh repo create claude-skills --public
   ```

3. **Add remote and push:**
   ```bash
   git remote add origin https://github.com/YOUR_USERNAME/claude-skills.git
   git push -u origin main
   ```

### On Additional Machines

1. **Clone the repository:**
   ```bash
   cd ~/code
   git clone https://github.com/YOUR_USERNAME/claude-skills.git
   ```

2. **Create symlink:**
   ```bash
   # Backup existing skills if any
   mv ~/.claude/skills ~/.claude/skills.backup 2>/dev/null || true

   # Create symlink
   ln -s ~/code/claude-skills ~/.claude/skills
   ```

3. **Verify:**
   ```bash
   /skills-sync action=status
   ```

## Usage

### Check Status
See what's changed locally and remote status:
```bash
/skills-sync action=status
```

### Pull Latest Changes
Get updates from other machines:
```bash
/skills-sync action=pull
```

### Push Your Changes
Send your changes to GitHub:
```bash
# With default commit message
/skills-sync action=push

# With custom commit message
/skills-sync action=push message="Added new XYZ feature"
```

### Show Help
```bash
/skills-sync action=info
```

## Daily Workflow

### Scenario: You update a skill on Machine A

**On Machine A:**
1. Edit skill files (Claude Code does this automatically)
2. Push changes:
   ```bash
   /skills-sync action=push message="Updated hf-storage-estimate to support new format"
   ```

**On Machine B:**
1. Pull changes:
   ```bash
   /skills-sync action=pull
   ```
2. Skills are now updated!

### Scenario: Claude Code improves a skill

When Claude Code modifies a skill on any machine:
1. Claude Code edits the files directly in `~/.claude/skills/`
2. Since this is a symlink to the Git repo, changes are tracked
3. You can push with:
   ```bash
   /skills-sync action=push message="Claude Code improvements"
   ```

## Features

### Automatic Stashing
If you have local changes when pulling, they're automatically stashed and reapplied.

### Conflict Resolution
If conflicts occur:
```bash
cd ~/.claude/skills
git status  # See conflicts
# Edit files to resolve
git add .
git rebase --continue
git push
```

### Safe Operations
- Backs up original skills directory during setup
- Creates timestamped backups before destructive operations
- Uses git rebase to maintain clean history

## Troubleshooting

### Problem: Symlink broken
```bash
rm ~/.claude/skills
ln -s ~/code/claude-skills ~/.claude/skills
```

### Problem: Can't push (conflicts)
```bash
cd ~/.claude/skills
git pull --rebase
# Resolve any conflicts
git push
```

### Problem: Want to reset to GitHub version
```bash
cd ~/.claude/skills
git fetch origin
git reset --hard origin/main
```

### Problem: Different paths on different machines
Adjust the symlink on each machine:
```bash
# If git repo is in a different location
ln -sf /actual/path/to/claude-skills ~/.claude/skills
```

## Advanced Usage

### Share Specific Skills
Create a branch for experimental skills:
```bash
cd ~/.claude/skills
git checkout -b experimental
# Make changes
git push origin experimental
```

### Restore Previous Version
```bash
cd ~/.claude/skills
git log  # Find commit hash
git checkout <commit-hash> -- skill-name/
git commit -m "Restored skill-name to previous version"
git push
```

### Collaborate with Others
Fork their skills repo, make improvements, and send pull requests!

## Configuration

### Use SSH Instead of HTTPS
```bash
cd ~/.claude/skills
git remote set-url origin git@github.com:YOUR_USERNAME/claude-skills.git
```

### Different Branch Name
```bash
cd ~/.claude/skills
git checkout -b custom-branch
git push -u origin custom-branch
# Update sync.sh to use your branch name
```

## Files

- `skill.json` - Skill manifest
- `sync.sh` - Main sync script
- `README.md` - This file

## Version

1.0.0
