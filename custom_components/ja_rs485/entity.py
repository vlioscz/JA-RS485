"""Base entity for the JA-RS485 integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity

from .client import JaRs485Client
from .const import DOMAIN, MANUFACTURER, MODEL, signal_update


class JaRs485Entity(Entity):
    """Common base: push updates via dispatcher, availability from the client."""

    _attr_should_poll = False

    def __init__(self, client: JaRs485Client, entry: ConfigEntry) -> None:
        self._client = client
        self._entry_id = entry.entry_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"Jablotron {MODEL}",
            manufacturer=MANUFACTURER,
            model=MODEL,
        )

    @property
    def available(self) -> bool:
        return self._client.connected

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, signal_update(self._entry_id), self._handle_update
            )
        )

    @callback
    def _handle_update(self) -> None:
        self.async_write_ha_state()

    async def _async_send_command(self, command: str) -> None:
        """Send a validated command; surface failures to the UI."""
        try:
            await self.hass.async_add_executor_job(self._client.send_command, command)
        except ConnectionError as err:
            raise HomeAssistantError(str(err)) from err
