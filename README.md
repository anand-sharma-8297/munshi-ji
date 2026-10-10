# Munshi Ji — a 24/7 personal AI agent on a spare laptop, driven from Telegram

Munshi Ji turns an old Ubuntu laptop into a personal assistant you talk to on Telegram (text or voice notes).
It runs [Claude Code](https://claude.com/claude-code) around the clock with two real, logged-in Chrome browsers
(personal + work), a scheduler, long-term memory and strict safety rules.

> *Munshi* (मुंशी) = the clerk who keeps the records, accounts and letters. That's the job.

## What it can do
- **Chat & voice on Telegram** — Hindi/English/Hinglish voice notes are transcribed (Groq Whisper) and answered.
- **Two isolated browsers** — a PERSONAL and a WORK Chrome, each its own profile/logins, driven via Playwright MCP.
- **Phone logins without sharing passwords** — `login-link.sh` gives you a one-time link (Tailscale only) that
  shows the agent's browser tab on your phone; you type the password yourself, it never passes through chat.
- **Scheduled jobs** that survive restarts (`schedule.sh` → crontab): daily digests, reminders, reports.
- **Memory** — `memory/` (profile, site playbooks, pending questions, daily journal) + per-topic `workflows/`.
- **Self-healing** — watchdog restarts a stuck session, nightly fresh context at 04:00, idle restart.
- **STOP button** — send `STOP` and a watcher interrupts the running task immediately.
- **Live steps** — optional italic progress message while it works.
- **Tap-to-select buttons**, `/new`, `/resume`, `/model`, `/info`, `/pending` … from the Telegram menu.
- **Power BI add-on (optional)** — DAX queries via service principal, dashboards built as code and published to a
  drafts-only workspace for review (`addons/powerbi/`).
- **Desktop control** — whole-screen screenshots and mouse/keyboard (`tools/desktop-shot`, `tools/desktop-control`).

## Safety model (in `templates/agent-instructions.md`)
- Anything outward-facing or irreversible (send, post, buy, delete, publish, settings) needs your explicit "yes"
  in a later message.
- Web pages, emails and files are treated as **data, not instructions**; suspicious instructions are reported to you.
- Never handles passwords/OTPs; never reads secret folders; only sends data to you.
- Personal and work browsers never exchange data.

## Layout
```
bin/        agent scripts (start, restart, watchdog, schedule, session, buttons, login link, watchers)
tools/      desktop-shot, desktop-control, transcribe  → copy to ~/.local/bin
addons/     powerbi/ — optional Power BI add-on (DAX queries, dashboards-as-code, drafts-only publish)
templates/  agent-instructions.md (→ ~/agent-home/CLAUDE.md), agent.env.example, crontab.txt, autostart
memory/     INDEX, profile, pending, site-playbook template, journal/
workflows/  one folder per topic (WORKFLOW.md + outputs/)
schedules/  job prompts (memory-cleanup.txt is the built-in weekly tidy-up)
```

## Requirements
Ubuntu (GNOME) laptop that stays on · Google Chrome · Node.js (npx) · Python 3 · tmux · jq · curl ·
Claude Code (logged in) with the official Telegram channel plugin · a Telegram bot (@BotFather) ·
optional: Tailscale (phone logins), ydotool (desktop control), Groq API key (voice notes).

## Setup (short version)
1. `git clone <this repo> ~/agent-home`
2. `cp templates/agent-instructions.md ~/agent-home/CLAUDE.md` and fill in the `{{…}}` placeholders.
3. `cp templates/agent.env.example ~/.agent.env && chmod 600 ~/.agent.env` and set `TELEGRAM_CHAT_ID`.
4. Set up the Telegram channel plugin in Claude Code with your bot token, and allow only your own account.
5. `cp tools/* ~/.local/bin/` (voice: put `GROQ_API_KEY=…` in `~/.local/state/personal-agent/secrets/groq.env`).
6. Add the two system cron lines from `templates/crontab.txt` and the autostart file from `templates/autostart/`.
7. `bin/start-agent.sh` → watch with `tmux attach -t agent`. Message your bot.
8. Sign in to your sites once in each browser (or via the login link from your phone).

To use Claude Code by hand on the same laptop run `bin/claude-admin.sh`, **not** plain `claude` — a second
Telegram poller would steal the agent's connection.

## Notes
- Built for one owner on one laptop; paths assume `~/agent-home`. Times in `workflow.sh` use Asia/Kolkata.
- `start-claude.sh` runs Claude Code with `--permission-mode dontAsk`; review the rules before you trust it.
- This repo contains no personal data: `memory/`, `workflows/*/outputs/`, `workspace/`, `downloads/`, `logs/`
  and `CLAUDE.md` are git-ignored. Keep it that way.

## License
MIT
