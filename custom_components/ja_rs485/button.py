"""Button entities — PG outputs configured as impulse in F-Link.

An impulse PG activates on PGON and the panel switches it off by itself
after the configured time, so in Home Assistant it is a stateless button
(press = PGON), not a switch.
"""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .client import JaRs485Client
from .const import DOMAIN, can_control_pg, is_impulse_pg, is_pg_allowed, signal_update
from .entity import JaRs485Entity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    client: JaRs485Client = hass.data[DOMAIN][entry.entry_id]
    known: set[int] = set()

    @callback
    def _sync_entities() -> None:
        new = [
            JaPgButton(client, entry, pg_id)
            for pg_id in client.get_pg_ids()
            if pg_id not in known
            and is_pg_allowed(entry.options, pg_id)
            and is_impulse_pg(entry.options, pg_id)
        ]
        for entity in new:
            known.add(entity.pg_id)
        if new:
            async_add_entities(new)

    entry.async_on_unload(
        async_dispatcher_connect(hass, signal_update(entry.entry_id), _sync_entities)
    )
    _sync_entities()


class JaPgButton(JaRs485Entity, ButtonEntity):
    _attr_icon = "mdi:gesture-tap-button"

    def __init__(self, client: JaRs485Client, entry: ConfigEntry, pg_id: int) -> None:
        super().__init__(client, entry)
        self.pg_id = pg_id
        self._options = entry.options
        self._attr_name = f"Jablotron PG {pg_id}"
        self._attr_unique_id = f"{entry.entry_id}_pg_button_{pg_id}"

    async def async_press(self) -> None:
        if not can_control_pg(self._options, self.pg_id):
            raise HomeAssistantError(
                f"Controlling PG {self.pg_id} is not allowed by the "
                "integration control settings"
            )
        await self._async_send_command(f"PGON {self.pg_id}")
