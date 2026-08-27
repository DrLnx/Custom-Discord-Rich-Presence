"""Where drpc keeps its files, on every platform it supports.

platformdirs gives the right answer per OS (``~/.config/drpc`` on Linux,
``%APPDATA%\\drpc`` on Windows).  Runtime state is deliberately kept apart
from persistent state: on Linux it belongs on tmpfs so a hard reboot cannot
leave a stale pidfile behind, and elsewhere it simply lives with the logs.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from platformdirs import PlatformDirs

WINDOWS = sys.platform == "win32"
MACOS = sys.platform == "darwin"

_dirs = PlatformDirs(appname="drpc", appauthor=False, ensure_exists=False)

CONFIG_DIR = Path(_dirs.user_config_dir)
STATE_DIR = Path(_dirs.user_state_dir)

CONFIG = CONFIG_DIR / "config.json"
LOG = STATE_DIR / "drpc.log"


def _runtime_dir() -> Path:
    runtime = os.environ.get("XDG_RUNTIME_DIR")
    if runtime and not WINDOWS:
        return Path(runtime) / "drpc"
    return STATE_DIR


RUN_DIR = _runtime_dir()
PID = RUN_DIR / "drpc.pid"
SESSION = RUN_DIR / "drpc-session.json"
STOP_FLAG = RUN_DIR / "drpc.stop"


def ensure_dirs() -> None:
    for directory in (CONFIG_DIR, STATE_DIR, RUN_DIR):
        directory.mkdir(parents=True, exist_ok=True)


def self_command() -> list[str]:
    """The argv prefix that re-invokes drpc, frozen binary or not."""
    if getattr(sys, "frozen", False):  # PyInstaller one-file build
        return [sys.executable]
    return [sys.executable, "-m", "drpc"]
