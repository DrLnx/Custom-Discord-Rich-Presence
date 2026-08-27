"""The drpc command line."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
import time

from . import autostart, config, daemon, images, ui
from .errors import Fail
from .paths import CONFIG, LOG, PID, WINDOWS

__version__ = "1.0.0"


# --- daemon ----------------------------------------------------------------

def cmd_start(args) -> None:
    pid = daemon.start(args.profile)
    name = daemon.session().get("profile", args.profile or "?")
    ui.line(f"{ui.dot(True)} broadcasting [head]{name}[/]  [faint]pid {pid}[/]")


def cmd_serve(args) -> None:
    daemon.serve(args.profile, args.started_at or int(time.time()))


def cmd_stop(_args) -> None:
    ui.line("stopped" if daemon.stop() else "[faint]not running[/]")


def cmd_restart(args) -> None:
    pid, carried = daemon.restart(args.profile, args.reset_timer)
    name = daemon.session().get("profile", args.profile or "?")
    ui.line(f"{ui.dot(True)} restarted [head]{name}[/]  [faint]pid {pid}[/]")
    if carried is not None:
        ui.note(f"timer kept running — {ui.clock(carried)} elapsed")


def cmd_status(_args) -> None:
    pid = daemon.status()
    if not pid:
        ui.line(f"{ui.dot(False)} [faint]stopped[/]")
        return
    session = daemon.session()
    cfg = config.load()
    profile = cfg.get("profiles", {}).get(session.get("profile"), {})

    ui.line(
        f"{ui.dot(True)} [head]live[/]  [dim]{ui.clock(daemon.elapsed())}[/]"
        f"  [faint]pid {pid}[/]"
    )
    ui.line()
    ui.kv("profile", str(session.get("profile") or "—"))
    for key in ("name", "details", "state"):
        if profile.get(key):
            ui.kv(key, str(profile[key]))
    for button in profile.get("buttons") or []:
        ui.kv("button", f"{button.get('label')} [faint]→ {button.get('url')}[/]")


# --- profiles --------------------------------------------------------------

def cmd_list(_args) -> None:
    cfg = config.load()
    active = cfg.get("active")
    running = daemon.session().get("profile") if daemon.status() else None
    width = max((len(n) for n in cfg["profiles"]), default=8) + 2
    for name, profile in cfg["profiles"].items():
        mark = ui.dot(True) if name == running else ("[accent]•[/]" if name == active else " ")
        label = f"[head]{name}[/]" if name == active else name
        summary = profile.get("name") or "—"
        details = profile.get("details") or ""
        pad = " " * max(0, width - len(name))
        ui.line(f"{mark} {label}{pad}[dim]{summary}[/]"
                + (f"  [faint]{details}[/]" if details else ""))
    ui.line()
    ui.note("[accent]•[/] active    [ok]●[/] broadcasting")


def cmd_use(args) -> None:
    cfg = config.load()
    name, _ = config.get_profile(cfg, args.profile)
    cfg["active"] = name
    config.save(cfg)
    ui.line(f"active profile [head]{name}[/]")
    if daemon.status():
        ui.note("drpc restart — to switch the live presence")


def cmd_new(args) -> None:
    cfg = config.load()
    if args.profile in cfg["profiles"]:
        raise Fail(f"profile {args.profile!r} already exists")
    if args.blank:
        cfg["profiles"][args.profile] = config.blank_profile()
        source = "a blank profile"
    else:
        name, base = config.get_profile(cfg, args.copy)
        cfg["profiles"][args.profile] = json.loads(json.dumps(base))
        source = f"{name!r}"
    config.save(cfg)
    ui.line(f"created [head]{args.profile}[/] [faint]from {source}[/]")


def cmd_rm(args) -> None:
    cfg = config.load()
    name, _ = config.get_profile(cfg, args.profile)
    if len(cfg["profiles"]) == 1:
        raise Fail("cannot delete the only profile")
    del cfg["profiles"][name]
    if cfg.get("active") == name:
        cfg["active"] = next(iter(cfg["profiles"]))
    config.save(cfg)
    ui.line(f"deleted [head]{name}[/]")


# --- editing ---------------------------------------------------------------

def cmd_set(args) -> None:
    cfg = config.load()
    name, profile = config.get_profile(cfg, args.profile)
    node, parts = profile, args.key.split(".")
    for part in parts[:-1]:
        node = node[int(part)] if isinstance(node, list) else node.setdefault(part, {})
    leaf = parts[-1]
    value = config.coerce(args.value)

    if leaf in config.IMAGE_KEYS and isinstance(value, str) and value:
        value = _vet_image(value, profile.get("client_id", ""))

    if isinstance(node, list):
        node[int(leaf)] = value
    else:
        node[leaf] = value
    config.save(cfg)
    ui.line(f"[head]{name}[/].[dim]{args.key}[/] = {value!r}")
    if daemon.status():
        ui.note("drpc restart — to apply")


def cmd_button(args) -> None:
    cfg = config.load()
    name, profile = config.get_profile(cfg, args.profile)
    buttons = profile.setdefault("buttons", [])
    while len(buttons) < args.slot:
        buttons.append({"label": "", "url": ""})
    buttons[args.slot - 1] = {"label": args.label, "url": args.url}
    profile["buttons"] = [b for b in buttons[:2] if b.get("label") and b.get("url")]
    config.save(cfg)
    ui.line(f"[head]{name}[/] button {args.slot}  {args.label} [faint]→ {args.url}[/]")
    if daemon.status():
        ui.note("drpc restart — to apply")


def cmd_edit(_args) -> None:
    default = "notepad" if WINDOWS else "nvim"
    editor = os.environ.get("VISUAL") or os.environ.get("EDITOR") or default
    config.load()  # make sure the file exists before the editor opens it
    parts = [editor] if WINDOWS else shlex.split(editor)
    subprocess.call([*parts, str(CONFIG)])
    try:
        config.load()  # re-parse so a syntax error surfaces now, not at start
    except Fail as exc:
        raise Fail(
            f"{exc}\n  the presence keeps using the last good config until this is fixed"
        ) from exc
    ui.verdict(True, "config is valid")
    if daemon.status():
        ui.note("drpc restart — to apply")


# --- verification ----------------------------------------------------------

def _vet_image(url: str, client_id: str) -> str:
    clean, notes = images.normalize(url)
    for note in notes:
        ui.note(note)
    if clean != url:
        ui.note(f"→ {clean}")
    ok, detail = images.verify(clean, client_id)
    ui.verdict(ok, detail)
    if ok is False:
        ui.note("Discord will show a blank image. Open the picture directly")
        ui.note("(right-click → Open image in new tab) and copy that URL.")
    return clean


def cmd_try(args) -> None:
    cfg = config.load()
    name, profile = config.get_profile(cfg, args.profile)
    was_running = daemon.status() is not None
    clean = _vet_image(args.url, profile.get("client_id", ""))
    ok, _ = images.verify(clean, profile.get("client_id", ""))
    if was_running:
        daemon.restart()  # the probe borrowed the RPC slot; hand it back
    ui.line()
    if ok:
        ui.note(f"use it:  drpc set large_image '{clean}' -p {name}")
    else:
        ui.note("won't render. Right-click the picture itself → 'Open image in")
        ui.note("new tab' and use that link, from a host that allows hotlinking")
        ui.note("(github raw, jsdelivr, imgur, or your own site).")
        raise Fail("not usable")


def cmd_check(args) -> None:
    cfg = config.load()
    name, profile = config.get_profile(cfg, args.profile)
    was_running = daemon.status() is not None
    ui.line(f"profile [head]{name}[/]")
    ui.line()
    problems = 0

    for key in config.IMAGE_KEYS:
        url = (profile.get(key) or "").strip()
        if not url:
            ui.kv(key, "[faint]not set[/]", width=14)
            continue
        clean, _ = images.normalize(url)
        ok, detail = images.verify(clean, profile.get("client_id", ""))
        ui.console.print(f"  [key]{key:<14}[/]{ui.MARKS[ok]} [dim]{detail}[/]")
        if clean != url:
            ui.console.print(f"  {'':<14}[faint]unwraps to {clean}[/]")
            if ok:
                ui.console.print(f"  {'':<14}[faint]fix: drpc set {key} '{clean}' -p {name}[/]")
        if ok is False:
            problems += 1
            ui.console.print(
                f"  {'':<14}[faint]tip: open the picture itself "
                f"(right-click → 'Open image in new tab') and copy THAT url[/]"
            )

    for index, button in enumerate(profile.get("buttons") or [], 1):
        url = button.get("url", "")
        ok = url.startswith(("http://", "https://"))
        ui.console.print(f"  [key]{'button ' + str(index):<14}[/]{ui.MARKS[ok]} "
                         f"[dim]{url or 'no url'}[/]")
        if not ok:
            problems += 1

    if was_running:
        daemon.restart()
        ui.line()
        ui.note("presence restored, timer untouched")
    if problems:
        raise Fail(f"{problems} problem(s) found")
    ui.line()
    ui.verdict(True, "all good")


# --- system ----------------------------------------------------------------

def cmd_autostart(args) -> None:
    if args.action == "status":
        state = autostart.state()
        if not state:
            ui.line("[faint]autostart is not supported on this platform[/]")
            return
        for method, on in state.items():
            ui.console.print(f"  {ui.MARKS[on or None]} [key]{method:<10}[/]"
                             f"[dim]{'on' if on else 'off'}[/]")
        if any(state.values()):
            ui.line()
            ui.note("drpc starts with your desktop session")
        return

    notes = autostart.enable(args.method) if args.action == "enable" \
        else autostart.disable(args.method)
    ui.line(f"autostart [head]{'on' if args.action == 'enable' else 'off'}[/]")
    for note in notes:
        ui.note(note)


def cmd_logs(args) -> None:
    if args.follow:
        daemon.follow_log(args.lines)
        return
    for line in daemon.read_log(args.lines):
        print(line)


def cmd_path(_args) -> None:
    ui.kv("config", str(CONFIG), width=9)
    ui.kv("log", str(LOG), width=9)
    ui.kv("pidfile", str(PID), width=9)


def cmd_ui(_args) -> None:
    try:
        from .tui.app import run
    except ImportError as exc:  # pragma: no cover - only without the tui extra
        raise Fail(f"the UI is unavailable ({exc}). Try: drpc --help") from exc
    run()


# --- wiring ----------------------------------------------------------------

EPILOG = """\
examples:
  drpc                        open the interactive UI
  drpc start                  broadcast the active profile in the background
  drpc status                 show what is live and for how long
  drpc set details "Shipping the new site"
  drpc button 1 "Portfolio" https://example.com
  drpc autostart enable       start with the desktop session
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="drpc",
        description="Discord Rich Presence from the terminal.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=EPILOG,
    )
    parser.add_argument("-V", "--version", action="version", version=f"drpc {__version__}")
    sub = parser.add_subparsers(dest="cmd", metavar="<command>")

    def profile_flag(sp):
        sp.add_argument("-p", "--profile", help="profile to act on (default: active)")

    sp = sub.add_parser("start", help="start broadcasting in the background")
    sp.add_argument("profile", nargs="?", help="profile to broadcast (default: active)")
    sp.set_defaults(func=cmd_start)

    sp = sub.add_parser("_serve", help=argparse.SUPPRESS)
    sp.add_argument("--profile")
    sp.add_argument("--started-at", type=int)
    sp.set_defaults(func=cmd_serve)

    sub.add_parser("stop", help="stop broadcasting").set_defaults(func=cmd_stop)

    sp = sub.add_parser("restart", help="reload the config, keeping the timer running")
    sp.add_argument("profile", nargs="?")
    sp.add_argument("--reset-timer", action="store_true",
                    help="start the elapsed counter over from zero")
    sp.set_defaults(func=cmd_restart)

    sub.add_parser("status", help="show the running presence").set_defaults(func=cmd_status)
    sub.add_parser("list", help="list profiles").set_defaults(func=cmd_list)
    sub.add_parser("ui", help="open the interactive terminal UI").set_defaults(func=cmd_ui)

    sp = sub.add_parser("use", help="set the default profile")
    sp.add_argument("profile")
    sp.set_defaults(func=cmd_use)

    sp = sub.add_parser("new", help="create a profile")
    sp.add_argument("profile")
    sp.add_argument("--copy", help="profile to copy (default: active)")
    sp.add_argument("--blank", action="store_true", help="start from defaults instead")
    sp.set_defaults(func=cmd_new)

    sp = sub.add_parser("rm", help="delete a profile")
    sp.add_argument("profile")
    sp.set_defaults(func=cmd_rm)

    sp = sub.add_parser("set", help="set a field, e.g. drpc set details 'Building things'")
    sp.add_argument("key", help="field name, dotted for nesting (buttons.0.label)")
    sp.add_argument("value")
    profile_flag(sp)
    sp.set_defaults(func=cmd_set)

    sp = sub.add_parser("button", help="set button 1 or 2")
    sp.add_argument("slot", type=int, choices=(1, 2))
    sp.add_argument("label")
    sp.add_argument("url")
    profile_flag(sp)
    sp.set_defaults(func=cmd_button)

    sp = sub.add_parser("check", help="verify image URLs and button links")
    profile_flag(sp)
    sp.set_defaults(func=cmd_check)

    sp = sub.add_parser("try", help="test an image URL against Discord, without saving")
    sp.add_argument("url")
    profile_flag(sp)
    sp.set_defaults(func=cmd_try)

    sub.add_parser("edit", help="open the config in $EDITOR").set_defaults(func=cmd_edit)

    sp = sub.add_parser("autostart", help="start with the desktop session")
    sp.add_argument("action", nargs="?", default="status",
                    choices=("enable", "disable", "status"))
    sp.add_argument("--method", choices=("systemd", "hypr", "registry"),
                    help="mechanism to use (default: whatever fits this system)")
    sp.set_defaults(func=cmd_autostart)

    sp = sub.add_parser("logs", help="show the daemon log")
    sp.add_argument("-f", "--follow", action="store_true")
    sp.add_argument("-n", "--lines", type=int, default=50)
    sp.set_defaults(func=cmd_logs)

    sub.add_parser("path", help="print config and log locations").set_defaults(func=cmd_path)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.cmd is None:  # bare `drpc` opens the UI
            cmd_ui(args)
        else:
            args.func(args)
    except Fail as exc:
        ui.fail(str(exc))
        return 1
    except KeyboardInterrupt:
        return 130
    except BrokenPipeError:  # piping into head, etc.
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
