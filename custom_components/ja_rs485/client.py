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
import time
from collections import deque
from collections.abc import Callable
from datetime import datetime, timezone

import serial

_LOGGER = logging.getLogger(__name__)

BAUDRATE = 9600  # fixed by the JA-121T (8N1)
READ_TIMEOUT_S = 1.0
WRITE_TIMEOUT_S = 2.0
RECONNECT_DELAY_INITIAL_S = 5.0
RECONNECT_DELAY_MAX_S = 60.0
MAX_BUFFER_BYTES = 4096
# Periodic full re-query: recovers states lost to half-duplex collisions
# (e.g. the module's spontaneous PRFSTATE broadcast clobbering a PGSTATE
# response on the shared pair).
RESYNC_INTERVAL_S = 300.0
# Gap between queued queries so each response can finish streaming first.
QUERY_GAP_S = 2.0

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
ALARM_TYPES = {
    "INTRUDER_ALARM": "intruder",
    "FIRE_ALARM": "fire",
    "PANIC_ALARM": "panic",
}
DELAY_FLAGS = {"ENTRY", "EXIT"}
SECTION_FLAGS = ALARM_FLAGS | DELAY_FLAGS | {"INTERNAL_WARNING", "EXTERNAL_WARNING"}

RECENT_LINES_KEPT = 50


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _to_int(token: str) -> int | None:
    try:
        return int(token)
    except ValueError:
        return None


def _decode_prfstate(hex_str: str) -> set[int] | None:
    """Decode a PRFSTATE hex bitmap into the set of active peripheral numbers.

    Per manual MNN51111 figure 2: byte i (i-th hex pair) covers peripherals
    8*i .. 8*i+7, LSB first — bit n of byte i set means peripheral 8*i+n is
    active. Peripheral 0 is the control panel itself.
    """
    if len(hex_str) % 2:
        return None
    try:
        raw = bytes.fromhex(hex_str)
    except ValueError:
        return None
    active: set[int] = set()
    for index, byte in enumerate(raw):
        for bit in range(8):
            if byte & (1 << bit):
                active.add(index * 8 + bit)
    return active


