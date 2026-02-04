#!/bin/bash
# Interactive setup script for Claude Code Skills Sync
# This script helps you set up Git-based sync for your skills across machines

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

print_header() {
    echo ""
    echo -e "${CYAN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}${BOLD}  $1${NC}"
    echo -e "${CYAN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

print_step() {
    echo -e "${BLUE}➜${NC} ${BOLD}$1${NC}"
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

print_info() {
    echo -e "${CYAN}ℹ${NC} $1"
}

ask_yes_no() {
    local prompt="$1"
    local default="${2:-n}"

    if [ "$default" = "y" ]; then
        prompt="$prompt [Y/n]: "
    else
        prompt="$prompt [y/N]: "
    fi

    while true; do
        read -p "$(echo -e "${YELLOW}?${NC} $prompt")" yn
        yn=${yn:-$default}

        case $yn in
            [Yy]*) return 0 ;;
            [Nn]*) return 1 ;;
            *) echo "Please answer yes or no." ;;
        esac
    done
}

ask_input() {
    local prompt="$1"
    local default="$2"

    if [ -n "$default" ]; then
        prompt="$prompt [$default]: "
    else
        prompt="$prompt: "
    fi

    read -p "$(echo -e "${YELLOW}?${NC} $prompt")" value
    echo "${value:-$default}"
}

check_command() {
    if command -v "$1" &> /dev/null; then
        return 0
    else
        return 1
    fi
}

print_header "Claude Code Skills Sync Setup"

echo "This script will help you set up Git-based synchronization for your"
echo "Claude Code skills across multiple machines using GitHub."
echo ""

# Check prerequisites
print_step "Checking prerequisites..."

MISSING_DEPS=()

if ! check_command git; then
    MISSING_DEPS+=("git")
fi

if ! check_command gh; then
    print_warning "GitHub CLI (gh) not found - you'll need to create the repo manually"
    HAS_GH=false
else
    HAS_GH=true
    print_success "GitHub CLI (gh) found"
fi

