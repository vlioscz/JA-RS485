# JA-RS485 — Home Assistant Jablotron RS-485 Integration

This repository contains a **custom Home Assistant integration** for reading and controlling a Jablotron alarm system
over the RS-485 bus interface (JA-121T) using its ASCII protocol.

It includes:
- Config Flow (UI integration setup)
- Dynamic sensors for sections (zones) and PG outputs
- Services for SET/UNSET/PGON/PGOFF
- A dynamic Lovelace dashboard with auto-generated control buttons

## Installation

1. Copy the `custom_components/ja_rs485/` folder into your Home Assistant: `config/custom_components/ja_rs485/`

2. Copy the dashboard file `dashboards/jablotron_dashboard.yaml`
(optional: add it to Lovelace or import via UI editor)

3. Install the required Lovelace plugins:
- `auto-entities`
- `vertical-stack-in-card`

4. Restart Home Assistant.

5. Go to **Settings → Integrations → Add Integration** and select **JA-RS485**.
Enter your serial port and baud rate.

## Services

There are the following services available:

| Service | Description |
|---------|-------------|
| `ja_rs485.set_zone` | Arm a section |
| `ja_rs485.unset_zone` | Disarm a section |
| `ja_rs485.pgon` | Turn PG output on |
| `ja_rs485.pgoff` | Turn PG output off |

Each service takes a numeric argument (`zone_id` / `pg_id`) to select which section/output you want to control.

## Lovelace Dashboard

Use the included `jablotron_dashboard.yaml` to automatically create a dashboard
with buttons for all detected sections and PG outputs.

## License

This integration is licensed under the MIT License.
