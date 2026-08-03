"""Diagnostic sensors — raw JA-121T state of each section."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .client import JaRs485Client
from .const import DOMAIN, is_section_allowed, signal_update
from .entity import JaRs485Entity

ICONS = {
    "ARMED": "mdi:shield-lock",
    "ARMED_PART": "mdi:shield-half-full",
    "READY": "mdi:shield-check-outline",
    "BLOCKED": "mdi:shield-alert",
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    client: JaRs485Client = hass.data[DOMAIN][entry.entry_id]
    known: set[int] = set()

    @callback
    def _sync_entities() -> None:
        # Sections reported as OFF are disabled in the panel configuration —
        # don't create entities for them (they appear later if ever enabled).
        new = [
            JaZoneSensor(client, entry, section_id)
            for section_id in client.get_section_ids()
            if section_id not in known
            and client.get_section_state(section_id) != "OFF"
            and is_section_allowed(entry.options, section_id)
        ]
        for entity in new:
            known.add(entity.section_id)
        if new:
            async_add_entities(new)

    entry.async_on_unload(
        async_dispatcher_connect(hass, signal_update(entry.entry_id), _sync_entities)
    )
    _sync_entities()


class JaZoneSensor(JaRs485Entity, SensorEntity):
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, client: JaRs485Client, entry: ConfigEntry, section_id: int) -> None:
        super().__init__(client, entry)
        self.section_id = section_id
        self._attr_name = f"Jablotron Zone {section_id}"
        self._attr_unique_id = f"{entry.entry_id}_zone_{section_id}"

    @property
    def native_value(self) -> str | None:
        return self._client.get_section_state(self.section_id)

    @property
    def icon(self) -> str:
        return ICONS.get(self.native_value or "", "mdi:shield-outline")

    @property
    def extra_state_attributes(self) -> dict:
        return {
            "flags": sorted(self._client.get_section_flags(self.section_id)),
            "state_changed_at": self._client.get_section_changed_at(self.section_id),
        }
