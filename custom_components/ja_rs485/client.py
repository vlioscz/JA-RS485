"""Threaded serial client for the Jablotron JA-121T RS-485 bus interface.

Protocol reference: Jablotron manual MNN51111 (JA-121T).
ASCII, 9600 Bd, 8N1. Command syntax: "<access code> <COMMAND> [args]" + LF.
The module pushes state changes spontaneously (unless Passive mode is
enabled in F-Link) and answers queries (STATE, PGSTATE, PRFSTATE, ...).

All blocking I/O happens in this thread — never in the Home Assistant
event loop. The access code is never logged.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable

import serial

_LOGGER = logging.getLogger(__name__)

BAUDRATE = 9600  # fixed by the JA-121T (8N1)
READ_TIMEOUT_S = 1.0
WRITE_TIMEOUT_S = 2.0
RECONNECT_DELAY_INITIAL_S = 5.0
RECONNECT_DELAY_MAX_S = 60.0
MAX_BUFFER_BYTES = 4096

SECTION_STATES = {
    "READY",
    "ARMED_PART",
    "ARMED",
    "MAINTENANCE",
    "SERVICE",
    "BLOCKED",
    "OFF",
}

ALARM_FLAGS = {"INTRUDER_ALARM", "FIRE_ALARM", "PANIC_ALARM"}
DELAY_FLAGS = {"ENTRY", "EXIT"}
SECTION_FLAGS = ALARM_FLAGS | DELAY_FLAGS | {"INTERNAL_WARNING", "EXTERNAL_WARNING"}


def _to_int(token: str) -> int | None:
    try:
        return int(token)
    except ValueError:
        return None


class JaRs485Client(threading.Thread):
    """Reader/writer for the JA-121T with automatic reconnect."""

    def __init__(
        self,
        port: str,
        access_code: str,
        on_update: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(daemon=True, name=f"JA-RS485 {port}")
        self._port = port
        self._access_code = access_code
        self._on_update = on_update
        self._serial: serial.Serial | None = None
        self._write_lock = threading.Lock()
        self._state_lock = threading.Lock()
        self._stop_event = threading.Event()
        self._connected = False
        self._connect_error_logged = False
        self._sections: dict[int, str] = {}
        self._section_flags: dict[int, set[str]] = {}
        self._pg: dict[int, bool] = {}
        self._prfstate: str | None = None

    # ------------------------------------------------------------------
    # Thread-safe state accessors
    # ------------------------------------------------------------------

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def port(self) -> str:
        return self._port

    def get_section_ids(self) -> list[int]:
        with self._state_lock:
            return sorted(self._sections)

    def get_section_state(self, section_id: int) -> str | None:
        with self._state_lock:
            return self._sections.get(section_id)

    def get_section_flags(self, section_id: int) -> set[str]:
        with self._state_lock:
            return set(self._section_flags.get(section_id, ()))

    def get_pg_ids(self) -> list[int]:
        with self._state_lock:
            return sorted(self._pg)

    def get_pg_state(self, pg_id: int) -> bool | None:
        with self._state_lock:
            return self._pg.get(pg_id)

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------

    def send_command(self, command: str) -> None:
        """Send a command (without the access code prefix).

        Raises ConnectionError if the serial link is down. The command
        string must be built from validated values only — callers are
        responsible for never passing user-supplied raw strings.
        """
        ser = self._serial
        if not self._connected or ser is None:
            raise ConnectionError(f"Not connected to JA-121T on {self._port}")
        data = f"{self._access_code} {command}\n".encode("ascii")
        try:
            with self._write_lock:
                ser.write(data)
                ser.flush()
        except (serial.SerialException, OSError) as err:
            raise ConnectionError(f"Failed to send command to JA-121T: {err}") from err
        # Deliberately log only the command, never the access code.
        _LOGGER.debug("Sent command: %s", command)

    def stop(self) -> None:
        """Stop the reader thread and close the port. Blocking, call from executor."""
        self._stop_event.set()
        ser = self._serial
        if ser is not None:
            try:
                if hasattr(ser, "cancel_read"):
                    ser.cancel_read()
                ser.close()
            except (serial.SerialException, OSError):
                pass
        if self.is_alive():
            self.join(timeout=5)

    # ------------------------------------------------------------------
    # Reader thread
    # ------------------------------------------------------------------

    def run(self) -> None:
        delay = RECONNECT_DELAY_INITIAL_S
        while not self._stop_event.is_set():
            if not self._open():
                if self._stop_event.wait(delay):
                    break
                delay = min(delay * 2, RECONNECT_DELAY_MAX_S)
                continue
            delay = RECONNECT_DELAY_INITIAL_S
            self._request_initial_state()
            self._read_loop()
            self._disconnect()
        self._disconnect()

    def _open(self) -> bool:
        try:
            self._serial = serial.Serial(
                port=self._port,
                baudrate=BAUDRATE,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=READ_TIMEOUT_S,
                write_timeout=WRITE_TIMEOUT_S,
            )
        except (serial.SerialException, OSError, ValueError) as err:
            if not self._connect_error_logged:
                _LOGGER.warning(
                    "Cannot open serial port %s (%s); will keep retrying", self._port, err
                )
                self._connect_error_logged = True
            return False
        self._connect_error_logged = False
        self._connected = True
        _LOGGER.info("Connected to JA-121T on %s", self._port)
        self._notify()
        return True

    def _disconnect(self) -> None:
        was_connected = self._connected
        self._connected = False
        ser = self._serial
        self._serial = None
        if ser is not None:
            try:
                ser.close()
            except (serial.SerialException, OSError):
                pass
        if was_connected:
            self._notify()

    def _request_initial_state(self) -> None:
        """Query section and PG output states after (re)connecting.

        The RS-485 pair is half-duplex: transmitting while the module is
        still streaming a response clobbers it on the shared wires. Give the
        module time to answer each query before sending the next one; the
        responses accumulate in the OS buffer and are parsed once the read
        loop starts.
        """
        if self._stop_event.wait(0.5):
            return
        ser = self._serial
        if ser is not None:
            try:
                ser.reset_input_buffer()  # discard any stale bytes from port open
            except (serial.SerialException, OSError):
                return
        try:
            self.send_command("STATE")
            if self._stop_event.wait(2.0):
                return
            self.send_command("PGSTATE")
        except ConnectionError as err:
            _LOGGER.debug("Initial state query failed: %s", err)

    def _read_loop(self) -> None:
        buffer = bytearray()
        while not self._stop_event.is_set():
            ser = self._serial
            if ser is None:
                return
            try:
                data = ser.read(1)
                if data:
                    waiting = ser.in_waiting
                    if waiting:
                        data += ser.read(waiting)
            except (serial.SerialException, OSError):
                if not self._stop_event.is_set():
                    _LOGGER.warning(
                        "Serial connection to %s lost; reconnecting", self._port
                    )
                return
            if not data:
                continue
            buffer.extend(data)
            while (idx := buffer.find(b"\n")) != -1:
                raw_line = bytes(buffer[: idx])
                del buffer[: idx + 1]
                line = raw_line.decode("ascii", errors="ignore").strip()
                if line:
                    self._handle_line(line)
            if len(buffer) > MAX_BUFFER_BYTES:
                _LOGGER.debug("Discarding %d bytes of unterminated data", len(buffer))
                buffer.clear()

    # ------------------------------------------------------------------
    # Protocol parsing
    # ------------------------------------------------------------------

    def _handle_line(self, line: str) -> None:
        parts = line.split()
        head = parts[0]
        changed = False

        if head == "OK":
            _LOGGER.debug("Command confirmed: OK")
            return
        if head.startswith("ERROR"):
            if "NO_ACCESS" in line:
                _LOGGER.error(
                    "JA-121T rejected the command (%s) — check the access code and "
                    "its permissions for the targeted section/PG output",
                    line,
                )
            elif "INVALID_VALUE" in line:
                _LOGGER.warning(
                    "JA-121T could not execute the command (%s) — e.g. the section "
                    "is not ready or is already in the requested state",
                    line,
                )
            else:
                _LOGGER.warning("JA-121T rejected the command: %s", line)
            return

        with self._state_lock:
            if head == "STATE" and len(parts) >= 3 and parts[2] in SECTION_STATES:
                section_id = _to_int(parts[1])
                if section_id is not None:
                    if self._sections.get(section_id) != parts[2]:
                        changed = True
                        # Delay flags always end with a state change; alarm
                        # flags are cleared once the section is disarmed.
                        flags = self._section_flags.get(section_id)
                        if flags:
                            flags -= DELAY_FLAGS
                            if parts[2] == "READY":
                                flags.clear()
                    self._sections[section_id] = parts[2]
            elif head == "PG" and len(parts) >= 3 and parts[2] in ("ON", "OFF"):
                pg_id = _to_int(parts[1])
                if pg_id is not None:
                    value = parts[2] == "ON"
                    if self._pg.get(pg_id) is not value:
                        changed = True
                    self._pg[pg_id] = value
            elif head == "PRFSTATE" and len(parts) >= 2:
                if self._prfstate != parts[1]:
                    changed = True
                self._prfstate = parts[1]
            elif head in SECTION_FLAGS and len(parts) >= 3 and parts[-1] in ("ON", "OFF"):
                active = parts[-1] == "ON"
                for token in parts[1:-1]:
                    section_id = _to_int(token)
                    if section_id is None:
                        continue
                    flags = self._section_flags.setdefault(section_id, set())
                    if active and head not in flags:
                        flags.add(head)
                        changed = True
                    elif not active and head in flags:
                        flags.discard(head)
                        changed = True
            else:
                _LOGGER.debug("Unhandled line from JA-121T: %s", line)

        if changed:
            self._notify()

    def _notify(self) -> None:
        if self._on_update is None:
            return
        try:
            self._on_update()
        except Exception:  # noqa: BLE001 — never let a callback kill the reader
            _LOGGER.exception("Error in update callback")
