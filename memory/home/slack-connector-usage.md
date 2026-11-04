---
name: slack-connector-usage
description: "How Kyle uses the claude.ai Slack connector vs Telegram, plus self-DM ID and the auto footer"
metadata:
  node_type: memory
  type: reference
  originSessionId: decb66c0-f367-4d6d-8715-cf7be0f0de53
  modified: 2026-10-29T19:15:00.614Z
---

- The claude.ai Slack connector is live in Claude Code (tools `mcp__claude_ai_Slack__*`). Kyle's user ID is UT1JL93D5; his self-DM channel is DSZ9BLRK6.
- Kyle talks to Claude through the Telegram channel plugin (`claude --channels plugin:telegram@claude-plugins-official`), not Slack. Slack is for sending updates to teammates and reading threads.
- `slack_send_message` adds a "Sent using @claude" footer that can't be turned off. If he wants no footer, save a draft (`slack_send_message_draft`) for him to send.

**Why:** Decided on 2026-10-29 after a live Slack channel turned out to need a Slack app and probably admin approval.
**How to apply:** Before sending a Slack message to anyone else, show Kyle the exact text and get his OK. Don't propose Slack as a chat channel with Claude again unless he brings it up.
