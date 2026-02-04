---
name: skills-sync
description: This skill should be used when the user asks to "sync skills", "push skills", "pull skills", "check skill status", "sync my tools", "update skills from GitHub", "commit skills", or discusses synchronizing their Claude Code skills across machines using Git.
version: 1.0.0
---

# Skills Sync

Synchronize Claude Code skills across multiple machines using Git and GitHub.

## When to Use This Skill

Use this skill when the user wants to:
- Sync their skills with GitHub
- Pull latest skills from other machines
- Push skill changes to GitHub
- Check Git status of their skills directory
- Set up Git synchronization for skills

## Available Actions

### status
Check the current Git status and configuration of the skills directory.

```bash
~/.claude/skills/skills-sync/sync.sh status
```

### pull
Pull the latest changes from the remote GitHub repository.

```bash
~/.claude/skills/skills-sync/sync.sh pull
```

This will:
- Fetch changes from GitHub
- Rebase local changes if any
- Auto-stash and reapply local modifications if conflicts occur

### push
Commit and push local changes to GitHub.

```bash
~/.claude/skills/skills-sync/sync.sh push "Commit message"
```

If no message is provided, a default timestamped message is used.

### setup
Initialize Git repository and symlink structure for multi-machine sync.

```bash
~/.claude/skills/skills-sync/setup-skills-sync.sh
```

This interactive script guides through:
- Primary machine setup (first time)
- Additional machine setup (cloning existing repo)
- GitHub repository creation
- Symlink configuration

## Architecture

```
GitHub Repository
    ↓
~/code/claude-skills/  ← Git repository (tracks all changes)
    ↓ (symlink)
~/.claude/skills/      ← Claude Code reads/writes here
```

Skills directory is a symlink to the Git repository, so all changes by Claude Code or the user are automatically tracked and can be synced.

## Common Workflows

### After Modifying Skills
When skills are created or modified (by Claude or user):

```bash
~/.claude/skills/skills-sync/sync.sh push "Added new feature"
```

### On Another Machine
To get the updates:

```bash
~/.claude/skills/skills-sync/sync.sh pull
```

### Check Sync Status
Before pushing or to see what changed:

```bash
~/.claude/skills/skills-sync/sync.sh status
```

## Multi-Machine Setup

### First Machine
Run the setup script and follow prompts:

```bash
~/.claude/skills/skills-sync/setup-skills-sync.sh
```

Choose option 1 for primary machine setup.

### Additional Machines
On other machines, run the same script:

```bash
~/.claude/skills/skills-sync/setup-skills-sync.sh
```

Choose option 2 and provide the GitHub repository URL.

## Troubleshooting

### Merge Conflicts
If conflicts occur during pull:

```bash
cd ~/.claude/skills
git status  # See conflicted files
# Edit files to resolve conflicts
git add .
git rebase --continue
```

### Symlink Issues
If the symlink is broken:

```bash
rm ~/.claude/skills
ln -s ~/code/claude-skills ~/.claude/skills
```

### Out of Sync
To force sync to remote state:

```bash
cd ~/.claude/skills
git fetch origin
git reset --hard origin/main
```

## Shell Aliases

For convenience, users can add to `~/.bashrc`:

```bash
alias skills-sync="$HOME/.claude/skills/skills-sync/sync.sh"
alias skills-pull="$HOME/.claude/skills/skills-sync/sync.sh pull"
alias skills-push="$HOME/.claude/skills/skills-sync/sync.sh push"
alias skills-status="$HOME/.claude/skills/skills-sync/sync.sh status"
```

Then invoke as: `skills-sync push "message"`

## Implementation Notes

When the user asks to sync skills, invoke the appropriate bash script directly rather than trying to use a formal skill invocation syntax. Execute the script with the Bash tool.

Example:
- User: "Push my skills to GitHub"
- Action: Execute `~/.claude/skills/skills-sync/sync.sh push "Updated skills"`
