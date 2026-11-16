from types import SimpleNamespace

from app.services.security import LOCK_TYPES, blocklist_matches, message_matches_lock


def fake_message(**kwargs):
    defaults = {"text": None, "photo": None, "video": None, "animation": None,
                "document": None, "audio": None, "voice": None, "sticker": None,
                "video_note": None, "poll": None, "contact": None,
                "location": None, "venue": None, "forward_origin": None,
                "game": None, "dice": None}
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_lock_catalog_is_nonempty_and_distinct():
    assert "text" in LOCK_TYPES
    assert "links" in LOCK_TYPES
    assert len(LOCK_TYPES) == len(set(LOCK_TYPES))


def test_photo_and_link_locks():
    assert message_matches_lock(fake_message(photo=[object()]), "photo")
    assert message_matches_lock(fake_message(text="Visit https://example.com"), "links")
    assert not message_matches_lock(fake_message(text="hello"), "links")


def test_blocklist_contains_word_and_regex():
    assert blocklist_matches("This is BAD content", {"phrase": "bad", "mode": "contains"})
    assert blocklist_matches("bad!", {"phrase": "bad", "mode": "word"})
    assert not blocklist_matches("badminton", {"phrase": "bad", "mode": "word"})
    assert blocklist_matches("abc123", {"phrase": r"abc\d+", "mode": "regex"})
    assert not blocklist_matches("abc", {"phrase": "[", "mode": "regex"})