if [ ${#MISSING_DEPS[@]} -gt 0 ]; then
    print_error "Missing required dependencies: ${MISSING_DEPS[*]}"
    echo "Please install them and run this script again."
    exit 1
fi

print_success "All required dependencies found"
echo ""

# Determine setup type
print_step "Setup type"
echo "Are you setting up on:"
echo "  1) Primary machine (first time setup)"
echo "  2) Additional machine (already have GitHub repo)"
echo ""

SETUP_TYPE=$(ask_input "Enter choice (1 or 2)" "1")

if [ "$SETUP_TYPE" = "2" ]; then
    # Secondary machine setup
    print_header "Additional Machine Setup"

    GITHUB_USERNAME=$(ask_input "Enter your GitHub username")
    REPO_NAME=$(ask_input "Enter repository name" "claude-skills")

    REPO_URL="https://github.com/$GITHUB_USERNAME/$REPO_NAME.git"
    LOCAL_PATH="$HOME/code/$REPO_NAME"

    print_step "Will clone from: $REPO_URL"
    print_step "To: $LOCAL_PATH"
    echo ""

    if ! ask_yes_no "Continue?" "y"; then
        echo "Aborted."
        exit 0
    fi

    # Clone repository
    print_step "Cloning repository..."
    mkdir -p "$(dirname "$LOCAL_PATH")"

    if [ -d "$LOCAL_PATH" ]; then
        print_warning "Directory already exists: $LOCAL_PATH"
        if ask_yes_no "Pull latest changes instead?" "y"; then
            cd "$LOCAL_PATH"
            git pull
            print_success "Repository updated"
        fi
    else
        git clone "$REPO_URL" "$LOCAL_PATH"
        print_success "Repository cloned"
    fi

    # Backup existing skills
    if [ -d "$HOME/.claude/skills" ] && [ ! -L "$HOME/.claude/skills" ]; then
        BACKUP_PATH="$HOME/.claude/skills.backup.$(date +%Y%m%d_%H%M%S)"
        print_step "Backing up existing skills to: $BACKUP_PATH"
        mv "$HOME/.claude/skills" "$BACKUP_PATH"
        print_success "Backup created"
    fi

    # Create symlink
    if [ -L "$HOME/.claude/skills" ]; then
        rm "$HOME/.claude/skills"
    fi

    print_step "Creating symlink..."
    ln -s "$LOCAL_PATH" "$HOME/.claude/skills"
    print_success "Symlink created: $HOME/.claude/skills -> $LOCAL_PATH"

    print_header "Setup Complete! 🎉"
    echo "Your skills are now synced with GitHub."
    echo ""
    echo "Usage:"
    echo "  /skills-sync action=status  # Check sync status"
    echo "  /skills-sync action=pull    # Pull latest changes"
    echo "  /skills-sync action=push    # Push your changes"
    echo ""

else
    # Primary machine setup
    print_header "Primary Machine Setup"

    SKILLS_DIR="$HOME/.claude/skills"
    REPO_PATH=$(ask_input "Where should the Git repository be?" "$HOME/code/claude-skills")
    REPO_NAME=$(basename "$REPO_PATH")

    print_step "Checking existing skills..."

    if [ ! -d "$SKILLS_DIR" ]; then
        print_error "No skills directory found at: $SKILLS_DIR"
        echo "Please create some skills first, then run this script."
        exit 1
    fi

    SKILL_COUNT=$(find "$SKILLS_DIR" -maxdepth 1 -type d | wc -l)
    SKILL_COUNT=$((SKILL_COUNT - 1))  # Exclude the parent directory

    if [ "$SKILL_COUNT" -eq 0 ]; then
        print_warning "No skills found in: $SKILLS_DIR"
        if ! ask_yes_no "Continue anyway?" "n"; then
            exit 0
        fi
    else
        print_success "Found $SKILL_COUNT skill(s)"
    fi

    echo ""
    print_step "Setup plan:"
    echo "  1. Create Git repository at: $REPO_PATH"
    echo "  2. Copy existing skills to repository"
    echo "  3. Initialize Git and create initial commit"
    echo "  4. Create GitHub repository"
    echo "  5. Push to GitHub"
    echo "  6. Create symlink: $SKILLS_DIR -> $REPO_PATH"
    echo ""

    if ! ask_yes_no "Continue with this plan?" "y"; then
        echo "Aborted."
        exit 0
    fi

    # Create repository directory
    print_step "Creating repository directory..."
    mkdir -p "$REPO_PATH"
    print_success "Directory created: $REPO_PATH"

    # Copy skills
    print_step "Copying skills to repository..."
    if [ "$SKILL_COUNT" -gt 0 ]; then
        cp -r "$SKILLS_DIR"/* "$REPO_PATH/" || true
        print_success "Skills copied"
    fi

    # Create README
    print_step "Creating README..."
    cat > "$REPO_PATH/README.md" << 'EOF'
# My Claude Code Skills

Personal collection of Claude Code skills, synced across machines using Git.

## Syncing

Use the `skills-sync` skill to manage synchronization:

```bash
/skills-sync action=status                          # Check status
/skills-sync action=pull                            # Pull latest changes
/skills-sync action=push message="Your message"     # Push changes
```

## Skills

EOF

    # List skills in README
    if [ "$SKILL_COUNT" -gt 0 ]; then
        for skill_dir in "$REPO_PATH"/*/; do
            if [ -f "${skill_dir}skill.json" ]; then
                skill_name=$(basename "$skill_dir")
                echo "- \`$skill_name\`" >> "$REPO_PATH/README.md"
            fi
        done
    fi

    # Create .gitignore
    cat > "$REPO_PATH/.gitignore" << 'EOF'
# Python
*.pyc
__pycache__/
*.pyo
*.pyd
.Python
*.so
*.egg
*.egg-info/
dist/
build/
.venv/
venv/
ENV/

# Editor
.vscode/
.idea/
*.swp
*.swo
*~
.DS_Store

# Logs
*.log

# Temporary
tmp/
temp/
EOF

    print_success "Repository files created"

    # Initialize Git
    print_step "Initializing Git repository..."
    cd "$REPO_PATH"
    git init
    git checkout -b main 2>/dev/null || git checkout main
    git add .
    git commit -m "Initial commit: Claude Code skills collection"
    print_success "Git repository initialized"

    # Create GitHub repository
    if [ "$HAS_GH" = true ]; then
        echo ""
        if ask_yes_no "Create GitHub repository now?" "y"; then
            print_step "Creating GitHub repository..."

            VISIBILITY=$(ask_input "Repository visibility (public/private)" "public")

            if gh repo create "$REPO_NAME" "--$VISIBILITY" --source=. --remote=origin --push; then
                print_success "GitHub repository created and pushed"
                GITHUB_URL=$(git remote get-url origin)
                print_info "Repository URL: $GITHUB_URL"
            else
                print_error "Failed to create GitHub repository"
                print_info "You can create it manually later with:"
                echo "    cd $REPO_PATH"
                echo "    gh repo create $REPO_NAME --public"
                echo "    git remote add origin https://github.com/YOUR_USERNAME/$REPO_NAME.git"
                echo "    git push -u origin main"
            fi
        fi
    else
        print_warning "GitHub CLI not available"
        print_info "Create repository manually:"
        echo "  1. Go to https://github.com/new"
        echo "  2. Create repository named: $REPO_NAME"
        echo "  3. Then run:"
        echo "       cd $REPO_PATH"
        echo "       git remote add origin https://github.com/YOUR_USERNAME/$REPO_NAME.git"
        echo "       git push -u origin main"
        echo ""
        read -p "Press Enter to continue after creating the repository..."
    fi

    # Backup and create symlink
    print_step "Setting up symlink..."

    if [ ! -L "$SKILLS_DIR" ]; then
        BACKUP_PATH="$SKILLS_DIR.backup.$(date +%Y%m%d_%H%M%S)"
        print_step "Backing up original skills directory to: $BACKUP_PATH"
        mv "$SKILLS_DIR" "$BACKUP_PATH"
        print_success "Backup created"
    else
        rm "$SKILLS_DIR"
    fi

    ln -s "$REPO_PATH" "$SKILLS_DIR"
    print_success "Symlink created: $SKILLS_DIR -> $REPO_PATH"

    print_header "Setup Complete! 🎉"
    echo "Your skills are now managed by Git and synced to GitHub."
    echo ""
    echo "Next steps:"
    echo "  1. Test the sync: /skills-sync action=status"
    echo "  2. On other machines, run this script and choose option 2"
    echo ""
    echo "Usage:"
    echo "  /skills-sync action=status  # Check sync status"
    echo "  /skills-sync action=pull    # Pull latest changes"
    echo "  /skills-sync action=push    # Push your changes"
    echo ""

fi
