# My Claude Code Tools

Personal collection of scripts and tools for Claude Code, synchronized across machines using Git.

## Quick Setup

### 1. Set up shell aliases (one-time)

```bash
~/.claude/skills/setup-aliases.sh
source ~/.bashrc  # or ~/.zshrc
```

### 2. Initialize Git sync (on first machine)

```bash
cd ~/.claude/skills/skills-sync
./setup-skills-sync.sh
```

## Available Tools

### skills-sync
**Git synchronization for your tools**

```bash
# Check what's changed
skills-sync status

# Pull updates from other machines
skills-sync pull

# Push your changes
skills-sync push "Updated something"

# Or use shortcuts
skills-status
skills-pull
skills-push "Your message"
```

📖 [Full Documentation](skills-sync/SKILLS_SYNC_SOLUTION.md)

### hf-storage-estimate
**HuggingFace model storage estimation**

```bash
# Analyze a log file
hf-storage-estimate /path/to/logfile.log

# Example
hf-storage-estimate test_matrix_analysis_*/entry_1_collect.log
```

Generates comprehensive reports with storage estimates, breakdowns, and CSV exports.

📖 [Documentation](hf-storage-estimate/README.md)

## How It Works

### Architecture

```
GitHub Repository
    ↓
~/code/claude-skills/  ← Git repository (when using setup-skills-sync.sh)
    ↓ (or symlink)
~/.claude/skills/      ← Scripts and tools live here
```

### Daily Workflow

**On Machine A:**
```bash
# Edit or add tools
vim ~/.claude/skills/my-script.sh

# Push changes
skills-push "Added new feature"
```

**On Machine B:**
```bash
# Get updates
skills-pull
```

## Multi-Machine Setup

### Primary Machine
```bash
cd ~/.claude/skills/skills-sync
./setup-skills-sync.sh
# Choose option 1, follow prompts
```

### Additional Machines
```bash
# Option 1: Use setup script
./setup-skills-sync.sh  # Choose option 2

# Option 2: Manual
git clone https://github.com/YOUR_USERNAME/claude-skills.git ~/code/claude-skills
ln -s ~/code/claude-skills ~/.claude/skills
~/.claude/skills/setup-aliases.sh
source ~/.bashrc
```

## Adding Your Own Tools

```bash
# Create a new script
cat > ~/.claude/skills/my-tool.sh << 'SCRIPT_EOF'
#!/bin/bash
echo "Hello from my tool!"
SCRIPT_EOF

chmod +x ~/.claude/skills/my-tool.sh

# Add alias (edit ~/.bashrc)
echo 'alias my-tool="$HOME/.claude/skills/my-tool.sh"' >> ~/.bashrc
source ~/.bashrc

# Use it
my-tool

# Sync to other machines
skills-push "Added my-tool"
```

## Directory Structure

```
~/.claude/skills/
├── README.md                      # This file
├── setup-aliases.sh               # Shell alias setup
├── skills-sync/                   # Git sync tool
│   ├── sync.sh                    # Main script
│   ├── setup-skills-sync.sh       # Setup wizard
│   └── README.md
├── hf-storage-estimate/           # Storage estimation tool
│   ├── estimate_storage.py
│   └── README.md
└── (your other tools)/
```

## Troubleshooting

### "Command not found"

```bash
# Re-run alias setup
~/.claude/skills/setup-aliases.sh
source ~/.bashrc  # or ~/.zshrc
```

### Git sync not working

```bash
# Check git status
cd ~/.claude/skills
git status

# Or use the tool
skills-status
```

## Why This Approach?

This uses shell scripts and aliases instead of formal Claude Code skills because:

✅ Works immediately
✅ Easy to understand and modify
✅ Git-syncable across machines
✅ Flexible - any script works
✅ No special format required

Claude Code can still create and modify these scripts - they're just regular files!

---

**Synced with**: Git/GitHub
**Invoked via**: Shell aliases
