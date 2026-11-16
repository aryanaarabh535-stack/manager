"""Pure helpers for MANAGER message security rules."""
from __future__ import annotations

import re
from typing import Any

LOCK_TYPES = (
    "text", "media", "photo", "video", "animation", "sticker", "gif",
    "document", "audio", "voice", "video_note", "poll", "links",
    "contact", "location", "venue", "forward", "game", "dice",
)


def message_matches_lock(message: Any, kind: str) -> bool:
    checks = {
        "text": bool(message.text),
        "media": any((message.photo, message.video, message.animation, message.document,
                       message.audio, message.voice, message.sticker, message.video_note)),
        "photo": bool(message.photo),
        "video": bool(message.video),
        "animation": bool(message.animation),
        "sticker": bool(message.sticker),
        "gif": bool(message.animation),
        "document": bool(message.document),
        "audio": bool(message.audio),
        "voice": bool(message.voice),
        "video_note": bool(message.video_note),
        "poll": bool(message.poll),
        "links": bool(message.text and re.search(r"(?:https?://|www\.|t\.me/)", message.text, re.I)),
        "contact": bool(message.contact),
        "location": bool(message.location),
        "venue": bool(message.venue),
        "forward": bool(message.forward_origin),
        "game": bool(message.game),
        "dice": bool(message.dice),
    }
    return checks.get(kind, False)


def blocklist_matches(text: str, entry: dict[str, Any]) -> bool:
    phrase = str(entry.get("phrase", ""))
    if not phrase:
        return False
    mode = entry.get("mode", "contains")
    haystack = text.casefold()
    needle = phrase.casefold()
    if mode == "regex":
        try:
            return bool(re.search(phrase, text, re.I))
        except re.error:
            return False
    if mode == "word":
        return bool(re.search(rf"(?<!\w){re.escape(phrase)}(?!\w)", text, re.I))
    return needle in haystack
