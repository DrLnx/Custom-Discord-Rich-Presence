"""The daemon is spawned for real; only Discord itself is stubbed out."""

from __future__ import annotations

import time

import pytest


def wait_for(predicate, timeout=8.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.05)
    return False


def test_lock_reports_a_free_pidfile_as_not_running(sandbox):
    from drpc.lock import PidLock, running_pid

    path = sandbox.RUN_DIR / "test.pid"
    assert running_pid(path) is None

    lock = PidLock(path)
    assert lock.acquire()
    assert running_pid(path) is not None

    second = PidLock(path)
    assert not second.acquire()  # single instance, enforced by the OS

    lock.release()
    assert running_pid(path) is None


def test_a_stale_pidfile_does_not_look_like_a_running_daemon(sandbox):
    from drpc import daemon

    sandbox.RUN_DIR.mkdir(parents=True, exist_ok=True)
    sandbox.PID.write_text("999999\n")
    assert daemon.status() is None


@pytest.mark.slow
def test_start_stop_restart_round_trip(sandbox):
    from drpc import config, daemon

    cfg = config.load()
    config.save(cfg)

    pid = daemon.start()
    assert pid and daemon.status() == pid
    assert daemon.session()["profile"] == cfg["active"]

    started_at = daemon.session()["started_at"]
    new_pid, carried = daemon.restart()
    assert new_pid != pid
    assert carried is not None
    assert daemon.session()["started_at"] == started_at  # the timer survives a reload

    assert daemon.stop() is True
    assert wait_for(lambda: daemon.status() is None)
    assert not sandbox.SESSION.exists()
    assert daemon.stop() is False  # stopping twice is not an error


@pytest.mark.slow
def test_a_second_start_refuses_rather_than_racing(sandbox):
    from drpc import daemon
    from drpc.errors import Fail

    daemon.start()
    try:
        with pytest.raises(Fail, match="already running"):
            daemon.start()
    finally:
        daemon.stop()


def test_start_rejects_a_profile_with_no_client_id(sandbox):
    from drpc import config, daemon
    from drpc.errors import Fail

    cfg = config.load()
    cfg["profiles"][cfg["active"]]["client_id"] = ""
    config.save(cfg)
    with pytest.raises(Fail, match="client_id"):
        daemon.start()
