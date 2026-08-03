"""Alarm control panel entities — one per Jablotron section."""

from __future__ import annotations

from homeassistant.components.alarm_control_panel import (
    AlarmControlPanelEntity,
    AlarmControlPanelEntityFeature,
    AlarmControlPanelState,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .client import ALARM_FLAGS, JaRs485Client
from .const import DOMAIN, is_section_allowed, signal_update
from .entity import JaRs485Entity

# Mapping of JA-121T section states to HA alarm states. MAINTENANCE, SERVICE
# and OFF intentionally map to None (unknown) — the section cannot be
# operated in those modes.
STATE_MAP = {
    "READY": AlarmControlPanelState.DISARMED,
    "ARMED": AlarmControlPanelState.ARMED_AWAY,
    "ARMED_PART": AlarmControlPanelState.ARMED_HOME,
    "BLOCKED": AlarmControlPanelState.DISARMED,
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
            JaSectionAlarmPanel(client, entry, section_id)
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


class JaSectionAlarmPanel(JaRs485Entity, AlarmControlPanelEntity):
    _attr_supported_features = (
        AlarmControlPanelEntityFeature.ARM_AWAY | AlarmControlPanelEntityFeature.ARM_HOME
    )
    _attr_code_arm_required = False

    def __init__(self, client: JaRs485Client, entry: ConfigEntry, section_id: int) -> None:
        super().__init__(client, entry)
        self.section_id = section_id
        self._attr_name = f"Jablotron Section {section_id}"
        self._attr_unique_id = f"{entry.entry_id}_section_{section_id}"

    @property
    def alarm_state(self) -> AlarmControlPanelState | None:
        flags = self._client.get_section_flags(self.section_id)
        if flags & ALARM_FLAGS:
            return AlarmControlPanelState.TRIGGERED
        if "ENTRY" in flags:
            return AlarmControlPanelState.PENDING
        if "EXIT" in flags:
            return AlarmControlPanelState.ARMING
        state = self._client.get_section_state(self.section_id)
        return STATE_MAP.get(state) if state else None

    @property
    def extra_state_attributes(self) -> dict:
        return {
            "raw_state": self._client.get_section_state(self.section_id),
            "flags": sorted(self._client.get_section_flags(self.section_id)),
        }

    async def async_alarm_arm_away(self, code: str | None = None) -> None:
        await self._async_send_command(f"SET {self.section_id}")

    async def async_alarm_arm_home(self, code: str | None = None) -> None:
        await self._async_send_command(f"SETP {self.section_id}")

    async def async_alarm_disarm(self, code: str | None = None) -> None:
        await self._async_send_command(f"UNSET {self.section_id}")
