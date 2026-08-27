"""The building blocks of the form.

Every row is a single focus stop that renders its own value, so plain letters
stay free for normal-mode commands.  Pressing ``i`` (or enter) swaps the
rendered value for a real Input and hands it focus; escape swaps back.
"""

from __future__ import annotations

from rich.markup import escape
from textual.containers import Horizontal
from textual.css.query import NoMatches
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Input, Label, Static


class Row(Horizontal, can_focus=True):
    """A label, a value, and an optional mark on the right."""

    DEFAULT_CLASSES = "row"

    class Changed(Message):
        def __init__(self, row: Row) -> None:
            super().__init__()
            self.row = row

        @property
        def control(self) -> Row:
            return self.row

    def __init__(self, key: str, label: str | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.key = key
        self.label = label or key

    def announce(self) -> None:
        self.post_message(self.Changed(self))


class TextRow(Row):
    """An editable string."""

    value = reactive("", init=False)
    mark = reactive("", init=False)
    editing = reactive(False, init=False)

    BINDINGS = [
        ("i,enter,a", "edit", "edit"),
        ("d", "clear", "clear"),
    ]

    def __init__(self, key: str, placeholder: str = "", label: str | None = None, **kwargs):
        super().__init__(key, label, **kwargs)
        self.placeholder = placeholder

    def compose(self):
        yield Label(self.label, classes="row-key")
        yield Static(classes="row-value")
        yield Input(placeholder=self.placeholder, select_on_focus=False,
                    classes="row-input")
        yield Static(classes="row-mark")

    def on_mount(self) -> None:
        self.query_one(Input).can_focus = False
        self._paint()

    # -- state ----------------------------------------------------------

    def watch_value(self) -> None:
        if not self.editing:
            self.query_one(Input).value = self.value
        self._paint()
        self.announce()

    def watch_mark(self) -> None:
        self._paint()

    def _paint(self) -> None:
        try:
            value_slot = self.query_one(".row-value", Static)
            mark_slot = self.query_one(".row-mark", Static)
        except NoMatches:  # not composed yet
            return
        if self.value:
            body = f"[$foreground]{escape(self.value)}[/]"
        else:
            body = f"[$text-disabled]{escape(self.placeholder)}[/]" if self.placeholder else ""
        value_slot.update(body)
        mark_slot.update(self.mark)

    # -- editing --------------------------------------------------------

    def action_edit(self) -> None:
        if self.editing:
            return
        self.editing = True
        self.add_class("editing")
        field = self.query_one(Input)
        field.can_focus = True
        field.value = self.value
        field.focus()
        field.cursor_position = len(field.value)

    def action_clear(self) -> None:
        self.value = ""

    def _stop_editing(self, commit: bool) -> None:
        if not self.editing:
            return
        field = self.query_one(Input)
        if commit:
            self.value = field.value.strip()
        else:
            field.value = self.value
        self.editing = False
        self.remove_class("editing")
        field.can_focus = False
        self._paint()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        event.stop()
        self._stop_editing(commit=True)
        self.focus()

    def on_input_blurred(self, event: Input.Blurred) -> None:
        event.stop()
        self._stop_editing(commit=True)

    def on_key(self, event) -> None:
        if self.editing and event.key == "escape":
            event.stop()
            event.prevent_default()
            self._stop_editing(commit=False)
            self.focus()

    def on_click(self) -> None:
        if not self.editing:
            self.focus()


class ChoiceRow(Row):
    """One of a handful of options, laid out inline."""

    value = reactive("", init=False)

    BINDINGS = [
        ("l,right,space,enter", "step(1)", "next"),
        ("h,left", "step(-1)", "previous"),
    ]

    def __init__(self, key: str, options, label: str | None = None, **kwargs):
        super().__init__(key, label, **kwargs)
        self.options = list(options)

    def compose(self):
        yield Label(self.label, classes="row-key")
        yield Static(classes="row-value")
        yield Static(classes="row-mark")

    def on_mount(self) -> None:
        self._paint()

    def watch_value(self) -> None:
        self._paint()
        self.announce()

    def _paint(self) -> None:
        try:
            value_slot = self.query_one(".row-value", Static)
        except NoMatches:
            return
        parts = []
        for option in self.options:
            if option == self.value:
                parts.append(f"[$text-primary on $primary-muted] {option} [/]")
            else:
                parts.append(f"[$text-disabled] {option} [/]")
        value_slot.update("".join(parts))

    def action_step(self, delta: int) -> None:
        try:
            index = self.options.index(self.value)
        except ValueError:
            index = 0
        self.value = self.options[(index + delta) % len(self.options)]

    def on_click(self) -> None:
        self.focus()
        self.action_step(1)


class ToggleRow(Row):
    """On or off, rendered as a status dot rather than a phone switch."""

    value = reactive(False, init=False)

    BINDINGS = [("space,enter,l,h,left,right", "toggle", "toggle")]

    def __init__(self, key: str, on_text: str, off_text: str,
                 label: str | None = None, **kwargs):
        super().__init__(key, label, **kwargs)
        self.on_text = on_text
        self.off_text = off_text

    def compose(self):
        yield Label(self.label, classes="row-key")
        yield Static(classes="row-value")
        yield Static(classes="row-mark")

    def on_mount(self) -> None:
        self._paint()

    def watch_value(self) -> None:
        self._paint()
        self.announce()

    def _paint(self) -> None:
        try:
            value_slot = self.query_one(".row-value", Static)
        except NoMatches:  # not composed yet
            return
        if self.value:
            body = f"[$success]●[/] [$foreground]{self.on_text}[/]"
        else:
            body = f"[$text-disabled]○ {self.off_text}[/]"
        value_slot.update(body)

    def action_toggle(self) -> None:
        self.value = not self.value

    def on_click(self) -> None:
        self.focus()
        self.action_toggle()


class SectionLabel(Static):
    """A lower-case heading, the only structure the form needs."""

    DEFAULT_CLASSES = "section"

    def __init__(self, title: str, **kwargs):
        super().__init__(title, **kwargs)
