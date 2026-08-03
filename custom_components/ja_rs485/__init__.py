"""The JA-RS485 integration — Jablotron alarm over the JA-121T RS-485 interface."""

from __future__ import annotations

import logging
import re

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STOP, Platform
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .client import JaRs485Client
from .const import (
    ATTR_PG_ID,
    ATTR_ZONE_ID,
    CONF_ACCESS_CODE,
    CONF_PORT,
    CONF_PRF_POLL_INTERVAL,
    DOMAIN,
    MAX_PG,
    MAX_SECTION,
    can_arm,
    can_control_pg,
    can_disarm,
    is_peripheral_allowed,
    is_pg_allowed,
    is_section_allowed,
    SERVICE_PGOFF,
    SERVICE_PGON,
    SERVICE_SET_ZONE,
    SERVICE_SET_ZONE_PARTIAL,
    SERVICE_UNSET_ZONE,
    signal_update,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [
    Platform.ALARM_CONTROL_PANEL,
    Platform.BINARY_SENSOR,
    Platform.SENSOR,
    Platform.SWITCH,
]

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


@callback
def _async_prune_registry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove registry entries for sections/PGs excluded via options."""
    ent_reg = er.async_get(hass)
    for reg_entry in er.async_entries_for_config_entry(ent_reg, entry.entry_id):
        unique_id = reg_entry.unique_id or ""
        if match := re.search(r"_(?:section|zone)_(\d+)$", unique_id):
            if not is_section_allowed(entry.options, int(match.group(1))):
                ent_reg.async_remove(reg_entry.entity_id)
        elif match := re.search(r"_pg_(\d+)$", unique_id):
            if not is_pg_allowed(entry.options, int(match.group(1))):
                ent_reg.async_remove(reg_entry.entity_id)
        elif match := re.search(r"_peripheral_(\d+)$", unique_id):
            if not is_peripheral_allowed(entry.options, int(match.group(1))):
                ent_reg.async_remove(reg_entry.entity_id)


async def _async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    port: str = entry.data[CONF_PORT]
    access_code: str = entry.data[CONF_ACCESS_CODE]

    _async_prune_registry(hass, entry)

    @callback
    def _dispatch() -> None:
        async_dispatcher_send(hass, signal_update(entry.entry_id))

    def _on_update() -> None:
        # Called from the reader thread — hop into the event loop safely.
        try:
            hass.loop.call_soon_threadsafe(_dispatch)
        except RuntimeError:
            pass  # loop already closed during shutdown

    client = JaRs485Client(
        port,
        access_code,
        on_update=_on_update,
        prf_poll_interval=float(entry.options.get(CONF_PRF_POLL_INTERVAL, 0) or 0),
    )
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = client
    client.start()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _async_register_services(hass)

    async def _async_shutdown(event) -> None:
        await hass.async_add_executor_job(client.stop)

    entry.async_on_unload(
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, _async_shutdown)
    )
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
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

    def _get_entry_and_client() -> tuple[ConfigEntry, JaRs485Client]:
        data: dict[str, JaRs485Client] = hass.data.get(DOMAIN, {})
        if not data:
            raise HomeAssistantError("JA-RS485 is not set up")
        if len(data) > 1:
            raise HomeAssistantError(
                "Multiple JA-RS485 connections are configured; use the alarm and "
                "switch entities instead of the domain services"
            )
        entry_id, client = next(iter(data.items()))
        entry = hass.config_entries.async_get_entry(entry_id)
        if entry is None:
            raise HomeAssistantError("JA-RS485 is not set up")
        return entry, client

    async def _async_send(client: JaRs485Client, command: str) -> None:
        try:
            await hass.async_add_executor_job(client.send_command, command)
        except ConnectionError as err:
            raise HomeAssistantError(str(err)) from err

    def _require(allowed: bool, action: str) -> None:
        if not allowed:
            raise HomeAssistantError(
                f"{action} is not allowed by the integration control settings"
            )

    async def _set_zone(call: ServiceCall) -> None:
        entry, client = _get_entry_and_client()
        section_id = call.data[ATTR_ZONE_ID]
        _require(can_arm(entry.options, section_id), f"Arming section {section_id}")
        await _async_send(client, f"SET {section_id}")

    async def _set_zone_partial(call: ServiceCall) -> None:
        entry, client = _get_entry_and_client()
        section_id = call.data[ATTR_ZONE_ID]
        _require(can_arm(entry.options, section_id), f"Arming section {section_id}")
        await _async_send(client, f"SETP {section_id}")

    async def _unset_zone(call: ServiceCall) -> None:
        entry, client = _get_entry_and_client()
        section_id = call.data[ATTR_ZONE_ID]
        _require(can_disarm(entry.options, section_id), f"Disarming section {section_id}")
        await _async_send(client, f"UNSET {section_id}")

    async def _pgon(call: ServiceCall) -> None:
        entry, client = _get_entry_and_client()
        pg_id = call.data[ATTR_PG_ID]
        _require(can_control_pg(entry.options, pg_id), f"Controlling PG {pg_id}")
        await _async_send(client, f"PGON {pg_id}")

    async def _pgoff(call: ServiceCall) -> None:
        entry, client = _get_entry_and_client()
        pg_id = call.data[ATTR_PG_ID]
        _require(can_control_pg(entry.options, pg_id), f"Controlling PG {pg_id}")
        await _async_send(client, f"PGOFF {pg_id}")

    hass.services.async_register(DOMAIN, SERVICE_SET_ZONE, _set_zone, ZONE_SERVICE_SCHEMA)
    hass.services.async_register(
        DOMAIN, SERVICE_SET_ZONE_PARTIAL, _set_zone_partial, ZONE_SERVICE_SCHEMA
    )
    hass.services.async_register(DOMAIN, SERVICE_UNSET_ZONE, _unset_zone, ZONE_SERVICE_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_PGON, _pgon, PG_SERVICE_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_PGOFF, _pgoff, PG_SERVICE_SCHEMA)
