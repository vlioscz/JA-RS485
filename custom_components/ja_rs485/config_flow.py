"""Config flow for the JA-RS485 integration."""

from __future__ import annotations

import re
import time
from typing import Any

import serial
import voluptuous as vol
from serial.tools import list_ports

from homeassistant import config_entries
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .client import BAUDRATE
from .const import CONF_ACCESS_CODE, CONF_PORT, DOMAIN

# JA-121T code format: "1234" or with a user prefix "1*1234". Restricting the
# charset here also guarantees the code can never smuggle extra commands onto
# the serial line.
CODE_RE = re.compile(r"^\d{1,4}(\*\d{1,8})?$|^\d{1,8}$")

VALIDATE_TIMEOUT_S = 5.0


class CannotConnect(Exception):
    """Serial port cannot be opened or communication failed."""


class InvalidAuth(Exception):
    """The panel rejected the access code."""


class NoResponse(Exception):
    """Port opened but the JA-121T did not answer."""


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
        raise CannotConnect(str(err)) from err

    try:
        ser.reset_input_buffer()
        ser.write(f"{access_code} STATE\n".encode("ascii"))
        ser.flush()
        deadline = time.monotonic() + VALIDATE_TIMEOUT_S
        got_data = False
        while time.monotonic() < deadline:
            raw = ser.readline()
            if not raw:
                continue
            got_data = True
            line = raw.decode("ascii", errors="ignore").strip()
            if line.startswith("STATE ") or line == "OK":
                return  # valid answer to our STATE query
            if "NO_ACCESS" in line:
                raise InvalidAuth
            if line.startswith("ERROR"):
                raise InvalidAuth
            # Any other line (spontaneous report) — keep listening.
        if got_data:
            raise CannotConnect("Unexpected data on the serial line")
        raise NoResponse
    except (serial.SerialException, OSError) as err:
        raise CannotConnect(str(err)) from err
    finally:
        ser.close()


class JaRs485ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow pro JA-RS485 (Jablotron JA-121T)."""

    VERSION = 2

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
