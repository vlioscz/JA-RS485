"""The JA-RS485 integration — Jablotron alarm over the JA-121T RS-485 interface."""

from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STOP, Platform
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .client import JaRs485Client
from .const import (
    ATTR_PG_ID,
    ATTR_ZONE_ID,
    CONF_ACCESS_CODE,
    CONF_PORT,
    DOMAIN,
    MAX_PG,
    MAX_SECTION,
    SERVICE_PGOFF,
    SERVICE_PGON,
    SERVICE_SET_ZONE,
    SERVICE_SET_ZONE_PARTIAL,
    SERVICE_UNSET_ZONE,
    signal_update,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.ALARM_CONTROL_PANEL, Platform.SENSOR, Platform.SWITCH]

# Strict validation: only integers within the JA-121T documented ranges may
# ever reach the serial line — this rules out command injection via services.
ZONE_SERVICE_SCHEMA = vol.Schema(
    {vol.Required(ATTR_ZONE_ID): vol.All(vol.Coerce(int), vol.Range(min=1, max=MAX_SECTION))}
)
PG_SERVICE_SCHEMA = vol.Schema(
    {vol.Required(ATTR_PG_ID): vol.All(vol.Coerce(int), vol.Range(min=1, max=MAX_PG))}
)

ALL_SERVICES = (
    SERVICE_SET_ZONE,
    SERVICE_SET_ZONE_PARTIAL,
    SERVICE_UNSET_ZONE,
    SERVICE_PGON,
    SERVICE_PGOFF,
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    port: str = entry.data[CONF_PORT]
    access_code: str = entry.data[CONF_ACCESS_CODE]

    @callback
    def _dispatch() -> None:
        async_dispatcher_send(hass, signal_update(entry.entry_id))

    def _on_update() -> None:
        # Called from the reader thread — hop into the event loop safely.
        try:
            hass.loop.call_soon_threadsafe(_dispatch)
        except RuntimeError:
            pass  # loop already closed during shutdown

    client = JaRs485Client(port, access_code, on_update=_on_update)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = client
    client.start()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _async_register_services(hass)

    async def _async_shutdown(event) -> None:
        await hass.async_add_executor_job(client.stop)

    entry.async_on_unload(
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, _async_shutdown)
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        client: JaRs485Client = hass.data[DOMAIN].pop(entry.entry_id)
        await hass.async_add_executor_job(client.stop)
        if not hass.data[DOMAIN]:
            for service in ALL_SERVICES:
                hass.services.async_remove(DOMAIN, service)
    return unload_ok


def _async_register_services(hass: HomeAssistant) -> None:
    if hass.services.has_service(DOMAIN, SERVICE_SET_ZONE):
        return

    async def _async_send(command: str) -> None:
        clients: list[JaRs485Client] = list(hass.data.get(DOMAIN, {}).values())
        if not clients:
            raise HomeAssistantError("JA-RS485 is not set up")
        if len(clients) > 1:
            raise HomeAssistantError(
                "Multiple JA-RS485 connections are configured; use the alarm and "
                "switch entities instead of the domain services"
            )
        try:
            await hass.async_add_executor_job(clients[0].send_command, command)
        except ConnectionError as err:
            raise HomeAssistantError(str(err)) from err

    async def _set_zone(call: ServiceCall) -> None:
        await _async_send(f"SET {call.data[ATTR_ZONE_ID]}")

    async def _set_zone_partial(call: ServiceCall) -> None:
        await _async_send(f"SETP {call.data[ATTR_ZONE_ID]}")

    async def _unset_zone(call: ServiceCall) -> None:
        await _async_send(f"UNSET {call.data[ATTR_ZONE_ID]}")

    async def _pgon(call: ServiceCall) -> None:
        await _async_send(f"PGON {call.data[ATTR_PG_ID]}")

    async def _pgoff(call: ServiceCall) -> None:
        await _async_send(f"PGOFF {call.data[ATTR_PG_ID]}")

    hass.services.async_register(DOMAIN, SERVICE_SET_ZONE, _set_zone, ZONE_SERVICE_SCHEMA)
    hass.services.async_register(
        DOMAIN, SERVICE_SET_ZONE_PARTIAL, _set_zone_partial, ZONE_SERVICE_SCHEMA
    )
    hass.services.async_register(DOMAIN, SERVICE_UNSET_ZONE, _unset_zone, ZONE_SERVICE_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_PGON, _pgon, PG_SERVICE_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_PGOFF, _pgoff, PG_SERVICE_SCHEMA)
