"""Turning a profile into a Discord payload, and keeping it broadcast."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from pypresence import ActivityType, Presence, StatusDisplayType

from .config import ACTIVITY_TYPES, DISPLAY_TYPES
from .errors import Fail

_ACTIVITY = {
    "playing": ActivityType.PLAYING,
    "listening": ActivityType.LISTENING,
    "watching": ActivityType.WATCHING,
    "competing": ActivityType.COMPETING,
}
_DISPLAY = {
    "name": StatusDisplayType.NAME,
    "state": StatusDisplayType.STATE,
    "details": StatusDisplayType.DETAILS,
}

RECONNECT_DELAY = 15
REFRESH_INTERVAL = 60
TICK = 0.5  # how often the loop looks up to see whether it was asked to stop


def build_payload(profile: dict[str, Any]) -> dict[str, Any]:
    """Turn a profile dict into kwargs for ``Presence.update()``."""
    payload: dict[str, Any] = {}
    for key in (
        "name",
        "details",
        "state",
        "large_image",
        "large_text",
        "large_url",
        "small_image",
        "small_text",
        "small_url",
    ):
        value = (profile.get(key) or "").strip()
        if value:
            payload[key] = value

    activity = (profile.get("activity_type") or "playing").lower()
    if activity not in _ACTIVITY:
        raise Fail(f"activity_type must be one of: {', '.join(ACTIVITY_TYPES)}")
    payload["activity_type"] = _ACTIVITY[activity]

    display = (profile.get("status_display_type") or "").lower()
    if display:
        if display not in _DISPLAY:
            raise Fail(f"status_display_type must be one of: {', '.join(DISPLAY_TYPES)}")
        payload["status_display_type"] = _DISPLAY[display]

    buttons = [
        {"label": button["label"], "url": button["url"]}
        for button in (profile.get("buttons") or [])
        if (button.get("label") or "").strip() and (button.get("url") or "").strip()
    ][:2]
    if buttons:
        payload["buttons"] = buttons

    return payload


def _sleep(seconds: float, should_stop: Callable[[], bool]) -> bool:
    """Nap in slices so a stop request is noticed promptly. True = stop now."""
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if should_stop():
            return True
        time.sleep(min(TICK, max(0.0, deadline - time.monotonic())))
    return should_stop()


def loop(
    profile_name: str,
    profile: dict[str, Any],
    started_at: int,
    log: Callable[[str], None],
    should_stop: Callable[[], bool] = lambda: False,
) -> None:
    payload = build_payload(profile)
    if profile.get("timer", True):
        payload["start"] = started_at

    log(f"profile={profile_name} client_id={profile['client_id']} start={started_at}")
    rpc: Presence | None = None
    try:
        while not should_stop():
            try:
                if rpc is None:
                    rpc = Presence(str(profile["client_id"]))
                    rpc.connect()
                    log("connected to Discord")
                rpc.update(**payload)
            except Exception as exc:  # Discord closed, restarted, or not running yet
                log(f"connection lost ({type(exc).__name__}: {exc}); retrying in "
                    f"{RECONNECT_DELAY}s")
                _close(rpc)
                rpc = None
                if _sleep(RECONNECT_DELAY, should_stop):
                    break
                continue
            if _sleep(REFRESH_INTERVAL, should_stop):
                break
    finally:
        if rpc is not None:
            try:
                rpc.clear()  # drop the presence now rather than on Discord's timeout
            except Exception:
                pass
            _close(rpc)


def _close(rpc: Presence | None) -> None:
    if rpc is None:
        return
    try:
        rpc.close()
    except Exception:
        pass
