# MANAGER feature and parity matrix

Status: extended development build. “Implemented” means a basic functional command path exists; it does not imply exact Miss Rose behavior or complete integration testing.

| Feature family | Current status | Main commands / notes |
|---|---|---|
| Core and settings | Partial | `/start`, `/help`, `/settings`; navigable pages; persistent greeting, CAPTCHA, raid and common lock toggles |
| Moderation | Partial | ban/mute/kick variants, warnings, warning threshold/action, approvals, bounded purge |
| Admin management | Improved basic | `/promote`, `/demote`, `/adminlist`, `/adminrights`, `/admincache`; limited moderator preset; no full granular rights editor |
| CAPTCHA | Basic | user-specific callback, pending-verification collection, expiry timestamp and configurable timeout value; no automatic timeout kick/unban flow or challenge modes |
| Antiflood | Basic | MongoDB per-user 5-second counter and configurable action; no Redis distributed limiter |
| Antiraid | Basic | configurable join threshold/window and ban/kick/mute action; no exemptions, adaptive mode or rollback |
| Locks | Partial | text/media/photo/video/animation/sticker/document/audio/voice/video note/poll/link/contact/location/venue/forward/game/dice |
| Blocklist | Basic | contains, whole-word and regex entries; no exemptions, full Rose syntax or per-entry punishment settings |
| Federations | Improved basic | create/join/leave/info, federation admins, federation bans and unbans; no ownership transfer, logs or retry queue for inaccessible chats |
| Reports and logs | Basic | persistent `/report` and `/admin`, `/setlog`, `/reports`, admin-only dismiss |
| Greetings | Partial | text welcome/goodbye and placeholders; media/buttons/advanced formatting pending |
| Notes and filters | Partial | text-only CRUD and trigger matching; media/formatting features pending |
| Full Rose parity | Not complete | exact command aliases, full argument grammar, every setting/button, advanced integrations and extensive tests remain |

## Important implementation notes

- The security message catch-all is registered last in the dispatcher so it does not intercept command handlers. Text filters are evaluated inside that final handler.
- Chat-member join processing calls the CAPTCHA/anti-raid logic and the greeting logic from one handler, avoiding competing chat-member handlers swallowing each other's updates.
- CAPTCHA verification state is separate from the administrator-managed approved-user list.
- Telegram Bot API permissions, bot membership, privacy settings and chat type constrain what can be enforced.
- Do not advertise this version as a complete Miss Rose replacement.
