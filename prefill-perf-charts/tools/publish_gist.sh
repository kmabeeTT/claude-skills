#!/bin/bash
# publish_gist.sh --dir DIR --readme NAME.md --desc "description" [--public]
#
# Publishes DIR as a new gist (secret unless --public) with the README listed first:
#  - the README is uploaded as 0_<NAME>.md; gists list files by name, and "0_" sorts first
#    whether the ordering is case-sensitive or not ("chart1_..." vs "GEMMA4_..." is not).
#  - gh gist create refuses binary files, so the gist is created from the text files
#    (md/csv/py/json/sh/txt), then the PNGs and any *.tar.gz log archives are added with a git push.
#  - GIST_ID in the README is replaced with the new id, so image links of the form
#    https://gist.githubusercontent.com/<user>/GIST_ID/raw/<file>.png resolve.
#  - gh is used as the git credential helper for this clone/push only; the global git
#    config is not touched (gh's git protocol may be ssh).
# Then verifies: every PNG URL returns 200 image/png, and the README is the first file on the page.
set -euo pipefail
pub=""; dir=""; readme=""; desc=""
while [ $# -gt 0 ]; do
    case "$1" in
        --dir) dir="$2"; shift ;; --readme) readme="$2"; shift ;; --desc) desc="$2"; shift ;;
        --public) pub="--public" ;; *) echo "unknown arg $1" >&2; exit 2 ;;
    esac; shift
done
[ -d "$dir" ] && [ -f "$dir/$readme" ] && [ -n "$desc" ] || { sed -n '2,4p' "$0"; exit 2; }
gh auth status >/dev/null 2>&1 || { echo "gh is not logged in: run '! gh auth login --insecure-storage'" >&2; exit 3; }
user=$(gh api user --jq .login)
first="0_${readme#0_}"
stage=$(mktemp -d "${TMPDIR:-/tmp}/gist_stage_XXXX")
cp "$dir/$readme" "$stage/$first"
for f in "$dir"/*; do
    b=$(basename "$f")
    [ "$b" = "$readme" ] && continue
    case "$b" in *.csv|*.py|*.json|*.sh|*.txt|*.md) cp "$f" "$stage/" ;; esac
done
url=$(cd "$stage" && gh gist create $pub -d "$desc" "$first" $(cd "$stage" && ls | grep -vx "$first") | tail -1)
id="${url##*/}"
echo "created $url"
git -c credential.helper= -c "credential.helper=!gh auth git-credential" clone -q "https://gist.github.com/$id.git" "$stage/repo"
cp "$dir"/*.png "$dir"/*.tar.gz "$stage/repo/" 2>/dev/null || true
sed -i "s/GIST_ID/$id/g; s#gist.githubusercontent.com/[A-Za-z0-9-]*/$id#gist.githubusercontent.com/$user/$id#g" "$stage/repo/$first"
(cd "$stage/repo" && git add -A && git commit -qm "Add charts" &&
    git -c credential.helper= -c "credential.helper=!gh auth git-credential" push -q)
echo "pushed charts and archives"
bad=0
for p in "$dir"/*.png; do
    [ -e "$p" ] || continue
    r=$(curl -sL -o /dev/null -w '%{http_code} %{content_type}' "https://gist.githubusercontent.com/$user/$id/raw/$(basename "$p")")
    [ "$r" = "200 image/png" ] || { echo "BAD $(basename "$p"): $r"; bad=1; }
done
grep -q "GIST_ID" "$stage/repo/$first" && { echo "BAD: GIST_ID placeholder left in README"; bad=1; }
top=$(curl -sL "$url" | grep -o 'id="file-[a-z0-9_-]*"' | head -1)
echo "first file on the gist page: $top"
case "$top" in *file-0_*) ;; *) echo "WARN: README is not the first file"; bad=1 ;; esac
[ $bad -eq 0 ] && echo "OK $url" || { echo "published with problems: $url"; exit 1; }
