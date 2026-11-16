# MANAGER — Telegram group management bot

Python 3.11+ · Aiogram 3 · MongoDB · Railway

## What this build contains

This is an expanded development build, not a certified full Miss Rose clone. It adds working implementations for several of the requested feature families:

- **Admin tools:** `/promote`, `/demote`, `/adminlist`, `/adminrights`, `/admincache`; promotion uses a limited moderator-rights profile rather than granting every possible right.
- **Moderation:** `/ban`, `/tban`, `/sban`, `/dban`, `/unban`, `/mute`, `/tmute`, `/smute`, `/dmute`, `/unmute`, `/kick`, `/skick`, `/dkick`, `/warn`, `/warns`, `/resetwarns`, `/setwarnlimit`, `/setwarnaction`.
- **CAPTCHA:** `/captcha on|off|status`, `/setcaptchatimeout MINUTES`; new members are restricted until they press their personal verification button. Verification uses a separate expiring pending-verification record and does not permanently whitelist the user.
- **Anti-raid:** `/antiraid on|off|status`, `/setraidthreshold N`, `/setraidaction ban|kick|mute`; basic join-spike threshold enforcement.
- **Antiflood:** `/setflood N` and `/setfloodaction delete|mute|ban|kick`; event counters are stored in MongoDB with TTL indexes.
- **Locks:** `/lock`, `/unlock`, `/locktypes` for text, media, photos, videos, animations/GIFs, stickers, documents, audio, voice, video notes, polls, links, contacts, locations, venues, forwarded messages, games and dice.
- **Blocklist:** `/addblocklist <phrase>`, `/addblocklist word|regex <pattern>`, `/unblocklist`, `/blocklist`; supports contains, whole-word and regular-expression matching.
- **Federations:** `/newfed`, `/joinfed`, `/leavefed`, `/fedinfo`, `/fedadmins`, `/addfedadmin`, `/delfedadmin`, `/fban`, `/unfban`, `/delfed`; federation admin checks and stored bans are applied to groups the bot can moderate, including when a group joins later.
- **Reports and logs:** `/report` (reply to a message), `/admin` alias, `/setlog`, `/reports`, persistent report records and admin-only dismiss button.
- **Bulk deletion:** `/purge` (reply to the first message; bounded to 100 message IDs).
- **Existing content/community features:** greetings, rules, text notes and text filters.
- **Settings panel:** navigable module pages with persistent welcome/goodbye/CAPTCHA/anti-raid and common message-lock toggles; help buttons explain related commands.

## Not yet complete / parity caveats

The requested list is broader than a single patch. This build does **not** claim full Miss Rose parity. Still outstanding are exact command-for-command parity and full argument grammar; CAPTCHA challenge modes, attempts and automatic timeout removal; sophisticated raid modes and exemptions; allowlists and per-user lock exemptions; blocklist exemptions and richer actions; federation transfer/ownership tools, logs and scheduled retry of failed cross-chat bans; settings panels for every setting; report assignment/resolve workflow; advanced purge selectors; welcome media/buttons/formatting; note/filter media and advanced formatting; import/export, connections, topics, language packs, privacy controls and extensive automated tests. Some moderation actions depend on Telegram admin permissions and may fail when the bot lacks them.

## Setup

1. Create a Telegram bot with @BotFather and add it to your group as an administrator. Grant only the rights it needs; moderation requires restrict/delete/invite/promote rights as applicable.
2. Create a MongoDB database (MongoDB Atlas or your own MongoDB server).
3. Copy `.env.example` to `.env` and set:

```env
BOT_TOKEN=your_bot_token
DATABASE_URL=mongodb+srv://USER:PASSWORD@HOST/?retryWrites=true&w=majority
MONGO_DATABASE=manager_bot
BOT_USERNAME=your_bot_username
LOG_LEVEL=INFO
```

4. Install and run:

```bash
pip install -r requirements.txt
python -m app.main
```

## Railway

Deploy this folder/repository. Set the same variables in Railway → Variables. Use a MongoDB connection URL reachable from Railway. `MONGO_DATABASE` is simply the database name; MongoDB creates it on first write. Start command: `python -m app.main`.

## Operational notes

- Never share your bot token or MongoDB URI. Rotate them immediately if exposed.
- Use a private test group first. Confirm the bot can delete messages, restrict members, ban members and receive `chat_member` updates.
- Telegram's Bot API cannot provide every capability of a userbot or guarantee that every old message can be deleted.
- Anti-flood and anti-raid event windows use MongoDB collections with TTL cleanup. A Redis-backed distributed rate limiter is a future improvement for very high-volume deployments.
- The Python source has been syntax-compiled. Pure security-helper tests pass in the build environment. The full test suite could not be run here because Aiogram is not installed and package installation was unavailable; a live Telegram/MongoDB integration test and Railway deployment have not been performed.
