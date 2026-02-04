#!/bin/bash
# Setup convenient aliases for Claude skills

SKILLS_DIR="$HOME/.claude/skills"

# Detect shell
SHELL_RC=""
if [ -n "$BASH_VERSION" ]; then
    SHELL_RC="$HOME/.bashrc"
elif [ -n "$ZSH_VERSION" ]; then
    SHELL_RC="$HOME/.zshrc"
fi

if [ -z "$SHELL_RC" ]; then
    echo "Could not detect shell type. Please add aliases manually."
    exit 1
fi

# Check if aliases already exist
if grep -q "# Claude Code Skills Aliases" "$SHELL_RC" 2>/dev/null; then
    echo "Aliases already exist in $SHELL_RC"
    exit 0
fi

# Add aliases
cat >> "$SHELL_RC" << 'EOF'

# Claude Code Skills Aliases
export CLAUDE_SKILLS_DIR="$HOME/.claude/skills"
alias skills-sync="$CLAUDE_SKILLS_DIR/skills-sync/sync.sh"
alias hf-storage-estimate="$CLAUDE_SKILLS_DIR/hf-storage-estimate/estimate_storage.py"

# Convenience shortcuts
alias skills-pull="skills-sync pull"
alias skills-push="skills-sync push"
alias skills-status="skills-sync status"
EOF

echo "✓ Aliases added to $SHELL_RC"
echo ""
echo "Run: source $SHELL_RC"
echo ""
echo "Then you can use:"
echo "  skills-sync status"
echo "  skills-sync pull"
echo "  skills-sync push"
echo "  hf-storage-estimate /path/to/log"
