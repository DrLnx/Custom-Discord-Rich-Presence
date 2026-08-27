"""Shared console styling, so the CLI and the TUI look like one program."""

from __future__ import annotations

from rich.console import Console
from rich.theme import Theme

# One accent, everything else on a grey ramp. Named after roles rather than
# colours so the TUI theme and this stay in step.
THEME = Theme(
    {
        "accent": "#d97757",
        "ok": "#7fb069",
        "bad": "#d1656b",
        "warn": "#d9a441",
        "dim": "grey50",
        "faint": "grey37",
        "key": "grey62",
        "head": "bold",
    }
)

console = Console(theme=THEME, highlight=False, soft_wrap=True)
err_console = Console(theme=THEME, highlight=False, soft_wrap=True, stderr=True)

MARKS = {True: "[ok]✓[/]", False: "[bad]✗[/]", None: "[warn]·[/]"}


def line(text: str = "") -> None:
    console.print(f"  {text}" if text else "")


def head(text: str) -> None:
    console.print(f"\n  [head]{text}[/]")


def kv(key: str, value: str, width: int = 11) -> None:
    console.print(f"  [key]{key:<{width}}[/]{value}")


def note(text: str) -> None:
    console.print(f"  [faint]{text}[/]")


def verdict(ok: bool | None, text: str) -> None:
    console.print(f"  {MARKS[ok]} {text}")


def fail(text: str) -> None:
    err_console.print(f"  [bad]drpc[/] {text}")


def dot(live: bool) -> str:
    return "[ok]●[/]" if live else "[faint]○[/]"


def clock(seconds: int | None) -> str:
    if seconds is None:
        return "--:--:--"
    hours, rest = divmod(max(0, int(seconds)), 3600)
    minutes, secs = divmod(rest, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"
