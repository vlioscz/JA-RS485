# Changelog

## 0.3.0

- **F-Link CSV/TXT import** — a new "Import from F-Link" step in the integration
  options. Upload the Sections / PG outputs / Devices page exports (any order —
  the file type is detected from the header, Czech and English exports and
  Windows-1250/UTF-8/UTF-16 encodings supported) and the entities get their real
  names. Manual renames in HA stay on top. The PG export can also configure the
  integration: the Function column sets the impulse-PG (button) list and hides
  unused outputs (Function = Off).
- Options steps reorganised into a menu (filters & permissions / F-Link import);
  editing one step no longer discards options managed by the other.

## 0.2.0

- **Impulse PG buttons** — PGs configured as impulse in F-Link can be listed in the
  integration options and become stateless `button` entities (press = PGON) instead
  of switches.
- **Device triggers** — intruder / fire / panic / any alarm (optionally filtered to
  a section) can now be picked directly in the UI automation editor.
- `CHANGELOG.md` added.

## 0.1.2

First public release (HACS default-store submission).

- Alarm control panel per section (SET / SETP / UNSET) with entry/exit delay and
  triggered states.
- Switch per PG output (instant push updates), diagnostic sensor per section.
- Peripheral (detector) binary sensors decoded from PRFSTATE — informational only
  (the panel broadcasts detector states only every ~10 s); route detectors through
  PG outputs for automations.
- Options: entity visibility filters, control permissions mirroring F-Link code
  rights, range input (e.g. `8-20`).
- Reconfigure flow, `ja_rs485_alarm` events, bus connection sensor, diagnostics
  download (access code redacted).
- Robust threaded serial client: automatic reconnect with backoff,
  half-duplex-aware query spacing, full state resync every 5 minutes.
- Brand icon/logo served locally by Home Assistant 2026.3+.

## 0.1.1

Internal pre-release: full rewrite of the original prototype — working JA-121T
protocol (access-code prefixed commands, STATE/PG/PRFSTATE/flag parsing), fixed
integration setup, config flow with connection validation.
