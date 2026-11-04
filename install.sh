#!/usr/bin/env bash
# install.sh - wire this checkout into Claude Code on the current machine.
#
# Creates the symlinks this repo's layout depends on, in each config dir:
#   <config>/skills                  -> this repo        (Claude Code loads skills from here)
#   <config>/CLAUDE.md               -> ./CLAUDE.md      (global, always-loaded working notes)
#   <config>/projects/<key>/memory   -> ./memory/<dir>   (per-project memory, map in memory/PROJECTS)
#
# Config dirs: $CLAUDE_CONFIG_DIR (if set) and ~/.claude, or just the one given with --config.
#
# Idempotent: re-running when the links are already correct changes nothing. Never deletes real
# files or directories - anything in the way is moved aside with a .bak suffix, and only when
# --force says so. A real memory dir is first merged into the repo dir (new notes copied, new
# MEMORY.md index lines appended); if a note of the same name differs, nothing is moved for that
# project and it is reported as a CONFLICT to resolve by hand.
#
# Usage:
#   ./install.sh                # install all links
#   ./install.sh --dry-run      # show what would happen, touch nothing
#   ./install.sh --force        # replace a wrong link, or merge + move a real dir/file aside
#   ./install.sh --skip-claude-md   # leave global CLAUDE.md alone
#   ./install.sh --skip-memory      # leave project memory dirs alone
#   ./install.sh --config DIR       # only this config dir

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIRS=()
DRY_RUN=0
FORCE=0
SKIP_CLAUDE_MD=0
SKIP_MEMORY=0
STAMP="$(date +%Y%m%d-%H%M%S)"
FAILED=0

while [ $# -gt 0 ]; do
    case "$1" in
        --dry-run)        DRY_RUN=1 ;;
        --force)          FORCE=1 ;;
        --skip-claude-md) SKIP_CLAUDE_MD=1 ;;
        --skip-memory)    SKIP_MEMORY=1 ;;
        --config)         shift; CONFIG_DIRS+=("${1:?--config needs a directory}") ;;
        -h|--help)        sed -n '2,25p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
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

# merge_into <real memory dir> <repo memory dir>: copy what the repo copy lacks. Sets CONFLICT=1
# when a note of the same name has different content (the caller then leaves that dir alone).
merge_into() {
    local src="$1" dest="$2" f base line
    # Pass 1: find conflicts before copying anything, so a conflict leaves the repo dir untouched.
    for f in "$src"/*; do
        [ -e "$f" ] || continue
        base="$(basename "$f")"
        [ "$base" = MEMORY.md ] && continue
        if [ -e "$dest/$base" ] && ! cmp -s "$f" "$dest/$base"; then
            say "  CONFLICT $base differs between $src and $dest"
            CONFLICT=1
        fi
    done
    [ "$CONFLICT" -eq 0 ] || return 0
    for f in "$src"/*; do
        [ -e "$f" ] || continue
        base="$(basename "$f")"
        if [ "$base" = MEMORY.md ] && [ -f "$dest/MEMORY.md" ]; then
            while IFS= read -r line; do
                [ -n "$line" ] || continue
                grep -qxF -- "$line" "$dest/MEMORY.md" && continue
                say "           index + ${line:0:90}"
                [ "$DRY_RUN" -eq 1 ] || printf '%s\n' "$line" >> "$dest/MEMORY.md"
            done < "$f"
        elif [ ! -e "$dest/$base" ]; then
            say "           merge   $base"
            run cp -R "$f" "$dest/$base"   # no -p: some notes carry a foreign group
        fi
    done
}

# link_memory <project key> <dir under memory/>
link_memory() {
    local key="$1" dir="$2"
    local target="$CLAUDE_DIR/projects/$key/memory" src="$REPO_DIR/memory/$dir"
    if [ ! -d "$src" ]; then
        say "  create   memory/$dir/ (new in memory/PROJECTS)"
        run mkdir -p "$src"
        run touch "$src/MEMORY.md"
    fi
    if [ -d "$target" ] && [ ! -L "$target" ] && [ "$FORCE" -eq 1 ]; then
        CONFLICT=0
        say "  merge    ${target/#$HOME/~} into memory/$dir/"
        merge_into "$target" "$src"
        if [ "$CONFLICT" -ne 0 ]; then
            say "  SKIP     ${target/#$HOME/~} left in place: resolve the CONFLICT lines, then re-run"
            FAILED=1
            return 0
        fi
    fi
    link "$target" "$src"
}

install_into() {
    CLAUDE_DIR="$1"
    say "config: ${CLAUDE_DIR/#$HOME/~}"

    link "$CLAUDE_DIR/skills" "$REPO_DIR"

    if [ "$SKIP_CLAUDE_MD" -eq 1 ]; then
        say "  skipped  global CLAUDE.md (--skip-claude-md)"
    elif [ -f "$REPO_DIR/CLAUDE.md" ]; then
        link "$CLAUDE_DIR/CLAUDE.md" "$REPO_DIR/CLAUDE.md"
    else
        say "  n/a      no CLAUDE.md in this checkout"
    fi

    if [ "$SKIP_MEMORY" -eq 1 ]; then
        say "  skipped  project memory (--skip-memory)"
    elif [ -f "$REPO_DIR/memory/PROJECTS" ]; then
        local key dir rest
        while read -r key dir rest <&3; do
            case "$key" in ''|\#*) continue ;; esac
            if [ -z "$dir" ]; then say "  BAD LINE memory/PROJECTS: $key"; FAILED=1; continue; fi
            link_memory "$key" "$dir"
        done 3< "$REPO_DIR/memory/PROJECTS"
    fi
    say ""
}

say "claude-skills installer"
say "  repo:   $REPO_DIR"
[ "$DRY_RUN" -eq 1 ] && say "  (dry run - nothing will be modified)"
say ""

if [ "${#CONFIG_DIRS[@]}" -eq 0 ]; then
    [ -n "${CLAUDE_CONFIG_DIR:-}" ] && CONFIG_DIRS+=("$CLAUDE_CONFIG_DIR")
    [ "${CLAUDE_CONFIG_DIR:-}" = "$HOME/.claude" ] || CONFIG_DIRS+=("$HOME/.claude")
fi
for c in "${CONFIG_DIRS[@]}"; do install_into "$c"; done

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
