#!/bin/bash
# Claude Code Skills Sync Script
# Manages Git synchronization of skills across machines

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Determine skills directory (resolve symlink if present)
SKILLS_DIR="$HOME/.claude/skills"
if [ -L "$SKILLS_DIR" ]; then
    REAL_SKILLS_DIR=$(readlink -f "$SKILLS_DIR")
else
    REAL_SKILLS_DIR="$SKILLS_DIR"
fi

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

check_git_repo() {
    if [ ! -d "$REAL_SKILLS_DIR/.git" ]; then
        print_error "Skills directory is not a Git repository: $REAL_SKILLS_DIR"
        print_info "Run: /skills-sync action=setup"
        exit 1
    fi
}

action_status() {
    check_git_repo
    cd "$REAL_SKILLS_DIR"

    print_info "Skills directory: $REAL_SKILLS_DIR"
    print_info "Git status:"
    echo ""

    git status

    echo ""
    print_info "Remote repository:"
    git remote -v
}

action_pull() {
    check_git_repo
    cd "$REAL_SKILLS_DIR"

    print_info "Pulling latest changes from remote..."

    # Fetch first
    git fetch origin

    # Check if there are changes
    LOCAL=$(git rev-parse @)
    REMOTE=$(git rev-parse @{u} 2>/dev/null || echo "")

    if [ -z "$REMOTE" ]; then
        print_warning "No upstream branch configured"
        print_info "Setting upstream to origin/main"
        git branch --set-upstream-to=origin/main main
        REMOTE=$(git rev-parse @{u})
    fi

    if [ "$LOCAL" = "$REMOTE" ]; then
        print_success "Already up to date"
        return 0
    fi

    # Check for local changes
    if [ -n "$(git status --porcelain)" ]; then
        print_warning "Local changes detected, stashing..."
        git stash push -m "Auto-stash before pull $(date +%Y%m%d_%H%M%S)"
        STASHED=1
    fi

    # Pull with rebase
    git pull --rebase origin main

    if [ "${STASHED:-0}" -eq 1 ]; then
        print_info "Applying stashed changes..."
        if git stash pop; then
            print_success "Successfully applied stashed changes"
        else
            print_warning "Conflicts detected in stashed changes"
            print_info "Resolve conflicts and run: git stash drop"
        fi
    fi

    print_success "Pull completed"
}

action_push() {
    check_git_repo
    cd "$REAL_SKILLS_DIR"

    # Check if there are changes
    if [ -z "$(git status --porcelain)" ]; then
        print_success "No changes to commit"

        # Check if local is ahead of remote
        git fetch origin
        LOCAL=$(git rev-parse @)
        REMOTE=$(git rev-parse @{u} 2>/dev/null || echo "$LOCAL")

        if [ "$LOCAL" != "$REMOTE" ]; then
            print_info "Pushing existing commits..."
            git push origin main
            print_success "Push completed"
        fi

        return 0
    fi

    # Get commit message
    COMMIT_MSG="${1:-Update skills $(date +%Y-%m-%d)}"

    print_info "Staging changes..."
    git add .

    print_info "Files to be committed:"
    git status --short
    echo ""

    print_info "Committing with message: $COMMIT_MSG"
    git commit -m "$COMMIT_MSG"

    print_info "Pushing to remote..."
    git push origin main

    print_success "Push completed successfully"
    print_info "Changes are now available on other machines"
}

