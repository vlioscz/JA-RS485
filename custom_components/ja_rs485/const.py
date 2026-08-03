"""Constants for the JA-RS485 integration."""

DOMAIN = "ja_rs485"

CONF_PORT = "port"
CONF_ACCESS_CODE = "access_code"

# Options: lists of section/PG numbers (as strings) to expose as entities.
# An empty/missing list means "expose everything the panel reports".
CONF_SECTIONS = "sections"
CONF_PG_OUTPUTS = "pg_outputs"
CONF_PERIPHERALS = "peripherals"

# Control permissions — mirror the rights granted to the access code in
# F-Link so the integration never even attempts a command it may not use.
CONF_CONTROL_MODE = "control_mode"          # section control: full|arm_only|none
CONF_CONTROL_SECTIONS = "control_sections"  # [] = all visible sections
CONF_ALLOW_PG_CONTROL = "allow_pg_control"  # bool, default True
CONF_CONTROL_PGS = "control_pgs"            # [] = all visible PGs

# Fast PRFSTATE polling interval in seconds (0 = off). The module broadcasts
# peripheral states only every ~10 s on its own; polling shortens detector
# latency at the cost of more bus traffic.
CONF_PRF_POLL_INTERVAL = "prf_poll_interval"

CONTROL_FULL = "full"
CONTROL_ARM_ONLY = "arm_only"
CONTROL_NONE = "none"
CONTROL_MODES = [CONTROL_FULL, CONTROL_ARM_ONLY, CONTROL_NONE]

ATTR_ZONE_ID = "zone_id"
ATTR_PG_ID = "pg_id"

SERVICE_SET_ZONE = "set_zone"
SERVICE_SET_ZONE_PARTIAL = "set_zone_partial"
SERVICE_UNSET_ZONE = "unset_zone"
SERVICE_PGON = "pgon"
SERVICE_PGOFF = "pgoff"

# Limits per the JA-121T manual (MNN51111): sections 1-15, PG outputs 1-128,
# peripherals 0-229 (position 0 is the control panel).
MAX_SECTION = 15
MAX_PG = 128
MAX_PERIPHERAL = 229

MANUFACTURER = "Jablotron"
MODEL = "JA-121T"


def signal_update(entry_id: str) -> str:
    """Dispatcher signal fired whenever the client state changes."""
    return f"{DOMAIN}_update_{entry_id}"


def expand_tokens(values: list | None) -> set[int]:
    """Expand a list of "5" / "8-20" tokens into a set of integers."""
    result: set[int] = set()
    for raw in values or []:
        token = str(raw).strip()
        if token.isdigit():
            result.add(int(token))
        elif "-" in token:
            low, _, high = token.partition("-")
            if low.strip().isdigit() and high.strip().isdigit():
                lo, hi = int(low), int(high)
                if lo > hi:
                    lo, hi = hi, lo
                result.update(range(lo, hi + 1))
    return result


def is_section_allowed(options: dict, section_id: int) -> bool:
    selected = options.get(CONF_SECTIONS) or []
    return not selected or section_id in expand_tokens(selected)


def is_pg_allowed(options: dict, pg_id: int) -> bool:
    selected = options.get(CONF_PG_OUTPUTS) or []
    return not selected or pg_id in expand_tokens(selected)


def is_peripheral_allowed(options: dict, peripheral_id: int) -> bool:
    selected = options.get(CONF_PERIPHERALS) or []
    return not selected or peripheral_id in expand_tokens(selected)


def selected_peripherals(options: dict) -> list[int]:
    """Explicitly selected peripheral positions, or [] for auto-discovery."""
    return sorted(expand_tokens(options.get(CONF_PERIPHERALS)))


def _section_controllable(options: dict, section_id: int) -> bool:
    selected = options.get(CONF_CONTROL_SECTIONS) or []
    return not selected or section_id in expand_tokens(selected)


def can_arm(options: dict, section_id: int) -> bool:
    mode = options.get(CONF_CONTROL_MODE, CONTROL_FULL)
    return mode in (CONTROL_FULL, CONTROL_ARM_ONLY) and _section_controllable(
        options, section_id
    )


def can_disarm(options: dict, section_id: int) -> bool:
    mode = options.get(CONF_CONTROL_MODE, CONTROL_FULL)
    return mode == CONTROL_FULL and _section_controllable(options, section_id)


def can_control_pg(options: dict, pg_id: int) -> bool:
    if not options.get(CONF_ALLOW_PG_CONTROL, True):
        return False
    selected = options.get(CONF_CONTROL_PGS) or []
    return not selected or pg_id in expand_tokens(selected)
