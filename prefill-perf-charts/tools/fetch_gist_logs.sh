#!/bin/bash
# fetch_gist_logs.sh GIST_ID_OR_URL OUT_DIR
# Clones a gist into OUT_DIR/gist and decodes every *.tar.gz.b64 (or *.tar.gz) in it into its
# own OUT_DIR/<name>/ directory. Prints the directories that hold [traced_perf] logs.
# OUT_DIR must not exist yet (no rm here; pick a fresh timestamped path).
set -euo pipefail
id="${1##*/}"; out="$2"
[ -e "$out" ] && { echo "$out exists; use a fresh path" >&2; exit 2; }
mkdir -p "$out"
GIT_TERMINAL_PROMPT=0 git -c credential.helper= -c "credential.helper=!gh auth git-credential" \
    clone -q "https://gist.github.com/$id.git" "$out/gist"
for f in "$out"/gist/*.tar.gz.b64 "$out"/gist/*.tar.gz; do
    [ -e "$f" ] || continue
    name=$(basename "$f"); name=${name%.b64}; name=${name%.tar.gz}
    mkdir -p "$out/$name"
    case "$f" in
        *.b64) base64 -d "$f" | tar -xz -C "$out/$name" ;;
        *)     tar -xzf "$f" -C "$out/$name" ;;
    esac
    echo "decoded $f -> $out/$name"
done
echo; echo "dirs with [traced_perf] logs:"
grep -rl --include='*.log' '\[traced_perf\] chunk' "$out" | xargs -r -n1 dirname | sort -u
