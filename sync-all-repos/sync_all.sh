#!/usr/bin/env bash
# sync_all.sh - commit and push every git repo under $HOME before moving machines.
#
# Usage:
#   sync_all.sh                 # dry run: one line per repo, what would happen (default)
#   sync_all.sh --apply [-m MSG]   # commit + push personal repos, push shared repos' local commits
#   sync_all.sh --apply --no-shared  # leave shared repos alone
#
# Repos: every .git (dir or worktree file) under $HOME to depth 3, skipping .cache/.local, plus any
# paths in $SYNC_EXTRA (space-separated).
#
# Personal repo = origin is github.com:$SYNC_OWNER/* (default kmabeeTT). For those:
#   - stage everything (git add -A), commit with MSG (default "sync: <host> <UTC time>"), push.
#   - refuse NEW untracked files over $SYNC_MAX_MB (default 50) or that look like secrets
#     (*.env, *.pem, *.key, id_rsa*, *credentials*, *token*). Already-tracked files are not checked.
#   - behind upstream: pull --rebase first; a conflict aborts the rebase and the repo is reported.
# Shared repo (any other origin, e.g. tenstorrent/tt-metal): never commits. Pushes existing local
#   commits only as a fast-forward of the current branch, and only if no open non-draft PR uses it.
#
# Never force-pushes, never skips hooks. Skips detached HEAD, a rebase/merge in progress, no origin.
# Exit 1 if any repo was left unsynced.

set -uo pipefail

APPLY=0
SHARED=1
MSG=""
OWNER="${SYNC_OWNER:-kmabeeTT}"
MAX_MB="${SYNC_MAX_MB:-50}"
while [ $# -gt 0 ]; do
    case "$1" in
        --apply) APPLY=1 ;;
        --no-shared) SHARED=0 ;;
        -m) MSG="$2"; shift ;;
        -h|--help) sed -n '2,25p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *) echo "unknown option: $1" >&2; exit 2 ;;
    esac
    shift
done
[ -n "$MSG" ] || MSG="sync: $(hostname -s) $(date -u '+%Y-%m-%d %H:%M UTC')"

repos=$( { find "$HOME" -maxdepth 3 \( -path "$HOME/.cache" -o -path "$HOME/.local" \) -prune -o \
               -name .git -print 2>/dev/null | xargs -r -n1 dirname
           for p in ${SYNC_EXTRA:-}; do echo "$p"; done; } | sort -u)


# push <repo> <branch> [-u]: origin first; if SSH is refused, retry over HTTPS with gh's token
# (same repo, remotes unchanged). Error text lands in $ERRF.
ERRF=$(mktemp)
push() {
    local r="$1" br="$2"; shift 2
    git -C "$r" push -q "$@" origin "$br" 2>"$ERRF" && return 0
    grep -q "Permission denied (publickey)\|Could not read from remote" "$ERRF" || return 1
    local url https
    url=$(git -C "$r" remote get-url origin)
    https=$(echo "$url" | sed -E 's#^git@github.com:#https://github.com/#; s#^ssh://git@github.com/#https://github.com/#')
    [ "$https" != "$url" ] && gh auth status >/dev/null 2>&1 || return 1
    git -C "$r" -c credential.helper= -c 'credential.helper=!gh auth git-credential' push -q "$https" "$br" 2>"$ERRF" \
        && { git -C "$r" fetch -q origin "$br" 2>/dev/null || git -C "$r" update-ref "refs/remotes/origin/$br" HEAD; VIA=" via https"; return 0; }
    return 1
}

FAIL=0
row() { printf '%-28s %-34s %s\n' "$1" "$2" "$3"; }
row REPO BRANCH RESULT

