import json

import pytest


def test_creates_a_default_config_on_first_read(sandbox):
    from drpc import config

    cfg = config.load()
    assert sandbox.CONFIG.exists()
    assert cfg["active"] in cfg["profiles"]


def test_save_is_atomic_and_round_trips(sandbox):
    from drpc import config

    cfg = config.load()
    cfg["profiles"]["default"]["details"] = "hello"
    config.save(cfg)
    assert json.loads(sandbox.CONFIG.read_text())["profiles"]["default"]["details"] == "hello"
    assert not sandbox.CONFIG.with_suffix(".json.tmp").exists()


def test_broken_json_is_reported_not_swallowed(sandbox):
    from drpc import config
    from drpc.errors import Fail

    sandbox.CONFIG.parent.mkdir(parents=True, exist_ok=True)
    sandbox.CONFIG.write_text("{ not json")
    with pytest.raises(Fail, match="not valid JSON"):
        config.load()


def test_unknown_profile_lists_the_known_ones(sandbox):
    from drpc import config
    from drpc.errors import Fail

    cfg = config.load()
    with pytest.raises(Fail, match="default"):
        config.get_profile(cfg, "nope")


@pytest.mark.parametrize(
    "raw,expected",
    [("true", True), ("ON", True), ("no", False), ("off", False), ("hi", "hi")],
)
def test_coerce_reads_booleans_but_leaves_text_alone(sandbox, raw, expected):
    from drpc import config

    assert config.coerce(raw) == expected
