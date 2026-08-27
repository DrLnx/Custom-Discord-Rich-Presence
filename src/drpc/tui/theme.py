"""Two themes: one accent on a neutral ramp, in dark and light."""

from __future__ import annotations

from textual.theme import Theme

_SHARED = {
    "primary": "#d97757",
    "secondary": "#7c8ea3",
    "accent": "#d97757",
    "success": "#7fb069",
    "warning": "#d9a441",
    "error": "#d1656b",
}

DARK = Theme(
    name="drpc-dark",
    dark=True,
    background="#111113",
    surface="#18181c",
    panel="#26262c",
    foreground="#d6d4d1",
    boost="#ffffff0e",
    variables={
        "block-cursor-background": "#d97757",
        "block-cursor-foreground": "#111113",
        "input-cursor-background": "#d97757",
        "input-cursor-foreground": "#111113",
        "input-selection-background": "#d9775740",
        "footer-background": "#111113",
        "footer-key-foreground": "#d97757",
        "scrollbar": "#26262c",
        "scrollbar-hover": "#3a3a42",
        "scrollbar-active": "#d97757",
        "border": "#26262c",
        "rule": "#26262c",
        "text-muted": "#8d8a86",
        "text-disabled": "#5c5a58",
    },
    **_SHARED,
)

LIGHT = Theme(
    name="drpc-light",
    dark=False,
    background="#faf9f7",
    surface="#ffffff",
    panel="#e6e3dd",
    foreground="#2b2a28",
    boost="#0000000d",
    variables={
        "block-cursor-background": "#c25f3f",
        "block-cursor-foreground": "#ffffff",
        "input-cursor-background": "#c25f3f",
        "input-cursor-foreground": "#ffffff",
        "input-selection-background": "#c25f3f30",
        "footer-background": "#faf9f7",
        "footer-key-foreground": "#c25f3f",
        "scrollbar": "#e6e3dd",
        "scrollbar-hover": "#cfcbc3",
        "scrollbar-active": "#c25f3f",
        "border": "#e0ddd6",
        "rule": "#e0ddd6",
        "text-muted": "#77736d",
        "text-disabled": "#a8a49d",
    },
    **{**_SHARED, "primary": "#c25f3f", "accent": "#c25f3f"},
)

THEMES = {DARK.name: DARK, LIGHT.name: LIGHT}
