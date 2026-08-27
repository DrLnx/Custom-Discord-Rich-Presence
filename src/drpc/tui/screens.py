"""Floating overlays: the profile picker, the key sheet, and small prompts."""

from __future__ import annotations

from rich.markup import escape
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Input, OptionList, Static
from textual.widgets.option_list import Option


class Picker(ModalScreen[str | None]):
    """Telescope, in miniature: a filtered list over a prompt."""

    BINDINGS = [
        ("escape", "dismiss_none", "cancel"),
        ("ctrl+j,down", "move(1)", "down"),
        ("ctrl+k,up", "move(-1)", "up"),
        ("enter", "choose", "select"),
    ]

    # width 62, minus the border and the panel and option padding
    INNER = 54

    def __init__(self, title: str, items: list[tuple[str, str, str]],
                 prompt: str = "") -> None:
        super().__init__()
        self.picker_title = title
        self.items = items  # (value, annotation, annotation style)
        self.prompt = prompt

    def compose(self) -> ComposeResult:
        with Vertical(id="picker"):
            yield OptionList(id="picker-list")
            with Horizontal(id="picker-prompt"):
                yield Static("[$primary]›[/]", classes="prompt-icon")
                yield Input(placeholder=self.prompt or "filter…", id="picker-input")

    def on_mount(self) -> None:
        self.query_one("#picker", Vertical).border_title = self.picker_title
        self._refill("")
        self.query_one("#picker-input", Input).focus()

    def _refill(self, needle: str) -> None:
        needle = needle.strip().lower()
        option_list = self.query_one("#picker-list", OptionList)
        option_list.clear_options()
        self.matches = [item for item in self.items if needle in item[0].lower()]
        for value, note, style in self.matches:
            gap = " " * max(1, self.INNER - len(value) - len(note))
            annotation = f"[{style}]{escape(note)}[/]" if note else ""
            option_list.add_option(Option(f"{escape(value)}{gap}{annotation}", id=value))
        if self.matches:
            option_list.highlighted = 0

    def on_input_changed(self, event: Input.Changed) -> None:
        self._refill(event.value)

    def action_move(self, delta: int) -> None:
        option_list = self.query_one("#picker-list", OptionList)
        if not self.matches:
            return
        current = option_list.highlighted or 0
        option_list.highlighted = (current + delta) % len(self.matches)

    def action_choose(self) -> None:
        option_list = self.query_one("#picker-list", OptionList)
        if option_list.highlighted is None or not self.matches:
            self.dismiss(None)
            return
        self.dismiss(self.matches[option_list.highlighted][0])

    def on_input_submitted(self, event: Input.Submitted) -> None:
        event.stop()
        self.action_choose()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        self.dismiss(str(event.option.id))

    def action_dismiss_none(self) -> None:
        self.dismiss(None)


class Prompt(ModalScreen[str | None]):
    """A single line of input, floating."""

    BINDINGS = [("escape", "dismiss_none", "cancel")]

    def __init__(self, title: str, placeholder: str = "", value: str = "") -> None:
        super().__init__()
        self.prompt_title = title
        self.placeholder = placeholder
        self.value = value

    def compose(self) -> ComposeResult:
        with Vertical(id="prompt"):
            with Horizontal(classes="prompt-line"):
                yield Static("[$primary]›[/]", classes="prompt-icon")
                yield Input(placeholder=self.placeholder, value=self.value, id="prompt-input")

    def on_mount(self) -> None:
        self.query_one("#prompt", Vertical).border_title = self.prompt_title
        self.query_one(Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.dismiss(event.value.strip() or None)

    def action_dismiss_none(self) -> None:
        self.dismiss(None)


class Confirm(ModalScreen[bool]):
    BINDINGS = [
        ("escape,n,q", "no", "no"),
        ("y,enter", "yes", "yes"),
    ]

    def __init__(self, question: str) -> None:
        super().__init__()
        self.question = question

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm"):
            yield Static(escape(self.question), classes="confirm-question")
            yield Static("[$primary]y[/] [$text-muted]yes[/]    "
                         "[$primary]n[/] [$text-muted]no[/]", classes="confirm-keys")

    def on_mount(self) -> None:
        self.query_one("#confirm", Vertical).border_title = "confirm"

    def action_yes(self) -> None:
        self.dismiss(True)

    def action_no(self) -> None:
        self.dismiss(False)


class KeySheet(ModalScreen[None]):
    """which-key, without the timing guesswork."""

    BINDINGS = [("escape,q,question_mark", "dismiss_sheet", "close")]

    GROUPS = [
        ("move", [
            ("j / k", "next / previous field"),
            ("g / G", "first / last field"),
            ("tab", "next field"),
        ]),
        ("edit", [
            ("i · enter", "edit the focused field"),
            ("esc", "stop editing, discard"),
            ("h / l", "cycle options, toggle"),
            ("d", "clear the focused field"),
        ]),
        ("profiles", [
            ("p", "switch profile"),
            ("n", "new profile"),
            ("D", "delete profile"),
        ]),
        ("presence", [
            ("s", "save to config.json"),
            ("a", "save and apply"),
            ("x", "start / stop"),
            ("c", "check image URLs"),
        ]),
        ("app", [
            ("T", "light / dark"),
            ("?", "this sheet"),
            ("q", "quit"),
        ]),
    ]

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="keysheet"):
            for title, rows in self.GROUPS:
                yield Static(title, classes="section")
                for keys, description in rows:
                    yield Static(
                        f"[$primary]{keys:<12}[/][$text-muted]{description}[/]",
                        classes="keyrow",
                    )

    def on_mount(self) -> None:
        self.query_one("#keysheet").border_title = "keys"

    def action_dismiss_sheet(self) -> None:
        self.dismiss(None)
