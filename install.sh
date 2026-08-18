#!/usr/bin/env bash
# install.sh - wire this checkout into Claude Code on the current machine.
#
# Creates the two symlinks this repo's layout depends on:
#   ~/.claude/skills   -> this repo        (Claude Code loads skills from here)
#   ~/.claude/CLAUDE.md -> ./CLAUDE.md     (global, always-loaded working notes)
#
# Idempotent: re-running when both links are already correct changes nothing. Never
# deletes real files or directories - anything in the way is moved aside with a .bak
# suffix, and only when --force says so.
#
# Usage:
#   ./install.sh                # install both links
#   ./install.sh --dry-run      # show what would happen, touch nothing
#   ./install.sh --force        # replace a wrong link, or move a real dir/file aside
#   ./install.sh --skip-claude-md   # skills only, leave global CLAUDE.md alone
#
# Honors CLAUDE_CONFIG_DIR if set (defaults to ~/.claude).

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
DRY_RUN=0
FORCE=0
SKIP_CLAUDE_MD=0
STAMP="$(date +%Y%m%d-%H%M%S)"
FAILED=0

while [ $# -gt 0 ]; do
    case "$1" in
        --dry-run)        DRY_RUN=1 ;;
        --force)          FORCE=1 ;;
        --skip-claude-md) SKIP_CLAUDE_MD=1 ;;
        -h|--help)        sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *) echo "unknown option: $1 (try --help)" >&2; exit 2 ;;
    esac
    shift
done

say()  { printf '%s\n' "$*"; }
run()  { if [ "$DRY_RUN" -eq 1 ]; then say "    would run: $*"; else "$@"; fi; }

# link <target> <source>
link() {
    local target="$1" source="$2" name="${1/#$HOME/~}"

    if [ -L "$target" ]; then
        local current
        current="$(readlink -f "$target" 2>/dev/null || true)"
        if [ "$current" = "$(readlink -f "$source")" ]; then
            say "  ok       $name -> already correct"
            return 0
        fi
        if [ "$FORCE" -eq 0 ]; then
            say "  SKIP     $name is a symlink to something else:"
            say "             $current"
            say "           re-run with --force to repoint it"
            FAILED=1
            return 0
        fi
        say "  repoint  $name (was $current)"
        run rm -f "$target"
    elif [ -e "$target" ]; then
        # A real file or directory. Could be someone's actual skills, or notes they
        # care about, so it is never removed - only moved aside, and only on --force.
        if [ "$FORCE" -eq 0 ]; then
            say "  SKIP     $name already exists and is NOT a symlink"
            say "           nothing was touched. Move it aside yourself, or re-run with"
            say "           --force to have it renamed to $name.bak.$STAMP"
            FAILED=1
            return 0
        fi
        say "  backup   $name -> $name.bak.$STAMP"
        run mv "$target" "$target.bak.$STAMP"
    else
        say "  link     $name -> $source"
    fi

    run mkdir -p "$(dirname "$target")"
    run ln -s "$source" "$target"
}

say "claude-skills installer"
say "  repo:   $REPO_DIR"
say "  config: ${CLAUDE_DIR/#$HOME/~}"
[ "$DRY_RUN" -eq 1 ] && say "  (dry run - nothing will be modified)"
say ""

link "$CLAUDE_DIR/skills" "$REPO_DIR"

if [ "$SKIP_CLAUDE_MD" -eq 1 ]; then
    say "  skipped  global CLAUDE.md (--skip-claude-md)"
elif [ -f "$REPO_DIR/CLAUDE.md" ]; then
    link "$CLAUDE_DIR/CLAUDE.md" "$REPO_DIR/CLAUDE.md"
else
    say "  n/a      no CLAUDE.md in this checkout"
fi

say ""
say "skills discovered:"
found=0
for d in "$REPO_DIR"/*/; do
    if [ -f "$d/SKILL.md" ]; then
        say "  - $(basename "$d")"
        found=$((found + 1))
    fi
done
[ "$found" -eq 0 ] && say "  (none - expected directories containing a SKILL.md)"

say ""
if [ "$FAILED" -ne 0 ]; then
    say "Finished with items skipped - see SKIP above. Nothing was destroyed."
    exit 1
fi
if [ "$DRY_RUN" -eq 1 ]; then
    say "Dry run complete. Re-run without --dry-run to apply."
    exit 0
fi
say "Done. $found skill(s) available; restart Claude Code (or start a new session) to pick them up."
say ""
say "Optional shell aliases (edits your shell rc):  ./setup-aliases.sh"
say "Keeping machines in sync:                      say \"sync my skills\", or skills-sync/sync.sh status"
