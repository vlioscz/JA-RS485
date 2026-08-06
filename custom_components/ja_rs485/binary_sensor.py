"""Binary sensors — Jablotron peripherals (detectors) from PRFSTATE.

The PRFSTATE bitmap cannot distinguish an empty position from an idle
detector, so by default an entity is created the first time a peripheral
reports active. Positions can also be selected explicitly in the
integration options (numbers match the Devices tab in F-Link;
position 0 is the control panel).
"""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .client import JaRs485Client
from .const import DOMAIN, get_custom_name, selected_peripherals, signal_update
from .entity import JaRs485Entity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    client: JaRs485Client = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([JaBusConnectionSensor(client, entry)])

    explicit = selected_peripherals(entry.options)
    known: set[int] = set()

    @callback
    def _sync_entities() -> None:
        # Explicit selection wins; otherwise auto-discover ever-active positions.
        wanted = explicit if explicit else client.get_peripheral_ids()
        new = [
            JaPeripheralBinarySensor(client, entry, peripheral_id)
            for peripheral_id in wanted
            if peripheral_id not in known
        ]
        for entity in new:
            known.add(entity.peripheral_id)
        if new:
            async_add_entities(new)

    entry.async_on_unload(
        async_dispatcher_connect(hass, signal_update(entry.entry_id), _sync_entities)
    )
    _sync_entities()


class JaBusConnectionSensor(JaRs485Entity, BinarySensorEntity):
    """Health of the serial link to the JA-121T."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, client: JaRs485Client, entry: ConfigEntry) -> None:
        super().__init__(client, entry)
        self._attr_name = "Jablotron Bus Connection"
        self._attr_unique_id = f"{entry.entry_id}_bus_connection"

    @property
    def available(self) -> bool:
        # Must stay available to be able to report the link as down.
        return True

    @property
    def is_on(self) -> bool:
        return self._client.connected


class JaPeripheralBinarySensor(JaRs485Entity, BinarySensorEntity):
    _attr_icon = "mdi:motion-sensor"

    def __init__(self, client: JaRs485Client, entry: ConfigEntry, peripheral_id: int) -> None:
        super().__init__(client, entry)
        self.peripheral_id = peripheral_id
        self._attr_name = (
            get_custom_name(entry.options, "peripherals", peripheral_id)
            or f"Jablotron Peripheral {peripheral_id}"
        )
        self._attr_unique_id = f"{entry.entry_id}_peripheral_{peripheral_id}"

    @property
    def is_on(self) -> bool | None:
        return self._client.get_peripheral_state(self.peripheral_id)
