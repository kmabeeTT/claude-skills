# Telegram Notify

Get a Telegram message when Claude Code finishes a long-running task — but only
when you ask for one.

## Why a hook and not just a skill

A skill is model-invoked: Claude has to remember to send the message as its last
action. On exactly the long, compacted sessions where you most want a ping, that
is where it silently fails.

So this splits the job:

- **The skill arms** a one-shot flag when you ask to be notified.
- **A `Stop` hook delivers**, firing deterministically when the turn ends.

## Files

| File | Purpose |
|---|---|
| `SKILL.md` | Skill definition and instructions for Claude |
| `arm.sh` | Arm a notification (`--sticky` for repeated pings) |
| `disarm.sh` | Cancel a pending notification |
| `stop-hook.sh` | Stop hook; sends and clears the flag |
| `notify-telegram.sh` | Standalone sender, usable from any script |

## Usage

Just ask, in plain English:

> run the full test suite and telegram me when it's done

Or drive it manually:

```bash
./arm.sh "Full test suite"          # one-shot
./arm.sh --sticky "Long session"    # until disarmed
./disarm.sh
./notify-telegram.sh "Ad-hoc message"
```

## Credentials

Stored **outside this repo** at `~/.tt-telegram.env`, mode `600`:

```
TELEGRAM_BOT_TOKEN=<from @BotFather>
TELEGRAM_CHAT_ID=<numeric; from @userinfobot>
```

```bash
chmod 600 ~/.tt-telegram.env
```

Point elsewhere with `TELEGRAM_ENV_FILE=/path/to/file`.

Never commit tokens to this repository.

## Setup

Register the Stop hook with `./install-hook.sh` (writes to
`${CLAUDE_CONFIG_DIR:-~/.claude}/settings.json`) — see the Setup section of
`SKILL.md`. Logs land in `~/.claude/telegram-notify.log`.
