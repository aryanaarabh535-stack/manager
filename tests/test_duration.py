from app.routers.moderation import parse_duration

def test_duration():
    assert parse_duration("3d").total_seconds() == 259200
    assert parse_duration("2h").total_seconds() == 7200
    assert parse_duration("10m").total_seconds() == 600
    assert parse_duration("bad") is None
