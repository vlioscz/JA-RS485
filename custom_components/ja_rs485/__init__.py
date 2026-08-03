import logging
from .const import DOMAIN, SERVICE_SET_ZONE, SERVICE_UNSET_ZONE, SERVICE_PGON, SERVICE_PGOFF
from .sensor import async_setup_entry as sensor_setup

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass, config):
    return True

async def async_setup_entry(hass, entry):
    await sensor_setup(hass, entry)
    reader = hass.data[DOMAIN]["reader"]

    # Registrace služeb
    async def set_zone(call):
        reader.send_command(f"SET {call.data['zone_id']}")
    async def unset_zone(call):
        reader.send_command(f"UNSET {call.data['zone_id']}")
    async def pgon(call):
        reader.send_command(f"PGON {call.data['pg_id']}")
    async def pgoff(call):
        reader.send_command(f"PGOFF {call.data['pg_id']}")

    hass.services.async_register(DOMAIN, SERVICE_SET_ZONE, set_zone)
    hass.services.async_register(DOMAIN, SERVICE_UNSET_ZONE, unset_zone)
    hass.services.async_register(DOMAIN, SERVICE_PGON, pgon)
    hass.services.async_register(DOMAIN, SERVICE_PGOFF, pgoff)

    return True
