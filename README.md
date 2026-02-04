# Home Assistant Jablotron ASCII Integration

This repository contains a **custom Home Assistant integration** for reading and controlling Jablotron alarm system 
over an RS485 ASCII protocol (e.g. via JA-121T).

It includes:
- Config Flow (UI integration setup)
- Dynamic sensors for zones and PG outputs
- Services for SET/UNSET/PGON/PGOFF
- A dynamic Lovelace dashboard with auto‑generated control buttons

## Installation

1. Copy the `custom_components/jablotron_ascii/` folder into your Home Assistant: config/custom_components/jablotron_ascii/


2. Copy the dashboard file `dashboards/jablotron_dashboard.yaml`
(optional: add it to Lovelace or import via UI editor)

3. Install the required Lovelace plugins:
- `auto-entities`
- `vertical-stack-in-card`

4. Restart Home Assistant.

5. Go to **Settings → Integrations → Add Integration** and select **Jablotron RS485 ASCII**.  
Enter your serial port and baud rate.

## Services

There are the following services available:

| Service | Description |
|---------|-------------|
| `jablotron_ascii.set_zone` | Arm a zone |
| `jablotron_ascii.unset_zone` | Disarm a zone |
| `jablotron_ascii.pgon` | Turn PG output on |
| `jablotron_ascii.pgoff` | Turn PG output off |

Each service takes a numeric argument (`zone_id` / `pg_id`) to select which sensor/output you want to control.

## Lovelace Dashboard

Use the included `jablotron_dashboard.yaml` to automatically create a dashboard 
with buttons for all detected zones and PG outputs.

## License

This integration is licensed under the MIT License.
