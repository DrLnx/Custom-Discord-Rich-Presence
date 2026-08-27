import sys

import pytest

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="POSIX autostart")


def test_hypr_is_preferred_when_omarchy_put_an_autostart_there(sandbox, monkeypatch):
    from drpc import autostart

    autostart.HYPR_AUTOSTART.parent.mkdir(parents=True, exist_ok=True)
    autostart.HYPR_AUTOSTART.write_text("-- Extra autostart processes.\n")
    monkeypatch.setattr(autostart, "methods", lambda: ["hypr", "systemd"])
    assert autostart.default_method() == "hypr"

    assert autostart.enable("hypr")
    assert "drpc" in autostart.HYPR_AUTOSTART.read_text()
    assert autostart.state()["hypr"] is True

    assert autostart.enable("hypr") == ["already on"]  # idempotent

    autostart.disable("hypr")
    assert "drpc" not in autostart.HYPR_AUTOSTART.read_text()


def test_disabling_hypr_keeps_the_rest_of_the_file(sandbox):
    from drpc import autostart

    autostart.HYPR_AUTOSTART.parent.mkdir(parents=True, exist_ok=True)
    autostart.HYPR_AUTOSTART.write_text(
        '-- Extra autostart processes.\no.exec_on_start("something-else")\n'
    )
    autostart.enable("hypr")
    autostart.disable("hypr")
    text = autostart.HYPR_AUTOSTART.read_text()
    assert "something-else" in text
    assert "drpc" not in text


def test_an_unavailable_method_is_refused(sandbox):
    from drpc import autostart
    from drpc.errors import Fail

    with pytest.raises(Fail):
        autostart.enable("registry")
