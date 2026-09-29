---
name: telegram-notify
description: This skill should be used when the user asks to "telegram me when done", "notify me when this finishes", "ping me when it's complete", "text me when the build is done", "let me know when you finish", "send me a telegram", or otherwise asks to be alerted away from the terminal when a long-running Claude Code task completes.
version: 1.0.0
---

# Telegram Notify

Send the user a Telegram message when Claude Code finishes a turn, but only when
they have asked to be notified.

Delivery is handled by a `Stop` hook rather than by Claude directly. Claude only
*arms* the notification; the hook guarantees it is actually sent, even if the
session is compacted or ends unexpectedly.

## When to Use This Skill

Use this skill when the user asks to be alerted once something finishes, for example:
- "run the full test suite and telegram me when it's done"
- "notify me when this finishes, I'm stepping out"
- "ping me on telegram when the build completes"

Do **not** arm a notification for ordinary short tasks the user is watching in
real time. This is for work they are walking away from.

## How It Works

1. Claude runs `arm.sh` with a short description of the task.
2. Claude does the actual work as normal.
3. When the turn ends, the `Stop` hook fires, finds the armed flag, sends the
   Telegram message, and clears the flag.

The flag lives at `~/.claude/telegram-notify.flag` (mode 600).

## Available Actions

### arm
Arm a one-shot notification. Run this **as part of starting the requested work**,
not at the very end — the hook handles delivery.

```bash
~/claude-skills/telegram-notify/arm.sh "Full test suite on main"
```

### arm (sticky)
Notify on *every* turn end until explicitly disarmed. Use only when the user asks
to be pinged repeatedly, such as during a long back-and-forth session while away.

```bash
~/claude-skills/telegram-notify/arm.sh --sticky "Long refactor session"
```

### disarm
Cancel a pending notification.

```bash
~/claude-skills/telegram-notify/disarm.sh
```

### send directly
Send a message immediately, without involving the hook. Useful for a mid-task
checkpoint or from any other script.

```bash
~/claude-skills/telegram-notify/notify-telegram.sh "Checkpoint: migration step 3 done"
```

## Instructions for Claude

- Arm the notification **early**, right when you begin the long-running work, and
  pass a short label naming the task. Do not wait until the end.
- A `Stop` hook fires whenever you hand control back — including when you stop to
  ask a clarifying question. That is usually desirable, since the user is away and
  needs to know you are blocked.
- Tell the user plainly that the notification is armed.
- If the user says to cancel, stop, or that they are back at the keyboard, run
  `disarm.sh`.
- Never echo the bot token or chat ID into the transcript.

## Credentials

Read from `~/.tt-telegram.env` (mode 600, **outside** this repo):

```
TELEGRAM_BOT_TOKEN=<from @BotFather>
TELEGRAM_CHAT_ID=<numeric; from @userinfobot>
```

Override the location with the `TELEGRAM_ENV_FILE` environment variable.

Never commit credentials to this repository.

## Setup

The `Stop` hook must be registered in the user settings file,
`${CLAUDE_CONFIG_DIR:-~/.claude}/settings.json` (on boxes that set
`CLAUDE_CONFIG_DIR`, `~/.claude/settings.json` is **not** read). Run once per machine:

```bash
~/claude-skills/telegram-notify/install-hook.sh
```

It is idempotent, keeps every other setting, and replaces any older registration of
this hook (such as a hardcoded `/Users/...` path). It writes:

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "$HOME/claude-skills/telegram-notify/stop-hook.sh",
            "async": true
          }
        ]
      }
    ]
  }
}
```

Hook commands run through a shell, so `$HOME` resolves on both macOS and Linux. A
session that started before the hook was added picks it up after opening `/hooks`
once or restarting.

## Troubleshooting

Delivery attempts are logged to `~/.claude/telegram-notify.log`.

- **Nothing sent:** check the flag file exists after arming, and that the hook is
  registered: `jq .hooks.Stop "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/settings.json"`
  (re-run `install-hook.sh` if not).
- **`SEND FAILED` in the log:** credentials are wrong, expired, or the bot was
  never started by the user in Telegram. Send a test with `notify-telegram.sh`.
