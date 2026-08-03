"""Diagnostics support for JA-RS485 (access code always redacted)."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .client import JaRs485Client
from .const import CONF_ACCESS_CODE, DOMAIN

TO_REDACT = {CONF_ACCESS_CODE}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    client: JaRs485Client | None = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    diagnostics: dict[str, Any] = {
        "entry": {
            "data": async_redact_data(dict(entry.data), TO_REDACT),
            "options": dict(entry.options),
        },
    }
    if client is not None:
        diagnostics["client"] = client.snapshot()
    return diagnostics
