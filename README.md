# drpc

Discord Rich Presence from the terminal — a background daemon, a small CLI,
and a TUI for the parts that are easier to see than to type.

Runs on **Linux** and **Windows**.

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

**With pipx or uv** (needs Python 3.9+):

```bash
pipx install discord-rpc-cli     # or: uv tool install discord-rpc-cli
```

**Standalone binary** — no Python required. Grab `drpc-linux-x86_64` or
`drpc-windows-x86_64.exe` from the [latest release][releases].

```bash
# Linux
curl -L -o ~/.local/bin/drpc \
  https://github.com/n3xt-agency/drpc/releases/latest/download/drpc-linux-x86_64
chmod +x ~/.local/bin/drpc
```

On Windows, drop `drpc.exe` anywhere on your `PATH`.

[releases]: https://github.com/n3xt-agency/drpc/releases/latest

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

Discord fetches image URLs server-side, through `media.discordapp.net`. A URL
that loads fine in your browser can still come back blank — hosts that block
hotlinking, SVGs, and Google Images result pages all fail this way, silently.

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
git clone https://github.com/n3xt-agency/drpc && cd drpc
python -m venv .venv && .venv/bin/pip install -e '.[dev]'
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/textual run --dev drpc.tui.app:DrpcApp   # live CSS reload
```

## License

MIT
