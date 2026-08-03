"""Constants for the JA-RS485 integration."""

DOMAIN = "ja_rs485"

CONF_PORT = "port"
CONF_ACCESS_CODE = "access_code"

ATTR_ZONE_ID = "zone_id"
ATTR_PG_ID = "pg_id"

SERVICE_SET_ZONE = "set_zone"
SERVICE_SET_ZONE_PARTIAL = "set_zone_partial"
SERVICE_UNSET_ZONE = "unset_zone"
SERVICE_PGON = "pgon"
SERVICE_PGOFF = "pgoff"

# Limits per the JA-121T manual (MNN51111): sections 1-15, PG outputs 1-128.
MAX_SECTION = 15
MAX_PG = 128

MANUFACTURER = "Jablotron"
MODEL = "JA-121T"


def signal_update(entry_id: str) -> str:
    """Dispatcher signal fired whenever the client state changes."""
    return f"{DOMAIN}_update_{entry_id}"
