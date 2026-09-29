#!/usr/bin/env bash
# Cancel a pending Telegram notification.

set -euo pipefail

FLAG_FILE="${TELEGRAM_NOTIFY_FLAG:-$HOME/.claude/telegram-notify.flag}"

if [[ -f "$FLAG_FILE" ]]; then
    rm -f "$FLAG_FILE"
    echo "Telegram notification disarmed."
else
    echo "Nothing was armed."
fi
