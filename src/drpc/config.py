"""Reading, writing, and validating ``config.json``."""

from __future__ import annotations

import json
from typing import Any

from .errors import Fail
from .paths import CONFIG

ACTIVITY_TYPES = ("playing", "listening", "watching", "competing")
DISPLAY_TYPES = ("name", "state", "details")

# Keys that are plain strings on a profile, in the order the UI shows them.
TEXT_KEYS = (
    "name",
    "client_id",
    "details",
    "state",
    "large_image",
    "large_text",
    "large_url",
    "small_image",
    "small_text",
    "small_url",
)
IMAGE_KEYS = ("large_image", "small_image")

DEFAULT_PROFILE: dict[str, Any] = {
    "client_id": "383226320970055681",
    "name": "Visual Studio Code",
    "activity_type": "playing",
    "status_display_type": "name",
    "details": "Building something",
    "state": "",
    "large_image": (
        "https://raw.githubusercontent.com/microsoft/vscode/main/resources/linux/code.png"
    ),
    "large_text": "Visual Studio Code",
    "large_url": "",
    "small_image": "",
    "small_text": "",
    "small_url": "",
    "timer": True,
    "buttons": [],
}

DEFAULT_CONFIG: dict[str, Any] = {
    "active": "default",
    "profiles": {"default": DEFAULT_PROFILE},
}


def blank_profile() -> dict[str, Any]:
    return json.loads(json.dumps(DEFAULT_PROFILE))


def load() -> dict[str, Any]:
    if not CONFIG.exists():
        cfg = json.loads(json.dumps(DEFAULT_CONFIG))
        save(cfg)
        return cfg
    try:
        cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise Fail(f"{CONFIG} is not valid JSON: {exc}") from exc
    if not isinstance(cfg, dict) or not isinstance(cfg.get("profiles"), dict):
        raise Fail(f"{CONFIG} has no 'profiles' object")
    if not cfg["profiles"]:
        raise Fail(f"{CONFIG} defines no profiles")
    return cfg


def save(cfg: dict[str, Any]) -> None:
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    tmp = CONFIG.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
    tmp.replace(CONFIG)


def get_profile(cfg: dict[str, Any], name: str | None = None) -> tuple[str, dict[str, Any]]:
    name = name or cfg.get("active")
    profiles = cfg.get("profiles", {})
    if name not in profiles:
        known = ", ".join(profiles) or "(none)"
        raise Fail(f"no profile named {name!r}. Known: {known}")
    return name, profiles[name]


def coerce(value: str) -> Any:
    low = value.strip().lower()
    if low in ("true", "yes", "on"):
        return True
    if low in ("false", "no", "off"):
        return False
    return value
