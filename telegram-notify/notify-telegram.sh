#!/usr/bin/env bash
# Send a Telegram message. Usable standalone or from the Stop hook.
# Usage: notify-telegram.sh "message text"
# Exits non-zero if Telegram rejects the message, not merely if curl fails.

set -euo pipefail

ENV_FILE="${TELEGRAM_ENV_FILE:-$HOME/.tt-telegram.env}"
MESSAGE="${1:?Usage: $0 <message>}"

if [[ ! -f "$ENV_FILE" ]]; then
    echo "ERROR: credentials file not found: $ENV_FILE" >&2
    exit 1
fi

# shellcheck disable=SC1090
source "$ENV_FILE"

if [[ -z "${TELEGRAM_BOT_TOKEN:-}" || -z "${TELEGRAM_CHAT_ID:-}" ]]; then
    echo "ERROR: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set in $ENV_FILE" >&2
    exit 1
fi

# --data-urlencode keeps newlines and special characters intact.
response=$(curl -s -m 15 -X POST \
    "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
    --data-urlencode "chat_id=${TELEGRAM_CHAT_ID}" \
    --data-urlencode "text=${MESSAGE}" 2>/dev/null) || {
    echo "ERROR: could not reach api.telegram.org" >&2
    exit 1
}

# Telegram returns HTTP 200 with {"ok":false,...} for bad tokens and chat ids,
# so the body must be checked rather than curl's exit status.
python3 - "$response" <<'PY'
import json, sys
try:
    d = json.loads(sys.argv[1])
except Exception:
    print("ERROR: unparseable response from Telegram", file=sys.stderr)
    sys.exit(1)
if not d.get("ok"):
    print("ERROR: Telegram rejected the message: %s %s"
          % (d.get("error_code", "?"), d.get("description", "")), file=sys.stderr)
    sys.exit(1)
PY
