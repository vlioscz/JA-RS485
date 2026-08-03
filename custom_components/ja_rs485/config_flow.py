"""Config flow for the JA-RS485 integration."""

from __future__ import annotations

import logging
import re
import time
from typing import Any

import serial
import voluptuous as vol
from serial.tools import list_ports

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    BooleanSelector,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .client import BAUDRATE
from .const import (
    CONF_ACCESS_CODE,
    CONF_ALLOW_PG_CONTROL,
    CONF_CONTROL_MODE,
    CONF_CONTROL_PGS,
    CONF_CONTROL_SECTIONS,
    CONF_PERIPHERALS,
    CONF_PG_OUTPUTS,
    CONF_PORT,
    CONF_SECTIONS,
    CONTROL_FULL,
    CONTROL_MODES,
    DOMAIN,
    MAX_PERIPHERAL,
    MAX_PG,
    MAX_SECTION,
)

# JA-121T code format: "1234" or with a user prefix "1*1234". Restricting the
# charset here also guarantees the code can never smuggle extra commands onto
# the serial line.
CODE_RE = re.compile(r"^\d{1,4}(\*\d{1,8})?$|^\d{1,8}$")

VALIDATE_TIMEOUT_S = 5.0

_LOGGER = logging.getLogger(__name__)


class CannotConnect(Exception):
    """Serial port cannot be opened or communication failed."""


class InvalidAuth(Exception):
    """The panel rejected the access code."""


class NoResponse(Exception):
    """Port opened but the JA-121T did not answer."""


class UnexpectedData(Exception):
    """Data arrived but did not match the JA-121T terminal protocol."""


def _list_serial_ports() -> list[SelectOptionDict]:
    options = []
    for info in sorted(list_ports.comports(), key=lambda p: p.device):
        label = info.device
        if info.description and info.description != "n/a":
            label = f"{info.device} — {info.description}"
        options.append(SelectOptionDict(value=info.device, label=label))
    return options


def _validate_connection(port: str, access_code: str) -> None:
    """Open the port, query STATE and check the panel's answer (executor job)."""
    try:
        ser = serial.Serial(
            port=port,
            baudrate=BAUDRATE,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=1,
            write_timeout=2,
        )
    except (serial.SerialException, OSError, ValueError) as err:
        _LOGGER.warning("Cannot open serial port %s: %s", port, err)
        raise CannotConnect(str(err)) from err

    try:
        ser.reset_input_buffer()
        ser.write(f"{access_code} STATE\n".encode("ascii"))
        ser.flush()
        deadline = time.monotonic() + VALIDATE_TIMEOUT_S
        seen: list[str] = []
        while time.monotonic() < deadline:
            raw = ser.readline()
            if not raw:
                continue
            line = raw.decode("ascii", errors="ignore").strip()
            seen.append(line or repr(raw))
            if line.startswith("STATE ") or line == "OK":
                return  # valid answer to our STATE query
            if "NO_ACCESS" in line:
                _LOGGER.warning("JA-121T on %s rejected the access code", port)
                raise InvalidAuth
            if line.startswith("ERROR"):
                _LOGGER.warning("JA-121T on %s answered: %s", port, line)
                raise InvalidAuth
            # Any other line (spontaneous report) — keep listening.
        if seen:
            _LOGGER.warning(
                "Port %s carries data that does not match the JA-121T terminal "
                "protocol (module in U1-A mode? swapped A/B wires? wrong device?). "
                "Received: %s",
                port,
                seen[:10],
            )
            raise UnexpectedData
        _LOGGER.warning(
            "No answer from JA-121T on %s within %.0f s — check wiring (A/B, GND), "
            "the selected port and that the module's RS-485 side is powered",
            port,
            VALIDATE_TIMEOUT_S,
        )
        raise NoResponse
    except (serial.SerialException, OSError) as err:
        _LOGGER.warning("Communication on %s failed: %s", port, err)
        raise CannotConnect(str(err)) from err
    finally:
        ser.close()


def _clean_id_list(values: list[str], max_value: int, min_value: int = 1) -> list[str]:
    """Normalize user tokens into "N" / "N-M" entries within the valid range.

    Accepts single numbers ("5"), ranges ("8-20") and whole pasted lists
    ("1-6 8-20, 25") in any custom_value chip; invalid parts are dropped.
    """
    tokens: list[str] = []
    seen: set[str] = set()
    for raw in values:
        normalized = re.sub(r"\s*-\s*", "-", str(raw).strip())
        for part in re.split(r"[\s,;]+", normalized):
            match = re.fullmatch(r"(\d+)(?:-(\d+))?", part) if part else None
            if not match:
                continue
            lo = int(match.group(1))
            hi = int(match.group(2)) if match.group(2) else lo
            if lo > hi:
                lo, hi = hi, lo
            lo, hi = max(lo, min_value), min(hi, max_value)
            if lo > hi:
                continue
            token = str(lo) if lo == hi else f"{lo}-{hi}"
            if token not in seen:
                seen.add(token)
                tokens.append(token)
    return sorted(tokens, key=lambda t: int(t.split("-")[0]))


