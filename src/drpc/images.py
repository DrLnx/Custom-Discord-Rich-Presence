"""Working out whether Discord will actually render an image URL.

Discord wraps whatever string it is given in ``mp:external/…`` without
checking that it points at an image, so a Google Images page URL "succeeds"
and then renders blank.  Unwrap and verify here instead.
"""

from __future__ import annotations

import urllib.error
import urllib.parse
import urllib.request

BROWSER_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)
SHORTENERS = {"images.app.goo.gl", "goo.gl", "g.co", "share.google"}


def _unwrap_google(url: str) -> str | None:
    """Pull the real image URL out of a google.com wrapper, if there is one."""
    try:
        parts = urllib.parse.urlsplit(url)
    except ValueError:
        return None
    host = parts.netloc.lower().split(":")[0]
    if host != "google.com" and not host.endswith(".google.com"):
        return None
    query = urllib.parse.parse_qs(parts.query)
    for key in ("imgurl", "imgrefurl", "url", "u", "q", "media"):
        for candidate in query.get(key, []):
            if candidate.startswith(("http://", "https://")):
                return candidate
    return None


def _follow_redirect(url: str) -> str | None:
    request = urllib.request.Request(
        url, method="HEAD", headers={"User-Agent": BROWSER_UA}
    )
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            return response.url
    except Exception:
        return None


def normalize(url: str, follow: bool = True) -> tuple[str, list[str]]:
    """Return (clean_url, notes) with Google wrappers and short links resolved."""
    url = (url or "").strip()
    notes: list[str] = []
    if not url:
        return url, notes

    host = urllib.parse.urlsplit(url).netloc.lower().split(":")[0]
    if follow and host in SHORTENERS:
        resolved = _follow_redirect(url)
        if resolved and resolved != url:
            url = resolved
            notes.append("followed the short link")

    for _ in range(4):  # wrappers occasionally nest
        inner = _unwrap_google(url)
        if not inner:
            break
        url = urllib.parse.unquote(inner)
        notes.append("unwrapped the Google Images link")

    return url, notes


def reachable(url: str) -> tuple[bool, str]:
    """Fetch a little of the URL ourselves. Returns (ok, description)."""
    if not url:
        return True, "not set"
    if url.startswith("mp:") or "/" not in url:
        return True, "Discord asset key"
    if not url.startswith(("http://", "https://")):
        return False, "not an http(s) URL"
    request = urllib.request.Request(url, headers={"User-Agent": BROWSER_UA})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            ctype = (response.headers.get("Content-Type") or "").split(";")[0].strip()
            body = response.read(2048)
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403):
            return False, (
                f"HTTP {exc.code} — the host blocks hotlinking, so Discord "
                "cannot fetch it either"
            )
        return False, f"HTTP {exc.code}"
    except Exception as exc:
        return False, f"unreachable ({type(exc).__name__})"

    if ctype.startswith("image/"):
        if ctype == "image/svg+xml":
            return False, "SVG — Discord will not render it, use PNG or JPG"
        if len(body) < 100:
            return False, f"{ctype}, but suspiciously tiny"
        return True, ctype
    if body[:15].lstrip().lower().startswith((b"<!doctype", b"<html")):
        return False, "an HTML page, not an image file"
    return False, f"content-type {ctype or 'unknown'}"


def discord_can_load(url: str, client_id: str) -> tuple[bool | None, str]:
    """The authoritative check: can Discord's own CDN fetch this image?

    Local reachability is not enough — Discord fetches server-side through
    media.discordapp.net.  Hand the URL to Discord, take the ``mp:external``
    it hands back, and try to pull the image through the proxy the client
    uses.  Returns (ok, detail), or (None, reason) when the probe cannot run.
    """
    try:
        from pypresence import Presence
    except ImportError:
        return None, "pypresence missing"

    rpc = None
    try:
        rpc = Presence(str(client_id))
        rpc.connect()
        result = rpc.update(details="checking…", large_image=url)
        proxy_key = ((result.get("data") or {}).get("assets") or {}).get("large_image", "")
    except Exception as exc:
        return None, f"Discord not reachable ({type(exc).__name__})"
    finally:
        if rpc:
            try:
                rpc.close()
            except Exception:
                pass

    if not proxy_key.startswith("mp:external/"):
        return None, "Discord returned no proxy URL"
    proxy = "https://media.discordapp.net/external/" + proxy_key.removeprefix("mp:external/")
    request = urllib.request.Request(proxy, headers={"User-Agent": BROWSER_UA})
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            ctype = (response.headers.get("Content-Type") or "").split(";")[0]
            if ctype.startswith("image/"):
                return True, f"loads in Discord ({ctype})"
            return False, f"Discord served {ctype or 'no image'}"
    except urllib.error.HTTPError as exc:
        if exc.code == 415:
            return False, "Discord rejects this file type (needs PNG/JPG/GIF/WebP)"
        if exc.code == 404:
            return False, "Discord could not fetch it (host blocks Discord, or dead link)"
        return False, f"Discord proxy returned HTTP {exc.code}"
    except Exception as exc:
        return False, f"Discord proxy unreachable ({type(exc).__name__})"


def verify(url: str, client_id: str) -> tuple[bool | None, str]:
    """Local fetch first, then ask Discord — the answer that actually counts."""
    ok, detail = reachable(url)
    if not ok:
        return False, detail
    verdict, vdetail = discord_can_load(url, client_id)
    if verdict is None:
        return None, vdetail
    return verdict, vdetail
