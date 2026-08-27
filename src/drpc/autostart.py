"""Starting drpc with the desktop session, on each platform's own terms.

Linux gets a systemd user unit, which works on any distro.  Omarchy machines
already have an ``autostart.lua``, so that route is kept and preferred when
the file exists.  Windows uses the per-user Run key, which needs nothing but
the standard library.
"""

from __future__ import annotations

import shlex
import shutil
import subprocess
import sys
from pathlib import Path

from .errors import Fail
from .paths import MACOS, WINDOWS, self_command

SERVICE = Path.home() / ".config" / "systemd" / "user" / "drpc.service"
HYPR_AUTOSTART = Path.home() / ".config" / "hypr" / "autostart.lua"
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_VALUE = "drpc"

UNIT = """\
[Unit]
Description=drpc — Discord Rich Presence
After=graphical-session.target
PartOf=graphical-session.target

[Service]
Type=simple
ExecStart={exec_start}
Restart=on-failure
RestartSec=15

[Install]
WantedBy=graphical-session.target
"""


def _launch_command() -> list[str]:
    """The argv that runs the presence in the foreground, for a supervisor."""
    if getattr(sys, "frozen", False):
        return [sys.executable, "_serve"]
    console_script = shutil.which("drpc")
    if console_script:
        return [console_script, "_serve"]
    return self_command() + ["_serve"]


def _spawn_command() -> str:
    """The argv that starts the daemon and returns, for a fire-and-forget hook."""
    if getattr(sys, "frozen", False):
        parts = [sys.executable, "start"]
    else:
        console_script = shutil.which("drpc")
        parts = [console_script, "start"] if console_script else self_command() + ["start"]
    return subprocess.list2cmdline(parts) if WINDOWS else shlex.join(parts)


def _hypr_line() -> str:
    return f'o.exec_on_start("{_spawn_command()}")'


def methods() -> list[str]:
    if WINDOWS:
        return ["registry"]
    if MACOS:
        return []
    return ["hypr", "systemd"] if HYPR_AUTOSTART.exists() else ["systemd"]


def default_method() -> str:
    available = methods()
    if not available:
        raise Fail(
            "autostart is not implemented for this platform yet — "
            "add 'drpc start' to your session's startup items by hand"
        )
    return available[0]


# --- systemd ---------------------------------------------------------------

def _systemctl(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["systemctl", "--user", *args], capture_output=True, text=True, check=False
    )


def _systemd_enabled() -> bool:
    if not SERVICE.exists():
        return False
    return _systemctl("is-enabled", "drpc.service").stdout.strip() == "enabled"


def _systemd_enable() -> list[str]:
    if not shutil.which("systemctl"):
        raise Fail("systemctl not found — this system does not use systemd")
    SERVICE.parent.mkdir(parents=True, exist_ok=True)
    SERVICE.write_text(UNIT.format(exec_start=shlex.join(_launch_command())), encoding="utf-8")
    _systemctl("daemon-reload")
    result = _systemctl("enable", "drpc.service")
    if result.returncode != 0:
        raise Fail(f"systemctl enable failed: {result.stderr.strip()}")
    return [f"wrote {SERVICE}", "enabled drpc.service for your user session"]


def _systemd_disable() -> list[str]:
    notes = []
    if shutil.which("systemctl"):
        _systemctl("disable", "--now", "drpc.service")
        notes.append("disabled drpc.service")
    if SERVICE.exists():
        SERVICE.unlink()
        notes.append(f"removed {SERVICE}")
        _systemctl("daemon-reload")
    return notes


# --- Omarchy / Hyprland ----------------------------------------------------

def _hypr_text() -> str:
    if HYPR_AUTOSTART.exists():
        return HYPR_AUTOSTART.read_text(encoding="utf-8")
    return "-- Extra autostart processes.\n"


def _hypr_enabled() -> bool:
    return any(
        "drpc" in line and "exec_on_start" in line
        for line in _hypr_text().splitlines()
    )


def _hypr_enable() -> list[str]:
    if not HYPR_AUTOSTART.parent.exists():
        raise Fail(f"{HYPR_AUTOSTART.parent} does not exist — is this Hyprland?")
    text = _hypr_text()
    if not text.endswith("\n"):
        text += "\n"
    # Deliberately exec_on_start and not launch_on_start: the latter wraps the
    # command in uwsm-app, which runs it in a systemd scope that gets torn down
    # the moment our spawning process exits.
    HYPR_AUTOSTART.write_text(text + _hypr_line() + "\n", encoding="utf-8")
    return [f"added to {HYPR_AUTOSTART}", f"  {_hypr_line()}"]


def _hypr_disable() -> list[str]:
    if not HYPR_AUTOSTART.exists():
        return []
    kept = [
        line
        for line in _hypr_text().splitlines()
        if not ("drpc" in line and "exec_on_start" in line)
    ]
    HYPR_AUTOSTART.write_text("\n".join(kept).rstrip("\n") + "\n", encoding="utf-8")
    return [f"removed from {HYPR_AUTOSTART}"]


# --- Windows ---------------------------------------------------------------

def _registry_enabled() -> bool:  # pragma: no cover - platform specific
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            winreg.QueryValueEx(key, RUN_VALUE)
    except OSError:
        return False
    return True


def _registry_enable() -> list[str]:  # pragma: no cover - platform specific
    import winreg

    command = _spawn_command()
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
        winreg.SetValueEx(key, RUN_VALUE, 0, winreg.REG_SZ, command)
    return [f"added HKCU\\{RUN_KEY}\\{RUN_VALUE}", f"  {command}"]


def _registry_disable() -> list[str]:  # pragma: no cover - platform specific
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, RUN_VALUE)
    except OSError:
        return []
    return [f"removed HKCU\\{RUN_KEY}\\{RUN_VALUE}"]


# --- dispatch --------------------------------------------------------------

_HANDLERS = {
    "systemd": (_systemd_enabled, _systemd_enable, _systemd_disable),
    "hypr": (_hypr_enabled, _hypr_enable, _hypr_disable),
    "registry": (_registry_enabled, _registry_enable, _registry_disable),
}


def state() -> dict[str, bool]:
    """Every mechanism available here, and whether it is currently on."""
    return {name: _HANDLERS[name][0]() for name in methods()}


def enabled() -> bool:
    return any(state().values())


def enable(method: str | None = None) -> list[str]:
    method = method or default_method()
    _check(method)
    if _HANDLERS[method][0]():
        return ["already on"]
    return _HANDLERS[method][1]()


def disable(method: str | None = None) -> list[str]:
    targets = [method] if method else list(methods())
    notes: list[str] = []
    for target in targets:
        _check(target)
        notes += _HANDLERS[target][2]()
    return notes or ["already off"]


def _check(method: str) -> None:
    if method not in _HANDLERS:
        raise Fail(f"unknown autostart method {method!r}")
    if method not in methods():
        available = ", ".join(methods()) or "none"
        raise Fail(f"{method!r} is not available here (available: {available})")