class JaRs485ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow pro JA-RS485 (Jablotron JA-121T)."""

    VERSION = 2

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        return JaRs485OptionsFlow()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            port = user_input[CONF_PORT].strip()
            access_code = user_input[CONF_ACCESS_CODE].strip()

            if not CODE_RE.match(access_code):
                errors[CONF_ACCESS_CODE] = "invalid_code_format"
            else:
                await self.async_set_unique_id(port)
                self._abort_if_unique_id_configured()
                try:
                    await self.hass.async_add_executor_job(
                        _validate_connection, port, access_code
                    )
                except CannotConnect:
                    errors["base"] = "cannot_connect"
                except InvalidAuth:
                    errors["base"] = "invalid_auth"
                except NoResponse:
                    errors["base"] = "no_response"
                except UnexpectedData:
                    errors["base"] = "unexpected_data"
                else:
                    return self.async_create_entry(
                        title=f"JA-121T ({port})",
                        data={CONF_PORT: port, CONF_ACCESS_CODE: access_code},
                    )

        ports = await self.hass.async_add_executor_job(_list_serial_ports)
        schema = vol.Schema(
            {
                vol.Required(CONF_PORT): SelectSelector(
                    SelectSelectorConfig(
                        options=ports,
                        custom_value=True,
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Required(CONF_ACCESS_CODE): TextSelector(
                    TextSelectorConfig(type=TextSelectorType.PASSWORD)
                ),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)


class JaRs485OptionsFlow(config_entries.OptionsFlow):
    """Options: choose which sections and PG outputs become entities."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        if user_input is not None:
            control_mode = user_input.get(CONF_CONTROL_MODE, CONTROL_FULL)
            if control_mode not in CONTROL_MODES:
                control_mode = CONTROL_FULL
            return self.async_create_entry(
                data={
                    CONF_SECTIONS: _clean_id_list(
                        user_input.get(CONF_SECTIONS, []), MAX_SECTION
                    ),
                    CONF_PG_OUTPUTS: _clean_id_list(
                        user_input.get(CONF_PG_OUTPUTS, []), MAX_PG
                    ),
                    CONF_PERIPHERALS: _clean_id_list(
                        user_input.get(CONF_PERIPHERALS, []),
                        MAX_PERIPHERAL,
                        min_value=0,
                    ),
                    CONF_CONTROL_MODE: control_mode,
                    CONF_CONTROL_SECTIONS: _clean_id_list(
                        user_input.get(CONF_CONTROL_SECTIONS, []), MAX_SECTION
                    ),
                    CONF_ALLOW_PG_CONTROL: bool(
                        user_input.get(CONF_ALLOW_PG_CONTROL, True)
                    ),
                    CONF_CONTROL_PGS: _clean_id_list(
                        user_input.get(CONF_CONTROL_PGS, []), MAX_PG
                    ),
                }
            )

        client = self.hass.data.get(DOMAIN, {}).get(self.config_entry.entry_id)
        options = self.config_entry.options
        current_sections = list(options.get(CONF_SECTIONS) or [])
        current_pgs = list(options.get(CONF_PG_OUTPUTS) or [])
        current_prf = list(options.get(CONF_PERIPHERALS) or [])

        # Offer everything the panel currently reports plus already-selected
        # tokens (which may be ranges like "8-20").
        def _by_start(token: str) -> int:
            return int(str(token).split("-")[0])

        known_sections = [str(s) for s in client.get_section_ids()] if client else []
        known_pgs = [str(p) for p in client.get_pg_ids()] if client else []
        known_prf = [str(p) for p in client.get_peripheral_ids()] if client else []
        section_options = sorted(set(known_sections) | set(current_sections), key=_by_start)
        pg_options = sorted(set(known_pgs) | set(current_pgs), key=_by_start)
        prf_options = sorted(set(known_prf) | set(current_prf), key=_by_start)

        schema = vol.Schema(
            {
                vol.Optional(CONF_SECTIONS, default=current_sections): SelectSelector(
                    SelectSelectorConfig(
                        options=section_options,
                        multiple=True,
                        custom_value=True,
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(CONF_PG_OUTPUTS, default=current_pgs): SelectSelector(
                    SelectSelectorConfig(
                        options=pg_options,
                        multiple=True,
                        custom_value=True,
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(CONF_PERIPHERALS, default=current_prf): SelectSelector(
                    SelectSelectorConfig(
                        options=prf_options,
                        multiple=True,
                        custom_value=True,
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(
                    CONF_CONTROL_MODE,
                    default=options.get(CONF_CONTROL_MODE, CONTROL_FULL),
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=CONTROL_MODES,
                        translation_key="control_mode",
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(
                    CONF_CONTROL_SECTIONS,
                    default=list(options.get(CONF_CONTROL_SECTIONS) or []),
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=section_options,
                        multiple=True,
                        custom_value=True,
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(
                    CONF_ALLOW_PG_CONTROL,
                    default=options.get(CONF_ALLOW_PG_CONTROL, True),
                ): BooleanSelector(),
                vol.Optional(
                    CONF_CONTROL_PGS,
                    default=list(options.get(CONF_CONTROL_PGS) or []),
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=pg_options,
                        multiple=True,
                        custom_value=True,
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