for r in $repos; do
    name="~${r#"$HOME"}"
    g() { git -C "$r" "$@"; }
    br=$(g branch --show-current 2>/dev/null)
    url=$(g remote get-url origin 2>/dev/null)
    gd=$(g rev-parse --git-dir 2>/dev/null)
    if [ -z "$url" ]; then row "$name" "-" "SKIP no origin"; FAIL=1; continue; fi
    if [ -z "$br" ]; then row "$name" "(detached)" "SKIP detached HEAD"; FAIL=1; continue; fi
    if [ -d "$gd/rebase-merge" ] || [ -d "$gd/rebase-apply" ] || [ -f "$gd/MERGE_HEAD" ]; then
        row "$name" "$br" "SKIP rebase/merge in progress"; FAIL=1; continue
    fi
    personal=0
    case "$url" in *github.com[:/]"$OWNER"/*) personal=1 ;; esac

    g fetch -q origin "$br" 2>/dev/null
    up="origin/$br"
    has_up=0; g rev-parse -q --verify "$up" >/dev/null && has_up=1
    dirty=$(g status --porcelain | wc -l)

    if [ "$personal" -eq 0 ]; then
        ahead=0; [ "$has_up" -eq 1 ] && ahead=$(g rev-list --count "$up..HEAD")
        note=""; [ "$dirty" -gt 0 ] && note=" ($dirty uncommitted entries left as is)"
        if [ "$SHARED" -eq 0 ]; then row "$name" "$br" "shared, left alone$note"; continue; fi
        if [ "$has_up" -eq 1 ] && [ "$ahead" -eq 0 ]; then row "$name" "$br" "shared, up to date$note"; continue; fi
        if [ "$has_up" -eq 1 ] && ! g merge-base --is-ancestor "$up" HEAD; then
            row "$name" "$br" "shared, DIVERGED from $up, not pushed$note"; FAIL=1; continue
        fi
        repo_slug=$(echo "$url" | sed -E 's#.*github.com[:/]##; s#\.git$##')
        pr=$(gh pr list -R "$repo_slug" --head "$br" --state open --json number,isDraft \
             --jq '[.[] | select(.isDraft | not)] | length' 2>/dev/null || echo "?")
        if [ "$pr" != "0" ]; then
            row "$name" "$br" "shared, $ahead local commits NOT pushed: open PR (or gh failed: $pr)$note"; FAIL=1; continue
        fi
        if [ "$APPLY" -eq 0 ]; then row "$name" "$br" "shared, would push ${ahead:-new branch} commits$note"; continue; fi
        VIA=""
        if push "$r" "$br"; then
            row "$name" "$br" "shared, pushed ${ahead} commits$VIA$note"
        else
            row "$name" "$br" "shared, PUSH FAILED: $(tail -1 "$ERRF")"; FAIL=1
        fi
        continue
    fi

    # personal repo: vet new untracked files
    bad=""
    while IFS= read -r -d '' f; do
        p="$r/$f"
        sz=$(( $(stat -c %s "$p" 2>/dev/null || echo 0) / 1048576 ))
        base=$(basename "$f")
        if [ "$sz" -ge "$MAX_MB" ]; then bad="$bad $f(${sz}MB)"; continue; fi
        case "$base" in
            *.env|*.pem|*.key|id_rsa*|id_ed25519*|*credentials*|*token*) bad="$bad $f(secret?)" ;;
        esac
    done < <(g ls-files -z --others --exclude-standard)
    if [ -n "$bad" ]; then row "$name" "$br" "SKIP, refusing new files:$bad"; FAIL=1; continue; fi

    ahead=0; behind=0
    if [ "$has_up" -eq 1 ]; then
        ahead=$(g rev-list --count "$up..HEAD"); behind=$(g rev-list --count "HEAD..$up")
    fi
    plan="$dirty changed, $ahead ahead, $behind behind"
    if [ "$dirty" -eq 0 ] && [ "$ahead" -eq 0 ] && [ "$behind" -eq 0 ] && [ "$has_up" -eq 1 ]; then
        row "$name" "$br" "up to date"; continue
    fi
    if [ "$APPLY" -eq 0 ]; then row "$name" "$br" "would sync ($plan)"; continue; fi

    if [ "$dirty" -gt 0 ]; then
        g add -A && g commit -q -m "$MSG" || { row "$name" "$br" "COMMIT FAILED ($plan)"; FAIL=1; continue; }
    fi
    if [ "$behind" -gt 0 ]; then
        if ! g pull -q --rebase origin "$br" 2>"$ERRF"; then
            g rebase --abort 2>/dev/null
            row "$name" "$br" "REBASE CONFLICT, committed locally, not pushed"; FAIL=1; continue
        fi
    fi
    VIA=""
    if push "$r" "$br" -u; then
        row "$name" "$br" "pushed ($plan)$VIA"
    else
        row "$name" "$br" "PUSH FAILED: $(tail -1 "$ERRF")"; FAIL=1
    fi
done
rm -f "$ERRF"
exit $FAIL
