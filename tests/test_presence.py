import pytest


def test_payload_drops_empty_fields_and_maps_enums(sandbox):
    from pypresence import ActivityType

    from drpc.presence import build_payload

    payload = build_payload(
        {
            "name": "Editor",
            "details": "  ",
            "state": "line 2",
            "activity_type": "listening",
            "status_display_type": "state",
            "buttons": [
                {"label": "a", "url": "https://a"},
                {"label": "", "url": "https://b"},
                {"label": "c", "url": "https://c"},
                {"label": "d", "url": "https://d"},
            ],
        }
    )
    assert "details" not in payload  # whitespace only
    assert payload["state"] == "line 2"
    assert payload["activity_type"] is ActivityType.LISTENING
    # blanks dropped, then capped at Discord's limit of two
    assert [b["label"] for b in payload["buttons"]] == ["a", "c"]


def test_bad_activity_type_is_a_clear_failure(sandbox):
    from drpc.errors import Fail
    from drpc.presence import build_payload

    with pytest.raises(Fail, match="activity_type"):
        build_payload({"activity_type": "vibing"})
