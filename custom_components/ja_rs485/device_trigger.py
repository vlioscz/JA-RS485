"""Device triggers — pick Jablotron alarms in the UI automation editor.

Wraps the ja_rs485_alarm event so an intruder/fire/panic alarm (optionally
filtered to one section) can be selected as a device trigger without writing
an event trigger by hand.
"""

from __future__ import annotations

import voluptuous as vol

from homeassistant.components.device_automation import DEVICE_TRIGGER_BASE_SCHEMA
from homeassistant.components.homeassistant.triggers import event as event_trigger
from homeassistant.const import CONF_DEVICE_ID, CONF_DOMAIN, CONF_PLATFORM, CONF_TYPE
from homeassistant.core import CALLBACK_TYPE, HomeAssistant
from homeassistant.helpers.trigger import TriggerActionType, TriggerInfo
from homeassistant.helpers.typing import ConfigType

from .const import EVENT_ALARM, MAX_SECTION

CONF_SECTION = "section"

TRIGGER_TYPES = ["intruder_alarm", "fire_alarm", "panic_alarm", "any_alarm"]

TRIGGER_SCHEMA = DEVICE_TRIGGER_BASE_SCHEMA.extend(
    {
        vol.Required(CONF_TYPE): vol.In(TRIGGER_TYPES),
        vol.Optional(CONF_SECTION): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=MAX_SECTION)
        ),
    }
)


async def async_get_triggers(
    hass: HomeAssistant, device_id: str
) -> list[dict[str, str]]:
    """List the triggers offered for the JA-121T device."""
    return [
        {
            CONF_PLATFORM: "device",
            CONF_DEVICE_ID: device_id,
            CONF_DOMAIN: "ja_rs485",
            CONF_TYPE: trigger_type,
        }
        for trigger_type in TRIGGER_TYPES
    ]


async def async_get_trigger_capabilities(
    hass: HomeAssistant, config: ConfigType
) -> dict[str, vol.Schema]:
    """Offer an optional section filter for every trigger type."""
    return {
        "extra_fields": vol.Schema(
            {
                vol.Optional(CONF_SECTION): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=MAX_SECTION)
                )
            }
        )
    }


async def async_attach_trigger(
    hass: HomeAssistant,
    config: ConfigType,
    action: TriggerActionType,
    trigger_info: TriggerInfo,
) -> CALLBACK_TYPE:
    """Attach as an event trigger on ja_rs485_alarm (alarm start only)."""
    event_data: dict = {"active": True}
    if config[CONF_TYPE] != "any_alarm":
        event_data["type"] = config[CONF_TYPE].removesuffix("_alarm")
    if CONF_SECTION in config:
        event_data["section"] = config[CONF_SECTION]

    event_config = event_trigger.TRIGGER_SCHEMA(
        {
            event_trigger.CONF_PLATFORM: "event",
            event_trigger.CONF_EVENT_TYPE: EVENT_ALARM,
            event_trigger.CONF_EVENT_DATA: event_data,
        }
    )
    return await event_trigger.async_attach_trigger(
        hass, event_config, action, trigger_info, platform_type="device"
    )
