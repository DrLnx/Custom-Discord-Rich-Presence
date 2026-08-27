"""The drpc terminal UI.

One centred column, no permanent chrome: profiles, keys, and prompts all
arrive as floating overlays.  Rows are the focus stops and plain letters are
commands, so editing is something you step into deliberately.
"""

from __future__ import annotations

import json

from rich.markup import escape
from textual import work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Static

from .. import config, daemon, images
from ..errors import Fail
from ..ui import clock
from .screens import Confirm, KeySheet, Picker, Prompt
from .theme import THEMES
from .widgets import ChoiceRow, Row, SectionLabel, TextRow, ToggleRow

ACTIVITY_HEADERS = {
    "playing": "PLAYING A GAME",
    "listening": "LISTENING TO",
    "watching": "WATCHING",
    "competing": "COMPETING IN",
}

IDENTITY = [
    ("name", "name", "Visual Studio Code"),
    ("client_id", "client_id", "Discord application ID"),
]
TEXT = [
    ("details", "details", "first line"),
    ("state", "state", "second line, optional"),
]
ASSETS = [
    ("large_image", "large_image", "https://… a direct .png link"),
    ("large_text", "large_text", "hover text"),
    ("large_url", "large_url", "click-through link, optional"),
    ("small_image", "small_image", "https://… optional"),
    ("small_text", "small_text", "hover text"),
    ("small_url", "small_url", "click-through link, optional"),
]
BUTTONS = [
    ("b0_label", "1 · label", "shown on the button"),
    ("b0_url", "1 · url", "https://…"),
    ("b1_label", "2 · label", "shown on the button"),
    ("b1_url", "2 · url", "https://…"),
]

HINTS = (
    "[$text-disabled]j k[/] move   [$text-disabled]i[/] edit   "
    "[$text-disabled]p[/] profiles   [$text-disabled]a[/] apply   "
    "[$text-disabled]x[/] start/stop   [$text-disabled]?[/] keys"
)


