# MANAGER Telegram Bot

Initial implementation scaffold for a Rose-compatible Telegram group-management bot.

## Stack
- Python 3.12
- Aiogram 3
- MongoDB (Motor async driver)
- Optional Redis (reserved for rate limits, FSM and cache)
- Railway Docker deployment

## Run locally
1. Create a bot with @BotFather and keep the token secret.
2. Create a MongoDB database (MongoDB Atlas or Railway-compatible MongoDB service).
3. Copy `.env.example` to `.env` and fill `BOT_TOKEN` and `DATABASE_URL`.
4. `pip install -r requirements.txt`
5. `python -m app.main`
6. Add the bot to a test group and grant only the permissions needed for features being tested.

`DATABASE_URL` must be your MongoDB connection string, such as `mongodb+srv://...` (Atlas) or `mongodb://...` (self-hosted). Set `MONGO_DATABASE` to the database name (defaults to `manager_bot`).

## Implemented in this starter
- `/start`, `/help`, `/settings` with callback navigation shell
- Ban, timed ban, silent/delete ban, unban
- Mute, timed mute, silent/delete mute, unmute
- Kick, silent/delete kick
- Warn, warns, resetwarns (warning threshold automation is pending)
- Welcome/goodbye enable, display and text configuration
- Rules, setrules, resetrules
- Text notes: save/get/notes/clear
- Text filters: filter/filters/stop and basic trigger matching
- Persistent MongoDB collections and indexes for settings, warnings, notes/filters, approvals, blocklists and federations
- Welcome/goodbye member event handling

## Parity roadmap
This is a working foundation, not a claim that all Rose features are finished. Complete parity requires implementing and testing every current Rose docs module:

1. Admin permissions, promote/demote/adminlist/admincache, anonymous admin verification.
2. Complete moderation argument grammar, reasons, target resolution, silent actions and permission parity.
3. Purges (`del`, `purge`, selective/ranged purges), pin/permapin/unpin, approvals.
4. Warning limits, modes, custom warning text, warning buttons.
5. Reports (`/report`, `@admin`) and report controls.
6. Command disabling and cleaning command/service/bot messages.
7. Full greetings: media, placeholders, random messages, formatting, buttons, delays, clean service and join/leave conditions.
8. CAPTCHA modes, timeout, attempts, welcome mute, verification callbacks.
9. Full lock type catalogue, lock modes, allowlists and Telegram message-type detection.
10. Blocklists: phrases, multi-entry syntax, regex/word matching, modes and exemptions.
11. Antiflood, antiraid and automatic punishment engines with Redis counters.
12. Federations: create/delete/join/leave, admins, chats, logs, federation bans and user commands.
13. Full notes: media/attachments, private/admin-only, repeated notes and all fillings.
14. Full filters: phrase/multi/exact/prefix triggers, media replies, `{admin}`, `{user}`, `{allow_bot}`, command suggestions.
15. Formatting parser: HTML/Markdown, fillings, random content, URL button syntax, same-row layout and button generator.
16. Connections, echo, import/export, privacy controls and bot-to-bot review workflow.
17. Topics/action topics, language packs, advanced options and all help/alias commands.
18. Interactive settings panels: every setting must read/write the same database state as its command counterpart; pagination, confirmations and back navigation.

## Important compatibility notes
- Telegram Bot API limitations apply (e.g. message deletion age limits, available member updates, anonymous admins, forum topic permissions).
- Do not grant the bot more permissions than necessary.
- Never commit `.env`, bot tokens, database credentials or user data.
- For production, replace `create_all` with Alembic migrations, add structured audit logs, Redis-backed rate limiting, backups and integration tests.
