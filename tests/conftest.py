"""Every test runs against a throwaway HOME, so nothing touches the real config."""

from __future__ import annotations

import importlib
import sys

import pytest


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    """Point every drpc path at tmp_path and hand back the reloaded modules."""
    home = tmp_path / "home"
    for name in ("config", "state", "run"):
        (home / name).mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(home / "config"))
    monkeypatch.setenv("XDG_STATE_HOME", str(home / "state"))
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(home / "run"))
    monkeypatch.setenv("APPDATA", str(home / "config"))
    monkeypatch.setenv("LOCALAPPDATA", str(home / "state"))

    for name in list(sys.modules):
        if name == "drpc" or name.startswith("drpc."):
            del sys.modules[name]
    paths = importlib.import_module("drpc.paths")
    return paths
