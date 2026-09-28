<div align="center">

# drpc

**Discord Rich Presence from the terminal.**

A background daemon, a small CLI, and a TUI for the parts that are
easier to see than to type.

[![release](https://img.shields.io/github/v/release/DrLnx/Custom-Discord-Rich-Presence?include_prereleases&sort=semver&color=5865F2&label=release)](https://github.com/DrLnx/Custom-Discord-Rich-Presence/releases)
[![python](https://img.shields.io/badge/python-3.10%2B-3776AB)](https://www.python.org/)
[![platform](https://img.shields.io/badge/platform-Linux%20%7C%20Windows-444)](#where-things-live)
[![license](https://img.shields.io/badge/license-MIT-green)](LICENSE)

[Install](#install) · [Quick start](#quick-start) · [The UI](#the-ui) · [Commands](#commands) · [Profiles](#profiles)

</div>

> [!NOTE]
> **This is an alpha.** It works, and it is in daily use — but the config
> format and the CLI surface can still move before `1.0`. Pin a tag if that
> matters to you.

```
 ● drpc  vscode                          ● live · 02:14:07 · vscode
 ──────────────────────────────────────────────────────────────────
 ╭─ preview ──────────────────────────────────────────────────────╮
 │  PLAYING A GAME                                                │
 │                                                                │
 │  ┌────┐  Visual Studio Code                                    │
 │  │▓▓▓▓│  Developing for N3XT                                   │
 │  └────┘  02:14:07 elapsed                                      │
 │                                                                │
 │    Join our Discord     Website                                │
 ╰────────────────────────────────────────────────────────────────╯

  identity
   name           Visual Studio Code
   client_id      383226320970055681

  activity
   type            playing  listening  watching  competing
   headline        name  state  details
   details        Developing for N3XT
   timer          ● counting up since launch
 ──────────────────────────────────────────────────────────────────
 j k move   i edit   p profiles   a apply   x start/stop   ? keys
```

## Install

### Standalone binary

No Python required. One file, nothing to uninstall.

```bash
# Linux
curl -L -o ~/.local/bin/drpc \
  https://github.com/DrLnx/Custom-Discord-Rich-Presence/releases/latest/download/drpc-linux-x86_64
chmod +x ~/.local/bin/drpc
```

On Windows, grab `drpc-windows-x86_64.exe` from the [latest release][releases],
rename it to `drpc.exe`, and drop it anywhere on your `PATH`.

### With pipx or uv

Needs Python 3.10+. Until the first stable release the package installs from
git rather than PyPI:

```bash
pipx install git+https://github.com/DrLnx/Custom-Discord-Rich-Presence
# or
uv tool install git+https://github.com/DrLnx/Custom-Discord-Rich-Presence
```

[releases]: https://github.com/DrLnx/Custom-Discord-Rich-Presence/releases/latest

## Quick start

```bash
drpc                 # open the UI, fill in the fields, press a to apply
drpc start           # or go straight to broadcasting the active profile
drpc status
drpc autostart enable
```

You need a Discord application ID. Create one at
[discord.com/developers/applications][apps] — the ID on the *General
Information* page is the `client_id`. The application's name is what Discord
shows on the top line of the presence.

[apps]: https://discord.com/developers/applications

## The UI

Keys are modal, like a Vim buffer: rows are the focus stops, plain letters are
commands, and you step into a field on purpose.

| key | |
|---|---|
| `j` `k` | next / previous field |
| `i` `enter` | edit the focused field · `esc` to back out |
| `h` `l` | cycle options, flip toggles |
| `d` | clear the focused field |
| `p` | switch profile (filterable) |
| `n` `D` | new / delete profile |
| `s` `a` | save · save and apply |
| `x` | start / stop broadcasting |
| `c` | check that Discord can load the image URLs |
| `T` | light / dark |
| `?` | the full key sheet |

## Commands

| | |
|---|---|
| `drpc start [profile]` | broadcast in the background |
| `drpc stop` | clear the presence |
| `drpc restart` | reload the config, keeping the elapsed timer |
| `drpc status` | what is live, and for how long |
| `drpc list` | every profile |
| `drpc use <profile>` | set the default |
| `drpc new <name> [--copy other] [--blank]` | |
| `drpc rm <name>` | |
| `drpc set <key> <value> [-p profile]` | `drpc set details "Shipping"` |
| `drpc button <1\|2> <label> <url>` | |
| `drpc check` | verify image URLs and button links |
| `drpc try <url>` | test an image URL without saving it |
| `drpc edit` | open `config.json` in `$EDITOR` |
| `drpc autostart [enable\|disable\|status]` | |
| `drpc logs [-f]` | the daemon log |
| `drpc path` | where everything lives |

## Profiles

A profile is one presence. Switch between them with `drpc use` or `p` in the UI.

```json
{
  "active": "vscode",
  "profiles": {
    "vscode": {
      "client_id": "383226320970055681",
      "name": "Visual Studio Code",
      "activity_type": "playing",
      "status_display_type": "name",
      "details": "Developing for N3XT",
      "state": "",
      "large_image": "https://example.com/icon.png",
      "large_text": "Visual Studio Code",
      "timer": true,
      "buttons": [{ "label": "Website", "url": "https://n3xt-agency.com" }]
    }
  }
}
```

`activity_type` is one of `playing`, `listening`, `watching`, `competing`.
`status_display_type` picks which line Discord shows next to your name:
`name`, `state`, or `details`.

## Images that actually render

> [!IMPORTANT]
> Discord fetches image URLs server-side, through `media.discordapp.net`. A URL
> that loads fine in your browser can still come back blank — hosts that block
> hotlinking, SVGs, and Google Images result pages all fail this way, silently.

`drpc check` (and `c` in the UI) hands the URL to Discord, takes the proxy
link back, and tries to pull the image through it. That is the only answer
that counts. Google Images links are unwrapped automatically.

Hosts that work reliably: `raw.githubusercontent.com`, jsDelivr, Imgur, or
anything you serve yourself.

## Autostart

| platform | mechanism |
|---|---|
| Linux | a `drpc.service` systemd user unit |
| Linux + Hyprland/Omarchy | a line in `~/.config/hypr/autostart.lua` |
| Windows | the per-user `Run` registry key |

`drpc autostart enable` picks the right one; `--method` overrides it. Discord
does not need to be running first — drpc waits and connects when it appears.

## Where things live

| | Linux | Windows |
|---|---|---|
| config | `~/.config/drpc/config.json` | `%APPDATA%\drpc\config.json` |
| log | `~/.local/state/drpc/drpc.log` | `%LOCALAPPDATA%\drpc\drpc.log` |
| runtime | `$XDG_RUNTIME_DIR/drpc/` | alongside the log |

`drpc path` prints them.

## Development

```bash
git clone https://github.com/DrLnx/Custom-Discord-Rich-Presence
cd Custom-Discord-Rich-Presence
python -m venv .venv && .venv/bin/pip install -e '.[dev]'

.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/textual run --dev drpc.tui.app:DrpcApp   # live CSS reload
```

Releases are cut from a tag — see [RELEASING.md](RELEASING.md).

## License

[MIT](LICENSE) © N3XT Agency
