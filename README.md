<p align="center"><img src="brands/logo@2x.png" alt="JA-RS485" width="461"></p>

# JA-RS485 — Jablotron alarm in Home Assistant over the JA-121T RS-485 interface

**English** | [Čeština](README.cs.md)

[![Validate](https://github.com/vlioscz/JA-RS485/actions/workflows/validate.yml/badge.svg)](https://github.com/vlioscz/JA-RS485/actions/workflows/validate.yml)
[![GitHub release](https://img.shields.io/github/v/release/vlioscz/JA-RS485)](https://github.com/vlioscz/JA-RS485/releases)
[![HACS](https://img.shields.io/badge/HACS-custom-orange.svg)](https://hacs.xyz)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Custom Home Assistant integration for reading and controlling a **Jablotron JABLOTRON 100 / 100+** alarm system
through the **[JA-121T RS-485 bus interface](https://portal.jablotron.com/cs/sbernicove-rozhrani-rs-485)**
(ASCII protocol, 9600 Bd, 8N1 — per Jablotron manual MNN51111), typically connected via a USB↔RS-485 converter.

## Why RS-485? (compared to other Jablotron integrations)

There are other ways to get a Jablotron system into Home Assistant:

- **[Jablotron Cloud](https://github.com/Pigotka/ha-cc-jablotron-cloud)** — uses the MyJABLOTRON
  cloud API. No wiring at all, but it depends on your internet connection *and* on the Jablotron
  cloud being up: when either is down, so is your alarm in HA.
- **[Jablotron 100](https://github.com/kukulich/home-assistant-jablotron100)** — connects directly
  to the control panel over USB. Feature-rich, but it requires the HA machine to sit next to the
  panel, a USB cable someone can knock loose, and over any real distance you have to work out how
  to extend USB (which it was never designed for).

This integration may not offer every feature of those two, but it is the **hardest to break**:
the JA-121T talks over a dedicated RS-485 bus — an industrial standard designed for runs of
hundreds of metres over a cheap twisted pair, galvanically isolated, on screw terminals that
don't fall out. Everything is **fully local** (no internet, no cloud account), and if the link
does drop, the integration reconnects by itself and tells you about it
(`binary_sensor.jablotron_bus_connection`).

## Features

- **Alarm control panel** entity per section — arm (SET), arm partially (SETP), disarm (UNSET),
  with proper HA states: `disarmed`, `arming` (exit delay), `pending` (entry delay),
  `armed_away`, `armed_home` and `triggered` (intruder / fire / panic alarm)
- **Switch** entity per PG output (PGON / PGOFF), non-optimistic — state changes only after
  the panel confirms them. PGs configured as **impulse** in F-Link can be listed in the
  options and become stateless **button** entities (press = PGON) instead
- **Device triggers** — pick "Intruder / Fire / Panic / Any alarm" (optionally for one
  section) directly in the UI automation editor
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
- Config flow validates the connection and the access code before the entry is created;
  **Reconfigure** lets you change the port or access code later without losing entities
- **`ja_rs485_alarm` event** fired on the HA event bus whenever an intruder / fire / panic
  alarm flag of a section changes — ideal for push-notification automations
- **Bus connection binary sensor** (`binary_sensor.jablotron_bus_connection`) for watching
  the health of the serial link
- **Diagnostics** download (access code redacted) including the last 50 received protocol
  lines — attach it when reporting issues
- Section entities expose a `state_changed_at` attribute (UTC) with the time of the last
  reported state change

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

### HACS (recommended)

[![Open your Home Assistant instance and open this repository inside HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=vlioscz&repository=JA-RS485&category=integration)

1. Click the button above (or **HACS → ⋮ → Custom repositories**, add
   `https://github.com/vlioscz/JA-RS485` as type **Integration** — skip once the repository
   is in the HACS default store).
2. Download **JA-RS485** and restart Home Assistant.

### Manual

1. Copy `custom_components/ja_rs485/` into `config/custom_components/ja_rs485/`.
2. Restart Home Assistant.

### Setup

[![Open your Home Assistant instance and start setting up this integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=ja_rs485)

1. Click the button above, or **Settings → Devices & services → Add integration → JA-RS485.**
2. Pick the serial port — prefer the stable path `/dev/serial/by-id/usb-...` over `/dev/ttyUSB0`
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

## Alarm event automations

Every change of an alarm flag fires a `ja_rs485_alarm` event with
`{"type": "intruder"|"fire"|"panic", "flag": "...", "section": N, "active": true|false}`:

```yaml
trigger:
  - platform: event
    event_type: ja_rs485_alarm
    event_data:
      active: true
action:
  - service: notify.mobile_app_phone
    data:
      title: "ALARM!"
      message: "{{ trigger.event.data.type }} alarm in section {{ trigger.event.data.section }}"
```

## Tested hardware

Verified working on a JABLOTRON 100+ system with a JA-121T and an FT232R-based USB↔RS-485
converter (`/dev/ttyUSB0`), wired A→D+, B→D−, GND↔GND, with an external 12 V DC supply on
the module's +U/GND output terminals. Section arm/disarm, PG control and detector reading
all confirmed on real hardware. Practical findings: PG output changes propagate instantly,
detector (PRFSTATE) updates arrive only every ~10 s — route detectors through PG outputs
for automations.

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
