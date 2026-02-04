import logging
import serial
import threading
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.entity import EntityCategory
from .const import DOMAIN, CONF_PORT, CONF_BAUDRATE

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    config = entry.data
    port = config.get(CONF_PORT)
    baudrate = config.get(CONF_BAUDRATE, 9600)

    reader = JablotronSerialReader(port, baudrate)
    reader.start()
    hass.data.setdefault(DOMAIN, {})["reader"] = reader

    sensors = []

    import asyncio
    async def discover():
        await asyncio.sleep(2)
        for zone_id in reader.get_all_zone_ids():
            sensors.append(JablotronZoneSensor(reader, zone_id))
        for pg_id in reader.get_all_pg_ids():
            sensors.append(JablotronPGSensor(reader, pg_id))
        async_add_entities(sensors, update_before_add=True)

    hass.loop.create_task(discover())


class JablotronSerialReader(threading.Thread):
    def __init__(self, port, baudrate):
        super().__init__(daemon=True)
        self._port = port
        self._baudrate = baudrate
        self._zones = {}
        self._pg = {}
        self._lock = threading.Lock()
        self._running = True
        self._serial = None
        try:
            self._serial = serial.Serial(port, baudrate, timeout=1)
        except Exception as e:
            _LOGGER.error(f"Cannot open serial port {port}: {e}")

    def run(self):
        if not self._serial:
            return
        _LOGGER.info("Jablotron RS485 reader started")
        while self._running:
            try:
                line = self._serial.readline().decode("ascii", errors="ignore").strip()
                self._parse_line(line)
            except Exception as e:
                _LOGGER.error(f"Error reading serial: {e}")

    def _parse_line(self, line):
        parts = line.split()
        with self._lock:
            if parts and parts[0] == "STATE" and len(parts) >= 3:
                self._zones[int(parts[1])] = parts[2]
            elif parts and parts[0] == "PGSTATE" and len(parts) >= 3:
                self._pg[int(parts[1])] = parts[2]

    def get_zone_state(self, zone_id):
        with self._lock:
            return self._zones.get(zone_id)

    def get_pg_state(self, pg_id):
        with self._lock:
            return self._pg.get(pg_id)

    def get_all_zone_ids(self):
        with self._lock:
            return list(self._zones.keys())

    def get_all_pg_ids(self):
        with self._lock:
            return list(self._pg.keys())

    def send_command(self, command):
        try:
            self._serial.write(f"{command}\r\n".encode("ascii"))
            _LOGGER.info(f"Sent command: {command}")
        except Exception as e:
            _LOGGER.error(f"Error sending command: {e}")

    def stop(self):
        self._running = False
        if self._serial:
            self._serial.close()


class JablotronZoneSensor(SensorEntity):
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    def __init__(self, reader, zone_id):
        self._reader = reader
        self._zone_id = zone_id
        self._state = None
        self._attr_name = f"Jablotron Zone {zone_id}"

    @property
    def native_value(self):
        return self._state

    async def async_update(self):
        self._state = self._reader.get_zone_state(self._zone_id)


class JablotronPGSensor(SensorEntity):
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    def __init__(self, reader, pg_id):
        self._reader = reader
        self._pg_id = pg_id
        self._state = None
        self._attr_name = f"Jablotron PG {pg_id}"

    @property
    def native_value(self):
        return self._state

    async def async_update(self):
        self._state = self._reader.get_pg_state(self._pg_id)
