from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

PAGES = {
    "main": [
        ("🛡 Moderation", "moderation"), ("🔒 Locks & anti-spam", "security"),
        ("👋 Greetings", "greetings"), ("🧩 Notes & filters", "content"),
        ("📜 Rules & reports", "community"), ("🌐 Federation", "federation"),
        ("📋 Logs & cleaning", "logs"), ("⚙️ General", "general"),
    ],
    "moderation": [
        ("⚠️ Warnings", "help_warnings"), ("✅ Approvals", "help_approvals"),
        ("👮 Admin tools", "help_admins"), ("🧹 Purge tools", "help_purge"),
    ],
    "security": [
        ("CAPTCHA", "toggle_captcha"), ("Anti-raid", "toggle_antiraid"),
        ("Lock text", "toggle_lock_text"), ("Lock media", "toggle_lock_media"),
        ("Lock links", "toggle_lock_links"), ("Lock photos", "toggle_lock_photo"),
        ("Lock videos", "toggle_lock_video"), ("Lock stickers", "toggle_lock_sticker"),
        ("Lock documents", "toggle_lock_document"), ("Blocklist help", "help_blocklist"),
        ("Antiflood help", "help_antiflood"),
    ],
    "greetings": [
        ("Welcome", "toggle_welcome"), ("Goodbye", "toggle_goodbye"),
        ("Set welcome text", "help_setwelcome"), ("Set goodbye text", "help_setgoodbye"),
    ],
    "content": [
        ("Notes help", "help_notes"), ("Filters help", "help_filters"),
    ],
    "community": [("View rules", "help_rules"), ("Set rules", "help_setrules"), ("Reports", "help_reports")],
    "federation": [("Federation commands", "help_fed")],
    "logs": [("Set log channel", "help_setlog"), ("Purge messages", "help_purge")],
    "general": [("Refresh admin cache", "help_admincache"), ("Connections", "help_connections")],
}


def settings_keyboard(page: str = "main", settings: dict | None = None) -> InlineKeyboardMarkup:
    settings = settings or {}
    builder = InlineKeyboardBuilder()
    for label, callback in PAGES.get(page, PAGES["main"]):
        if callback.startswith("toggle_"):
            field = callback.removeprefix("toggle_")
            if field.startswith("lock_"):
                state = bool(settings.get("locks", {}).get(field.removeprefix("lock_"), False))
            else:
                state = bool(settings.get({"welcome": "welcome_enabled", "goodbye": "goodbye_enabled", "captcha": "captcha_enabled", "antiraid": "antiraid_enabled"}.get(field, field), False))
            label = f"{'🟢' if state else '⚪'} {label} {'ON' if state else 'OFF'}"
        builder.button(text=label, callback_data=f"mgr:{callback}")
    builder.adjust(2)
    if page != "main":
        builder.row(InlineKeyboardButton(text="⬅️ Back", callback_data="mgr:main"))
    return builder.as_markup()
