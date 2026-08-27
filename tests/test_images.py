import pytest


@pytest.mark.parametrize(
    "url,expected",
    [
        (
            "https://www.google.com/imgres?imgurl=https%3A%2F%2Fx.test%2Fa.png&h=1",
            "https://x.test/a.png",
        ),
        ("https://example.com/a.png", "https://example.com/a.png"),
        ("", ""),
    ],
)
def test_normalize_unwraps_google_but_leaves_plain_urls(sandbox, url, expected):
    from drpc import images

    clean, _ = images.normalize(url, follow=False)
    assert clean == expected


def test_normalize_reports_what_it_did(sandbox):
    from drpc import images

    _, notes = images.normalize(
        "https://www.google.com/imgres?imgurl=https%3A%2F%2Fx.test%2Fa.png", follow=False
    )
    assert notes == ["unwrapped the Google Images link"]


def test_reachable_rejects_non_http_without_touching_the_network(sandbox):
    from drpc import images

    ok, detail = images.reachable("ftp://x.test/a.png")
    assert ok is False and "http" in detail


def test_reachable_accepts_a_bare_discord_asset_key(sandbox):
    from drpc import images

    assert images.reachable("my_asset")[0] is True