class JaRs485Client(threading.Thread):
    """Reader/writer for the JA-121T with automatic reconnect."""

    def __init__(
        self,
        port: str,
        access_code: str,
        on_update: Callable[[], None] | None = None,
        on_event: Callable[[dict], None] | None = None,
    ) -> None:
        super().__init__(daemon=True, name=f"JA-RS485 {port}")
        self._port = port
        self._access_code = access_code
        self._on_update = on_update
        self._on_event = on_event
        self._pending: list[tuple[float, str]] = []
        self._last_resync = 0.0
        self._recent_lines: deque[str] = deque(maxlen=RECENT_LINES_KEPT)
        self._section_changed: dict[int, str] = {}
        self._serial: serial.Serial | None = None
        self._write_lock = threading.Lock()
        self._state_lock = threading.Lock()
        self._stop_event = threading.Event()
        self._connected = False
        self._connect_error_logged = False
        self._sections: dict[int, str] = {}
        self._section_flags: dict[int, set[str]] = {}
        self._pg: dict[int, bool] = {}
        self._prf_active: set[int] = set()
        self._prf_seen: set[int] = set()
        self._prf_received = False

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

    def get_peripheral_ids(self) -> list[int]:
        """Peripheral positions that have been active at least once."""
        with self._state_lock:
            return sorted(self._prf_seen)

    def get_peripheral_state(self, peripheral_id: int) -> bool | None:
        with self._state_lock:
            if not self._prf_received:
                return None
            return peripheral_id in self._prf_active

    def get_section_changed_at(self, section_id: int) -> str | None:
        """UTC timestamp of the last reported state change of a section."""
        with self._state_lock:
            return self._section_changed.get(section_id)

    def snapshot(self) -> dict:
        """State dump for diagnostics (never includes the access code)."""
        with self._state_lock:
            return {
                "port": self._port,
                "connected": self._connected,
                "sections": {str(k): v for k, v in sorted(self._sections.items())},
                "section_flags": {
                    str(k): sorted(v)
                    for k, v in sorted(self._section_flags.items())
                    if v
                },
                "section_changed_at": {
                    str(k): v for k, v in sorted(self._section_changed.items())
                },
                "pg_outputs": {str(k): v for k, v in sorted(self._pg.items())},
                "peripherals_active": sorted(self._prf_active),
                "peripherals_seen": sorted(self._prf_seen),
                "prfstate_received": self._prf_received,
                "recent_lines": list(self._recent_lines),
            }

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
            self._schedule_initial_queries()
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

    def _schedule_initial_queries(self) -> None:
        """Queue the state queries sent after (re)connecting.

        The RS-485 pair is half-duplex: transmitting while the module is
        still streaming a response clobbers it on the shared wires, so the
        queries are spaced apart and dispatched from the read loop.
        """
        ser = self._serial
        if ser is not None:
            try:
                ser.reset_input_buffer()  # discard any stale bytes from port open
            except (serial.SerialException, OSError):
                pass
        now = time.monotonic()
        self._pending = [
            (now + 0.5, "STATE"),
            (now + 0.5 + QUERY_GAP_S, "PGSTATE"),
            (now + 0.5 + 2 * QUERY_GAP_S, "PRFSTATE"),
        ]
        self._last_resync = now

    def _process_timers(self) -> None:
        """Dispatch due queued queries and the periodic resync."""
        now = time.monotonic()
        while self._pending and self._pending[0][0] <= now:
            _, command = self._pending.pop(0)
            try:
                self.send_command(command)
            except ConnectionError:
                return
        if now - self._last_resync >= RESYNC_INTERVAL_S:
            self._last_resync = now
            self._pending = [
                (now, "STATE"),
                (now + QUERY_GAP_S, "PGSTATE"),
                (now + 2 * QUERY_GAP_S, "PRFSTATE"),
            ]

    def _read_loop(self) -> None:
        buffer = bytearray()
        while not self._stop_event.is_set():
            self._process_timers()
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
        self._recent_lines.append(f"{_utcnow()} {line}")
        parts = line.split()
        head = parts[0]
        changed = False
        events: list[dict] = []

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
                        self._section_changed[section_id] = _utcnow()
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
                active = _decode_prfstate(parts[1])
                if active is None:
                    _LOGGER.debug("Invalid PRFSTATE payload: %s", parts[1])
                else:
                    if active != self._prf_active or not self._prf_received:
                        changed = True
                    self._prf_active = active
                    self._prf_seen |= active
                    self._prf_received = True
            elif head in SECTION_FLAGS and len(parts) >= 3 and parts[-1] in ("ON", "OFF"):
                active = parts[-1] == "ON"
                for token in parts[1:-1]:
                    section_id = _to_int(token)
                    if section_id is None:
                        continue
                    flags = self._section_flags.setdefault(section_id, set())
                    transitioned = (head not in flags) if active else (head in flags)
                    if not transitioned:
                        continue
                    if active:
                        flags.add(head)
                    else:
                        flags.discard(head)
                    changed = True
                    if head in ALARM_FLAGS:
                        events.append(
                            {
                                "type": ALARM_TYPES[head],
                                "flag": head,
                                "section": section_id,
                                "active": active,
                            }
                        )
            else:
                _LOGGER.debug("Unhandled line from JA-121T: %s", line)

        for event in events:
            self._notify_event(event)
        if changed:
            self._notify()

    def _notify(self) -> None:
        if self._on_update is None:
            return
        try:
            self._on_update()
        except Exception:  # noqa: BLE001 — never let a callback kill the reader
            _LOGGER.exception("Error in update callback")

    def _notify_event(self, data: dict) -> None:
        if self._on_event is None:
            return
        try:
            self._on_event(data)
        except Exception:  # noqa: BLE001 — never let a callback kill the reader
            _LOGGER.exception("Error in event callback")
