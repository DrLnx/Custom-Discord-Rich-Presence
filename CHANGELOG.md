# Changelog

## 1.0.0

First public release.

### Added
- Windows support throughout: paths via `platformdirs`, a spawn-based daemon
  in place of `fork()`, an advisory pidfile lock in place of reading `/proc`,
  a pure-Python `tail -f`, and autostart through the per-user `Run` key.
- Generic Linux autostart via a `drpc.service` systemd user unit, alongside
  the existing Hyprland/Omarchy `autostart.lua` route.
- Standalone single-file executables for Linux and Windows, plus a
  `discord-rpc-cli` package on PyPI.
- `drpc new --blank`, `drpc logs -n`, `drpc autostart --method`.

### Changed
- Rebuilt the TUI: one centred column, floating profile picker and key sheet,
  modal Vim-style keys, a light and a dark theme.
- Rewrote the single script as an installable package.
- The daemon now clears the presence on the way out instead of leaving Discord
  to time it out, and stops within a second rather than up to a minute.
- CLI output is consistent and quieter.
