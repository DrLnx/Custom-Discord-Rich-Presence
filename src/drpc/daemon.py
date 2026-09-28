"""Starting, stopping, and inspecting the background presence process.

The original daemon double-forked, which Windows has no answer for.  Both
platforms now do the same thing: spawn a detached copy of drpc running the
hidden ``_serve`` command, and let an advisory lock on the pidfile decide who
is in charge.  Shutdown is a flag file the daemon polls, so it can clear the
presence on the way out — with a hard kill only as a fallback.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from typing import Any

from . import presence
from .config import get_profile, load
from .errors import Fail
from .lock import PidLock, running_pid
from .paths import LOG, PID, SESSION, STOP_FLAG, WINDOWS, ensure_dirs, self_command

GRACE_SECONDS = 6.0
SPAWN_TIMEOUT = 5.0


def log(message: str) -> None:
    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{stamp}] {message}", flush=True)


def status() -> int | None:
    """The pid of the running daemon, or None."""
    return running_pid(PID)


def session() -> dict[str, Any]:
    try:
        return json.loads(SESSION.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def sane_start(started_at: int) -> int:
    """A start stamp from the future means the clock moved back (NTP, a timezone
    fix) since it was taken; anchor to now so the timer counts instead of sitting
    at zero until wall-clock catches up."""
    now = int(time.time())
    return min(int(started_at), now)


def elapsed() -> int | None:
    started = session().get("started_at")
    if not started or status() is None:
        return None
    return max(0, int(time.time()) - int(started))


# --- the daemon itself -----------------------------------------------------

def serve(profile_name: str | None, started_at: int) -> None:
    """Run the presence loop in this process. Invoked as ``drpc _serve``."""
    ensure_dirs()
    STOP_FLAG.unlink(missing_ok=True)

    lock = PidLock(PID)
    if not lock.acquire():
        raise Fail(f"already running (pid {status()})")

    started_at = sane_start(started_at)
    cfg = load()
    name, profile = get_profile(cfg, profile_name)
    SESSION.write_text(
        json.dumps({"profile": name, "started_at": started_at}), encoding="utf-8"
    )

    stopping = False

    def request_stop(_signum=None, _frame=None) -> None:
        nonlocal stopping
        stopping = True

    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            signal.signal(sig, request_stop)
        except (ValueError, OSError):  # not available in this context
            pass

    try:
        presence.loop(
            name,
            profile,
            started_at,
            log,
            should_stop=lambda: stopping or STOP_FLAG.exists(),
        )
    finally:
        log("stopping")
        SESSION.unlink(missing_ok=True)
        STOP_FLAG.unlink(missing_ok=True)
        lock.release()


# --- controlling it from the CLI -------------------------------------------

def _spawn(profile_name: str | None, started_at: int) -> None:
    ensure_dirs()
    STOP_FLAG.unlink(missing_ok=True)
    command = self_command() + ["_serve", "--started-at", str(started_at)]
    if profile_name:
        command += ["--profile", profile_name]

    handle = open(LOG, "a", encoding="utf-8", errors="replace")
    kwargs: dict[str, Any] = {
        "stdin": subprocess.DEVNULL,
        "stdout": handle,
        "stderr": subprocess.STDOUT,
        "close_fds": True,
        "cwd": str(os.path.expanduser("~")),
    }
    if WINDOWS:  # pragma: no cover - platform specific
        kwargs["creationflags"] = (
            subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        )
    else:
        kwargs["start_new_session"] = True

    try:
        subprocess.Popen(command, **kwargs)
    finally:
        handle.close()


def start(profile_name: str | None = None, started_at: int | None = None) -> int:
    existing = status()
    if existing:
        raise Fail(f"already running (pid {existing}). Use 'drpc restart' to reload.")

    cfg = load()
    name, profile = get_profile(cfg, profile_name)
    if not str(profile.get("client_id") or "").strip():
        raise Fail(f"profile {name!r} has no client_id set")
    presence.build_payload(profile)  # fail here, not silently in the background

    started_at = sane_start(started_at or int(time.time()))
    _spawn(name, started_at)

    deadline = time.monotonic() + SPAWN_TIMEOUT
    while time.monotonic() < deadline:
        pid = status()
        if pid:
            return pid
        time.sleep(0.1)
    raise Fail(f"the daemon did not come up — see the log at {LOG}")


def stop() -> bool:
    """Ask the daemon to stop. Returns False when it was not running."""
    pid = status()
    if not pid:
        _clear_stale()
        return False

    ensure_dirs()
    STOP_FLAG.touch()
    if not WINDOWS and pid > 0:
        _signal(pid, signal.SIGTERM)

    deadline = time.monotonic() + GRACE_SECONDS
    while time.monotonic() < deadline:
        if status() is None:
            _clear_stale()
            return True
        time.sleep(0.1)

    _hard_kill(pid)
    for _ in range(20):
        if status() is None:
            break
        time.sleep(0.1)
    _clear_stale()
    return True


def restart(
    profile_name: str | None = None, reset_timer: bool = False
) -> tuple[int, int | None]:
    """Returns (pid, carried_over_elapsed_seconds)."""
    previous = session().get("started_at") if status() else None
    stop()
    carried = None
    started_at = None
    if previous and not reset_timer:
        started_at = sane_start(int(previous))
        carried = max(0, int(time.time()) - started_at)
    return start(profile_name, started_at), carried


def _signal(pid: int, sig: int) -> None:
    try:
        os.kill(pid, sig)
    except (OSError, ProcessLookupError):
        pass


def _hard_kill(pid: int) -> None:
    if pid <= 0:
        return
    if WINDOWS:  # pragma: no cover - platform specific
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(pid)],
            capture_output=True,
            check=False,
        )
    else:
        _signal(pid, signal.SIGKILL)


def _clear_stale() -> None:
    STOP_FLAG.unlink(missing_ok=True)
    SESSION.unlink(missing_ok=True)
    if status() is None:
        PID.unlink(missing_ok=True)


def read_log(lines: int = 50) -> list[str]:
    if not LOG.exists():
        return []
    with open(LOG, encoding="utf-8", errors="replace") as handle:
        return handle.read().splitlines()[-lines:]


def follow_log(lines: int = 50) -> None:
    """A portable ``tail -f``; Windows has no tail to shell out to."""
    ensure_dirs()
    LOG.touch(exist_ok=True)
    for line in read_log(lines):
        print(line)
    with open(LOG, encoding="utf-8", errors="replace") as handle:
        handle.seek(0, os.SEEK_END)
        while True:
            line = handle.readline()
            if line:
                sys.stdout.write(line)
                sys.stdout.flush()
            else:
                time.sleep(0.4)
