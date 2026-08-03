"""Constants for the JA-RS485 integration."""

DOMAIN = "ja_rs485"

CONF_PORT = "port"
CONF_ACCESS_CODE = "access_code"

# Options: lists of section/PG numbers (as strings) to expose as entities.
# An empty/missing list means "expose everything the panel reports".
CONF_SECTIONS = "sections"
CONF_PG_OUTPUTS = "pg_outputs"

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


def is_section_allowed(options: dict, section_id: int) -> bool:
    selected = options.get(CONF_SECTIONS) or []
    return not selected or str(section_id) in selected


def is_pg_allowed(options: dict, pg_id: int) -> bool:
    selected = options.get(CONF_PG_OUTPUTS) or []
    return not selected or str(pg_id) in selected
