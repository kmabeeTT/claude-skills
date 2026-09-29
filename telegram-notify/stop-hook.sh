#!/usr/bin/env bash
# Claude Code Stop hook: deliver a Telegram message if one was armed.
# Silent no-op when nothing is armed. Never fails the turn.

set -uo pipefail

FLAG_FILE="${TELEGRAM_NOTIFY_FLAG:-$HOME/.claude/telegram-notify.flag}"
SENDER="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/notify-telegram.sh"
LOG_FILE="$HOME/.claude/telegram-notify.log"

# Nothing armed: exit quietly. This is the common case.
[[ -f "$FLAG_FILE" ]] || exit 0

MODE="once"
CWD=""
ARMED_AT=""
LABEL=""
in_label=0

while IFS= read -r line; do
    if [[ $in_label -eq 1 ]]; then
        [[ "$line" == "END" ]] && { in_label=0; continue; }
        LABEL+="${LABEL:+$'\n'}${line}"
        continue
    fi
    case "$line" in
        MODE=*)     MODE="${line#MODE=}" ;;
        CWD=*)      CWD="${line#CWD=}" ;;
        ARMED_AT=*) ARMED_AT="${line#ARMED_AT=}" ;;
        "LABEL<<END") in_label=1 ;;
    esac
done < "$FLAG_FILE"

# One-shot: clear the flag first so a send failure cannot cause a repeat loop.
[[ "$MODE" == "sticky" ]] || rm -f "$FLAG_FILE"

MESSAGE="✅ Claude Code finished

${LABEL:-Task finished}

Dir: ${CWD:-unknown}
Started: ${ARMED_AT:-unknown}
Finished: $(date '+%Y-%m-%d %H:%M:%S')"

if "$SENDER" "$MESSAGE" 2>>"$LOG_FILE"; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') sent (${MODE}): ${LABEL}" >> "$LOG_FILE"
else
    echo "$(date '+%Y-%m-%d %H:%M:%S') SEND FAILED: ${LABEL}" >> "$LOG_FILE"
fi

exit 0
