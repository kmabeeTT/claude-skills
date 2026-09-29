#!/usr/bin/env bash
# Arm a Telegram notification for the next time Claude Code finishes a turn.
# Usage: arm.sh [--sticky] "what is being waited on"

set -euo pipefail

FLAG_FILE="${TELEGRAM_NOTIFY_FLAG:-$HOME/.claude/telegram-notify.flag}"
MODE="once"

if [[ "${1:-}" == "--sticky" ]]; then
    MODE="sticky"
    shift
fi

LABEL="${1:-Task finished}"

mkdir -p "$(dirname "$FLAG_FILE")"
{
    echo "MODE=${MODE}"
    echo "CWD=${PWD}"
    echo "ARMED_AT=$(date '+%Y-%m-%d %H:%M:%S')"
    echo "LABEL<<END"
    echo "${LABEL}"
    echo "END"
} > "$FLAG_FILE"
chmod 600 "$FLAG_FILE"

echo "Telegram notification armed (${MODE}): ${LABEL}"
