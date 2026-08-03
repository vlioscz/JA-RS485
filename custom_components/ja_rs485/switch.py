"""Switch entities — one per Jablotron PG output."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .client import JaRs485Client
from .const import DOMAIN, can_control_pg, is_pg_allowed, signal_update
from .entity import JaRs485Entity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    client: JaRs485Client = hass.data[DOMAIN][entry.entry_id]
    known: set[int] = set()

    @callback
    def _sync_entities() -> None:
        new = [
            JaPgSwitch(client, entry, pg_id)
            for pg_id in client.get_pg_ids()
            if pg_id not in known and is_pg_allowed(entry.options, pg_id)
        ]
        for entity in new:
            known.add(entity.pg_id)
        if new:
            async_add_entities(new)

    entry.async_on_unload(
        async_dispatcher_connect(hass, signal_update(entry.entry_id), _sync_entities)
    )
    _sync_entities()


class JaPgSwitch(JaRs485Entity, SwitchEntity):
    _attr_icon = "mdi:electric-switch"

    def __init__(self, client: JaRs485Client, entry: ConfigEntry, pg_id: int) -> None:
        super().__init__(client, entry)
        self.pg_id = pg_id
        self._options = entry.options
        self._attr_name = f"Jablotron PG {pg_id}"
        self._attr_unique_id = f"{entry.entry_id}_pg_{pg_id}"

    @property
    def is_on(self) -> bool | None:
        # Not optimistic on purpose: the state flips only after the panel
        # confirms it with a "PG n ON/OFF" report.
        return self._client.get_pg_state(self.pg_id)

    def _check_control(self) -> None:
        if not can_control_pg(self._options, self.pg_id):
            raise HomeAssistantError(
                f"Controlling PG {self.pg_id} is not allowed by the "
                "integration control settings"
            )

    async def async_turn_on(self, **kwargs: Any) -> None:
        self._check_control()
        await self._async_send_command(f"PGON {self.pg_id}")

    async def async_turn_off(self, **kwargs: Any) -> None:
        self._check_control()
        await self._async_send_command(f"PGOFF {self.pg_id}")
