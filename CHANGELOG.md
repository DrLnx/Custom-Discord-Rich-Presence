# Changelog

## 0.1.0-alpha.1

First public preview. Everything below is relative to the single-file script
drpc grew out of, which was never released.

### Added
- Windows support throughout: paths via `platformdirs`, a spawn-based daemon
  in place of `fork()`, an advisory pidfile lock in place of reading `/proc`,
  a pure-Python `tail -f`, and autostart through the per-user `Run` key.
- Generic Linux autostart via a `drpc.service` systemd user unit, alongside
  the existing Hyprland/Omarchy `autostart.lua` route.
- Standalone single-file executables for Linux and Windows.
- `drpc new --blank`, `drpc logs -n`, `drpc autostart --method`.

### Changed
- Rebuilt the TUI: one centred column, floating profile picker and key sheet,
  modal Vim-style keys, a light and a dark theme.
- Rewrote the single script as an installable package.
- The daemon now clears the presence on the way out instead of leaving Discord
  to time it out, and stops within a second rather than up to a minute.
- CLI output is consistent and quieter.

### Fixed
- A freshly loaded profile is no longer marked as edited.
- A start stamp from the future (a clock moved back by NTP or a timezone fix)
  is anchored to now, so the elapsed timer counts instead of sitting at zero.
