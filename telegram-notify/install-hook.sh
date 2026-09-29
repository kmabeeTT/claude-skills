#!/usr/bin/env bash
# Register stop-hook.sh as an async Stop hook in the active Claude Code user
# settings. Idempotent; preserves every other setting. Works on macOS and Linux.
#
# Settings file: ${CLAUDE_CONFIG_DIR:-$HOME/.claude}/settings.json
# (CLAUDE_CONFIG_DIR moves the whole config dir, e.g. onto /data on shared boxes.)

set -euo pipefail
command -v jq >/dev/null || { echo "install-hook: jq is required" >&2; exit 1; }

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
SETTINGS="$CONFIG_DIR/settings.json"

# Hook commands run through a shell, so a literal $HOME resolves per machine.
# Use it when the skill sits at the conventional path; otherwise use this path.
if [[ "$SKILL_DIR" == "$HOME/claude-skills/telegram-notify" ]]; then
    CMD='$HOME/claude-skills/telegram-notify/stop-hook.sh'
else
    CMD="$SKILL_DIR/stop-hook.sh"
fi

mkdir -p "$CONFIG_DIR"
[[ -s "$SETTINGS" ]] || echo '{}' > "$SETTINGS"
jq -e . "$SETTINGS" >/dev/null || { echo "install-hook: $SETTINGS is not valid JSON" >&2; exit 1; }

# Drop any earlier registration of this hook (e.g. a hardcoded /Users/... path),
# then add the current one.
tmp="$(mktemp "$SETTINGS.XXXXXX")"
jq --arg cmd "$CMD" '
  .hooks //= {} |
  .hooks.Stop = (
    [ (.hooks.Stop // [])[]
      | .hooks |= map(select((.command // "") | endswith("telegram-notify/stop-hook.sh") | not))
      | select(.hooks | length > 0) ]
    + [ { hooks: [ { type: "command", command: $cmd, async: true } ] } ]
  )' "$SETTINGS" > "$tmp"
chmod --reference="$SETTINGS" "$tmp" 2>/dev/null || chmod 600 "$tmp"
mv "$tmp" "$SETTINGS"

echo "install-hook: Stop hook registered in $SETTINGS -> $CMD"