class DrpcApp(App):
    TITLE = "drpc"
    CSS_PATH = "app.tcss"
    ENABLE_COMMAND_PALETTE = False

    BINDINGS = [
        ("j,down", "focus_next", "next"),
        ("k,up", "focus_previous", "previous"),
        ("g", "focus_edge(0)", "first"),
        ("G", "focus_edge(-1)", "last"),
        ("p", "profiles", "profiles"),
        ("n", "new_profile", "new"),
        ("D", "delete_profile", "delete"),
        ("s", "save", "save"),
        ("a", "apply", "apply"),
        ("x", "toggle_daemon", "start/stop"),
        ("c", "check", "check"),
        ("T", "next_theme", "theme"),
        ("question_mark", "keys", "keys"),
        ("q,ctrl+c", "leave", "quit"),
        # the modifier forms keep working while a field is being edited
        ("ctrl+s", "save", "save"),
        ("ctrl+r", "apply", "apply"),
    ]

    def __init__(self, cfg: dict | None = None) -> None:
        super().__init__()
        self.cfg = cfg if cfg is not None else config.load()
        self.profile_name = self.cfg.get("active")
        if self.profile_name not in self.cfg.get("profiles", {}):
            self.profile_name = next(iter(self.cfg["profiles"]))
        self.dirty = False
        self.loading = False
        self.marks: dict[str, bool | None] = dict.fromkeys(config.IMAGE_KEYS)

    # -- layout ---------------------------------------------------------

    def compose(self) -> ComposeResult:
        with Vertical(id="shell"):
            with Horizontal(id="topbar"):
                yield Static(id="brand")
                yield Static(id="live")
            with VerticalScroll(id="body"):
                yield Static(id="preview")
                yield SectionLabel("identity")
                yield from self._text_rows(IDENTITY)
                yield SectionLabel("activity")
                yield ChoiceRow("activity_type", config.ACTIVITY_TYPES,
                                label="type", id="r-activity_type")
                yield ChoiceRow("status_display_type", config.DISPLAY_TYPES,
                                label="headline", id="r-status_display_type")
                yield from self._text_rows(TEXT)
                yield ToggleRow("timer", "counting up since launch", "off",
                                label="timer", id="r-timer")
                yield SectionLabel("assets")
                yield from self._text_rows(ASSETS)
                yield SectionLabel("buttons")
                yield from self._text_rows(BUTTONS)
            yield Static(HINTS, id="hints")

    def _text_rows(self, spec):
        for key, label, placeholder in spec:
            yield TextRow(key, placeholder=placeholder, label=label, id=f"r-{key}")

    def on_mount(self) -> None:
        for theme in THEMES.values():
            self.register_theme(theme)
        self.theme = self.cfg.get("theme") if self.cfg.get("theme") in THEMES else "drpc-dark"
        self.query_one("#preview", Static).border_title = "preview"
        self.load_profile()
        self.tick()
        self.set_interval(1.0, self.tick)
        rows = self.query(Row)
        if rows:
            rows.first().focus()

    # -- profile <-> form ------------------------------------------------

    @property
    def profile(self) -> dict:
        return self.cfg["profiles"][self.profile_name]

    def row(self, key: str) -> Row:
        return self.query_one(f"#r-{key}", Row)

    def load_profile(self) -> None:
        self.loading = True
        profile = self.profile
        for key, _, _ in IDENTITY + TEXT + ASSETS:
            self.row(key).value = str(profile.get(key) or "")
        self.row("activity_type").value = (profile.get("activity_type") or "playing").lower()
        self.row("status_display_type").value = (
            profile.get("status_display_type") or "name"
        ).lower()
        self.row("timer").value = bool(profile.get("timer", True))
        buttons = profile.get("buttons") or []
        for index in (0, 1):
            button = buttons[index] if index < len(buttons) else {}
            self.row(f"b{index}_label").value = button.get("label") or ""
            self.row(f"b{index}_url").value = button.get("url") or ""
        for key in config.IMAGE_KEYS:
            self.marks[key] = None
            self.row(key).mark = (
                "[$text-disabled]unchecked[/]" if self.row(key).value else ""
            )
        self.loading = False
        self.dirty = False
        self.update_preview()
        self.tick()

    def collect(self) -> None:
        profile = self.profile
        for key, _, _ in IDENTITY + TEXT + ASSETS:
            profile[key] = self.row(key).value.strip()
        profile["activity_type"] = self.row("activity_type").value
        profile["status_display_type"] = self.row("status_display_type").value
        profile["timer"] = self.row("timer").value
        buttons = []
        for index in (0, 1):
            label = self.row(f"b{index}_label").value.strip()
            url = self.row(f"b{index}_url").value.strip()
            if label and url:
                buttons.append({"label": label, "url": url})
        profile["buttons"] = buttons

    # -- rendering -------------------------------------------------------

    def update_preview(self) -> None:
        name = self.row("name").value or "(name)"
        details = self.row("details").value
        state = self.row("state").value
        activity = self.row("activity_type").value
        timer_on = self.row("timer").value

        live = daemon.status() is not None
        stamp = clock(daemon.elapsed()) if live and timer_on else "00:00:00"

        colour = {True: "$success", False: "$error", None: "$text-disabled"}[
            self.marks["large_image"]
        ]
        fill = "████" if self.row("large_image").value else "    "
        art = [
            "[$panel]┌────┐[/]",
            f"[$panel]│[/][{colour}]{fill}[/][$panel]│[/]",
            "[$panel]└────┘[/]",
        ]

        text = [f"[b]{escape(name)}[/b]"]
        if details:
            text.append(f"[$text-muted]{escape(details)}[/]")
        if state:
            text.append(f"[$text-muted]{escape(state)}[/]")
        if timer_on:
            text.append(f"[$text-disabled]{stamp} elapsed[/]")
        text = text[:3]
        text += [""] * (3 - len(text))

        lines = [f"[$text-disabled]{ACTIVITY_HEADERS.get(activity, 'PLAYING A GAME')}[/]", ""]
        lines += [f"{art_line}  {body}" for art_line, body in zip(art, text)]

        pills = []
        for index in (0, 1):
            label = self.row(f"b{index}_label").value.strip()
            url = self.row(f"b{index}_url").value.strip()
            if label and url:
                pills.append(f"[$foreground on $panel]  {escape(label)}  [/]")
        lines += ["", "   ".join(pills) if pills else "[$text-disabled]no buttons[/]"]

        self.query_one("#preview", Static).update("\n".join(lines))

    def tick(self) -> None:
        pid = daemon.status()
        session = daemon.session()
        if pid:
            right = (
                f"[$success]●[/] [b]live[/b] [$text-disabled]·[/] "
                f"[$text-muted]{clock(daemon.elapsed())}[/] [$text-disabled]·[/] "
                f"[$text-muted]{escape(str(session.get('profile') or '—'))}[/]"
            )
        else:
            right = "[$text-disabled]○ stopped · x to start[/]"

        flag = "[$primary]●[/] " if self.dirty else "[$text-disabled]·[/] "
        self.query_one("#brand", Static).update(
            f"{flag}[b]drpc[/b]  [$text-muted]{escape(self.profile_name)}[/]"
        )
        self.query_one("#live", Static).update(right)
        if self.is_mounted:
            self.update_preview()

    # -- events ----------------------------------------------------------

    def on_row_changed(self, event: Row.Changed) -> None:
        if self.loading:
            return
        self.dirty = True
        if event.row.key in config.IMAGE_KEYS:
            self.marks[event.row.key] = None
            event.row.mark = "[$text-disabled]unchecked[/]" if event.row.value else ""
        self.update_preview()

    # -- actions ---------------------------------------------------------

    def action_focus_edge(self, index: int) -> None:
        rows = list(self.query(Row))
        if rows:
            rows[index].focus()

    def action_next_theme(self) -> None:
        names = list(THEMES)
        self.theme = names[(names.index(self.theme) + 1) % len(names)]
        self.cfg["theme"] = self.theme
        self.dirty = True

    def action_keys(self) -> None:
        self.push_screen(KeySheet())

    def action_save(self) -> bool:
        self.collect()
        self.cfg["active"] = self.profile_name
        try:
            config.save(self.cfg)
        except Exception as exc:
            self.notify(str(exc), severity="error", title="save failed")
            return False
        self.dirty = False
        self.notify(f"saved {self.profile_name}")
        self.tick()
        return True

    def action_apply(self) -> None:
        if self.action_save():
            self.run_daemon("restart" if daemon.status() else "start")

    def action_toggle_daemon(self) -> None:
        if daemon.status():
            self.run_daemon("stop")
        elif self.action_save():
            self.run_daemon("start")

    @work(thread=True, exclusive=True, group="daemon")
    def run_daemon(self, verb: str) -> None:
        try:
            if verb == "stop":
                message = "stopped" if daemon.stop() else "not running"
            elif verb == "restart":
                pid, _ = daemon.restart(self.profile_name)
                message = f"restarted · pid {pid}"
            else:
                pid = daemon.start(self.profile_name)
                message = f"broadcasting · pid {pid}"
        except Fail as exc:
            self.call_from_thread(self.notify, str(exc), severity="error")
            return
        except Exception as exc:  # pragma: no cover - defensive
            self.call_from_thread(self.notify, f"{type(exc).__name__}: {exc}",
                                  severity="error")
            return
        self.call_from_thread(self.notify, message)
        self.call_from_thread(self.tick)

    # -- profiles --------------------------------------------------------

    def action_profiles(self) -> None:
        running = daemon.session().get("profile") if daemon.status() else None
        active = self.cfg.get("active")
        items = []
        for name in self.cfg["profiles"]:
            if name == running:
                items.append((name, "● live", "$success"))
            elif name == active:
                items.append((name, "• active", "$primary"))
            else:
                items.append((name, "", "$text-disabled"))
        self.push_screen(Picker("profiles", items), self._switch_profile)

    def _switch_profile(self, name: str | None) -> None:
        if not name or name == self.profile_name:
            return
        self.collect()  # keep edits made before switching away
        self.profile_name = name
        self.load_profile()
        self.dirty = True

    def action_new_profile(self) -> None:
        self.push_screen(Prompt("new profile", "name"), self._create_profile)

    def _create_profile(self, name: str | None) -> None:
        if not name:
            return
        if name in self.cfg["profiles"]:
            self.notify(f"{name} already exists", severity="error")
            return
        self.collect()
        self.cfg["profiles"][name] = json.loads(json.dumps(self.profile))
        self.profile_name = name
        self.load_profile()
        self.dirty = True
        self.notify(f"created {name}")

    def action_delete_profile(self) -> None:
        if len(self.cfg["profiles"]) == 1:
            self.notify("that is the only profile", severity="warning")
            return
        self.push_screen(Confirm(f"Delete profile '{self.profile_name}'?"),
                         self._delete_profile)

    def _delete_profile(self, confirmed: bool | None) -> None:
        if not confirmed:
            return
        name = self.profile_name
        del self.cfg["profiles"][name]
        self.profile_name = next(iter(self.cfg["profiles"]))
        if self.cfg.get("active") == name:
            self.cfg["active"] = self.profile_name
        self.load_profile()
        self.dirty = True
        self.notify(f"deleted {name}")

    # -- image checking ---------------------------------------------------

    def action_check(self) -> None:
        pending = [key for key in config.IMAGE_KEYS if self.row(key).value]
        if not pending:
            self.notify("no image URLs to check")
            return
        for key in pending:
            self.row(key).mark = "[$warning]checking…[/]"
        self.check_images()

    @work(thread=True, exclusive=True, group="check")
    def check_images(self) -> None:
        """Network plus a Discord round trip, so well off the UI thread."""
        client_id = self.row("client_id").value
        for key in config.IMAGE_KEYS:
            url = self.row(key).value
            if not url:
                self.call_from_thread(self._set_mark, key, None, "")
                continue
            clean, _ = images.normalize(url)
            if clean != url:
                self.call_from_thread(self._set_value, key, clean)
            ok, detail = images.verify(clean, client_id)
            self.call_from_thread(self._set_mark, key, ok, detail)

        if daemon.status():  # the probe borrowed the RPC slot; hand it back
            try:
                daemon.restart(self.profile_name)
            except Fail:
                pass
            self.call_from_thread(self.tick)

    def _set_mark(self, key: str, ok: bool | None, detail: str) -> None:
        self.marks[key] = ok
        colour = {True: "$success", False: "$error", None: "$warning"}[ok]
        label = {True: "ok", False: "fail", None: "?"}[ok]
        self.row(key).mark = (
            f"[{colour}]{label}[/] [$text-disabled]{escape(detail)}[/]" if detail else ""
        )
        self.update_preview()

    def _set_value(self, key: str, value: str) -> None:
        self.row(key).value = value

    # -- leaving ----------------------------------------------------------

    def action_leave(self) -> None:
        self.collect()
        if not self.dirty:
            self.exit()
            return
        self.push_screen(Confirm("Discard unsaved changes?"), self._maybe_exit)

    def _maybe_exit(self, confirmed: bool | None) -> None:
        if confirmed:
            self.exit()


def run() -> None:
    DrpcApp().run()