action_setup() {
    print_info "Setting up Git repository for skills..."

    # Check if already a symlink to a git repo
    if [ -L "$SKILLS_DIR" ] && [ -d "$REAL_SKILLS_DIR/.git" ]; then
        print_success "Skills directory is already set up with Git"
        print_info "Directory: $REAL_SKILLS_DIR"
        cd "$REAL_SKILLS_DIR"
        git remote -v
        return 0
    fi

    # Check if skills directory exists and is not empty
    if [ -d "$SKILLS_DIR" ] && [ "$(ls -A $SKILLS_DIR)" ]; then
        print_info "Existing skills found, will preserve them"

        # Create repo location
        REPO_DIR="$HOME/code/claude-skills"
        mkdir -p "$REPO_DIR"

        print_info "Copying existing skills to: $REPO_DIR"
        cp -r "$SKILLS_DIR"/* "$REPO_DIR/"

        # Initialize git
        cd "$REPO_DIR"
        if [ ! -d ".git" ]; then
            git init
            git checkout -b main 2>/dev/null || git checkout main

            # Create README
            cat > README.md << 'EOF'
# My Claude Code Skills

Personal collection of Claude Code skills, synced across machines.

## Syncing

Use the `skills-sync` skill to manage synchronization:

- `/skills-sync action=pull` - Pull latest changes
- `/skills-sync action=push message="Your commit message"` - Push changes
- `/skills-sync action=status` - Check status

## Skills

EOF

            # List skills
            for skill_dir in */; do
                if [ -f "${skill_dir}skill.json" ]; then
                    echo "- \`${skill_dir%/}\`" >> README.md
                fi
            done

            # Create .gitignore
            cat > .gitignore << 'EOF'
*.pyc
__pycache__/
.DS_Store
*.swp
*.swo
*~
.venv/
venv/
*.log
EOF

            git add .
            git commit -m "Initial commit: Claude Code skills"

            print_success "Git repository initialized"
        fi

        # Backup original
        print_info "Backing up original skills directory"
        mv "$SKILLS_DIR" "${SKILLS_DIR}.backup.$(date +%Y%m%d_%H%M%S)"

        # Create symlink
        ln -s "$REPO_DIR" "$SKILLS_DIR"
        print_success "Created symlink: $SKILLS_DIR -> $REPO_DIR"

        print_warning "Next steps:"
        echo "  1. Create GitHub repository:"
        echo "     gh repo create claude-skills --public"
        echo ""
        echo "  2. Add remote and push:"
        echo "     cd $REPO_DIR"
        echo "     git remote add origin https://github.com/YOUR_USERNAME/claude-skills.git"
        echo "     git push -u origin main"
        echo ""
        echo "  3. On other machines, clone and symlink:"
        echo "     git clone https://github.com/YOUR_USERNAME/claude-skills.git ~/code/claude-skills"
        echo "     ln -s ~/code/claude-skills ~/.claude/skills"
    else
        print_error "Skills directory is empty or doesn't exist"
        print_info "Nothing to set up"
        exit 1
    fi
}

action_info() {
    cat << EOF
${BLUE}Claude Code Skills Sync${NC}

${GREEN}Usage:${NC}
  /skills-sync action=status                          # Show git status
  /skills-sync action=pull                            # Pull latest changes
  /skills-sync action=push                            # Push with default message
  /skills-sync action=push message="Updated X skill"  # Push with custom message
  /skills-sync action=setup                           # Initial setup

${GREEN}Current Configuration:${NC}
  Skills directory: $SKILLS_DIR
  Real location:    $REAL_SKILLS_DIR
  Is symlink:       $([ -L "$SKILLS_DIR" ] && echo "Yes" || echo "No")
  Is Git repo:      $([ -d "$REAL_SKILLS_DIR/.git" ] && echo "Yes" || echo "No")

${GREEN}Workflow:${NC}
  1. Make changes to skills on any machine
  2. Push: /skills-sync action=push message="Added new feature"
  3. On other machines: /skills-sync action=pull

${GREEN}Multi-Machine Setup:${NC}
  Primary machine:
    /skills-sync action=setup
    # Create GitHub repo and push

  Other machines:
    git clone https://github.com/YOUR_USERNAME/claude-skills.git ~/code/claude-skills
    ln -s ~/code/claude-skills ~/.claude/skills

EOF
}

# Main execution
ACTION="${1:-info}"

case "$ACTION" in
    status)
        action_status
        ;;
    pull)
        action_pull
        ;;
    push)
        action_push "$2"
        ;;
    setup)
        action_setup
        ;;
    info|help|--help|-h)
        action_info
        ;;
    *)
        print_error "Unknown action: $ACTION"
        print_info "Valid actions: status, pull, push, setup, info"
        exit 1
        ;;
esac
