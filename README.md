# JA-RS485 — Jablotron alarm in Home Assistant over the JA-121T RS-485 interface

Custom Home Assistant integration for reading and controlling a **Jablotron JABLOTRON 100 / 100+** alarm system
through the **[JA-121T RS-485 bus interface](https://portal.jablotron.com/cs/sbernicove-rozhrani-rs-485)**
(ASCII protocol, 9600 Bd, 8N1 — per Jablotron manual MNN51111), typically connected via a USB↔RS-485 converter.

## Features

- **Alarm control panel** entity per section — arm (SET), arm partially (SETP), disarm (UNSET),
  with proper HA states: `disarmed`, `arming` (exit delay), `pending` (entry delay),
  `armed_away`, `armed_home` and `triggered` (intruder / fire / panic alarm)
- **Switch** entity per PG output (PGON / PGOFF), non-optimistic — state changes only after
  the panel confirms them
- **Diagnostic sensor** per section with the raw JA-121T state (`READY`, `ARMED`, `ARMED_PART`,
  `BLOCKED`, `SERVICE`, …) and active flags as attributes
- **Binary sensor** per peripheral (detector) decoded from the `PRFSTATE` bitmap — created
  automatically on first activation, or select positions explicitly in the integration options
  (numbers match the Devices tab in F-Link, 0 = control panel). Note: the protocol carries no
  peripheral names or types — rename entities in HA as needed
- **Entity filter** in the integration options — choose which sections, PG outputs and
  peripherals become entities (state queries are not restricted by code permissions, so
  everything the panel reports is visible by default)
- **Control permissions** in the integration options, mirroring the rights of the access
  code in F-Link: section control type (full / arm only / read only), which sections may be
  controlled, and whether/which PG outputs may be controlled. Disallowed commands are
  rejected locally with a clear error instead of hitting the panel with `NO_ACCESS`
  attempts (which would pollute the Jablotron event history)
- Sections and PG outputs are **discovered automatically** from the bus (initial `STATE` / `PGSTATE`
  query + spontaneous reports); new ones appear as entities without a restart
- **Push updates** — the JA-121T reports section and PG changes instantly. Detector states
  (PRFSTATE) are only broadcast every ~10 s by the panel, so the detector binary sensors
  are **informational only** — for any automation, route the detector through a PG output
  in F-Link (PG changes are pushed instantly). A full state resync runs every 5 minutes
  to recover anything lost to half-duplex bus collisions
- **Automatic reconnect** with backoff when the serial port disappears (e.g. USB re-plug);
  entities become `unavailable` while the link is down
- Config flow validates the connection and the access code before the entry is created

## Security notes

- All communication runs in a dedicated thread — nothing blocks the HA event loop.
- Commands are built exclusively from validated integers (sections 1–15, PG 1–128); the access
  code is charset-restricted at setup. Nothing user-supplied can inject extra commands into the line.
- The access code is stored in the HA config entry and is **never written to logs**.
- **Use a dedicated user code** for this integration with only the permissions it needs
  (which sections it may control, which PG outputs). Every command is logged in the Jablotron
  event history under that user.
- Failed commands (e.g. `ERROR: 3 NO_ACCESS`) are logged and arm/disarm actions surface the
  failure in the UI instead of pretending they succeeded.

## Requirements

- Home Assistant 2024.11 or newer
- JA-121T enrolled in the control panel, **Terminal** mode (default; set in F-Link → Internal settings)
- A USB↔RS-485 converter (FTDI/CH340/CP2102-based all work)

### Wiring (the two things everyone gets wrong)

1. **External 12 V supply is mandatory.** The RS-485 side of the JA-121T is galvanically
   isolated and is **not** powered from the Jablotron bus. Feed **12 V DC** (6–28 V per the
   manual) into the **+U/GND terminals on the RS-485 output side**. Without it the line only
   carries noise (single garbage bytes like `\x00`).
2. **Data line polarity:** JA-121T **A → converter D+**, **B → D−**, and connect the JA-121T
   output-side **GND** to the converter's ground. (RS-485 A/B labeling is not standardized —
   if you only get garbage with power present, swap A/B.)

## Installation

1. Copy `custom_components/ja_rs485/` into `config/custom_components/ja_rs485/`.
2. Restart Home Assistant.
3. **Settings → Devices & services → Add integration → JA-RS485.**
4. Pick the serial port — prefer the stable path `/dev/serial/by-id/usb-...` over `/dev/ttyUSB0`
   (survives reboots and re-plugs) — and enter the access code (with prefix if your system uses
   prefixes, e.g. `1*1234`).

## Services

Kept for backward compatibility and automations; the alarm/switch entities are the preferred way.

| Service | Command | Description |
|---------|---------|-------------|
| `ja_rs485.set_zone` | `SET n` | Arm a section (1–15) |
| `ja_rs485.set_zone_partial` | `SETP n` | Arm a section partially |
| `ja_rs485.unset_zone` | `UNSET n` | Disarm a section |
| `ja_rs485.pgon` | `PGON n` | Turn a PG output (1–128) on |
| `ja_rs485.pgoff` | `PGOFF n` | Turn a PG output off |

## Lovelace dashboard

`dashboards/jablotron_dashboard.yaml` auto-generates tiles for all sections (with arm/disarm
buttons) and PG outputs. It only needs the [auto-entities](https://github.com/thomasloven/lovelace-auto-entities)
plugin (HACS).

## Troubleshooting

| Symptom | Check |
|---------|-------|
| `invalid_auth` / `NO_ACCESS` in logs | Wrong code, wrong prefix, or the code lacks rights for that section/PG |
| `no_response` during setup | A/B wires swapped, missing GND, wrong port, or JA-121T not in Terminal mode |
| `unexpected_data` / single garbage bytes (`\x00`, `\xfc`) in the log | **Missing 12 V supply on the RS-485 side (+U/GND)** or swapped A/B polarity |
| Entities appear but never update | *Passive mode* enabled in F-Link — disable it so the module pushes changes |
| Everything drops to `unavailable` | USB converter disconnected; the integration reconnects automatically |

## License

MIT
