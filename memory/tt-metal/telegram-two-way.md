---
name: telegram-two-way
description: Kyle answers questions over Telegram; read replies with ~/scripts/tg_read.sh (send with runs_ringsdpa/tg_send.sh)
metadata:
  node_type: memory
  type: reference
  originSessionId: 5ecff3cb-0b03-4794-9f83-de74c864ae69
  modified: 2026-10-04T02:54:24.416Z
---

Telegram is two-way since 2026-10-04. Send: `/data/kmabee/runs_ringsdpa/tg_send.sh "msg"`. Read Kyle's replies: `~/scripts/tg_read.sh` (prints `<UTC time> <text>` per new message from TELEGRAM_CHAT_ID and consumes them via `~/.tt-telegram.offset`; `--peek` shows without consuming, `--wait N` long-polls). Both read `~/.tt-telegram.env` and never print the token. The reader lives on `/home`, so it works when the /data quota is full.

**How to apply:** when a question is pending to Kyle (approval to delete, which experiment next), Telegram it and poll `tg_read.sh` (e.g. a background `--wait 1800` loop) instead of stopping. A reply there is Kyle's real answer, the same as a chat message. Kyle asked for this on 2026-10-04: "let me answer things in the future". Related: [[session-state-1003]].
