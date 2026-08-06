"""Parse F-Link CSV/TXT exports (sections, PG outputs, peripherals).

F-Link exports are ;-separated with a quoted header row, typically encoded
as Windows-1250 (Czech installs). The file kind is detected from the header
columns, so the user may upload the files in any order or slot:

- sections export has a "Název sekce" / "Section name" column,
- PG export has "Logika" / "Funkce" ("Logic" / "Function") columns,
- anything else with position + name columns is treated as peripherals.

The PG "Funkce" column doubles as configuration: rows with the value
"Vypnuto"/"Off" are unused outputs and rows with "Impulz"/"Impulse" are
pulse outputs (buttons in HA).
"""

from __future__ import annotations

import csv
import io
import re
import unicodedata
from dataclasses import dataclass, field

SECTION_KIND = "sections"
PG_KIND = "pgs"
PERIPHERAL_KIND = "peripherals"

# F-Link placeholder names for unused outputs carry no information.
_DEFAULT_PG_NAME = re.compile(r"^pg (vystup|output) \d+$")

_DISABLED_FUNCTIONS = {"vypnuto", "off", "disabled"}
_IMPULSE_PREFIXES = ("impulz", "impulse", "puls")


def _fold(text: str) -> str:
    """Lowercase and strip diacritics for language-tolerant matching."""
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(c for c in normalized if not unicodedata.combining(c)).lower().strip()


def _decode(data: bytes) -> str:
    if data[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return data.decode("utf-16")
    for encoding in ("utf-8-sig", "cp1250"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("cp1250", errors="replace")


def _sniff_delimiter(header_line: str) -> str:
    counts = {d: header_line.count(d) for d in (";", "\t", ",")}
    best = max(counts, key=lambda d: counts[d])
    return best if counts[best] else ";"


@dataclass
class FlinkImport:
    """Parsed content of one export file."""

    kind: str
    names: dict[int, str] = field(default_factory=dict)
    impulse: set[int] = field(default_factory=set)  # PG only
    used: set[int] = field(default_factory=set)  # PG only: function not disabled


def parse_flink_export(data: bytes) -> FlinkImport | None:
    """Parse one exported file; returns None if it is not a F-Link export."""
    text = _decode(data)
    lines = [line for line in text.splitlines() if line.strip()]
    if len(lines) < 2:
        return None
    delimiter = _sniff_delimiter(lines[0])
    rows = list(csv.reader(io.StringIO("\n".join(lines)), delimiter=delimiter))
    if len(rows) < 2:
        return None

    header = [_fold(cell) for cell in rows[0]]
    header_text = " ".join(header)
    position_idx = next(
        (i for i, h in enumerate(header) if "pozice" in h or "position" in h), None
    )
    name_idx = next(
        (i for i, h in enumerate(header) if "nazev" in h or "jmeno" in h or "name" in h),
        None,
    )
    if position_idx is None or name_idx is None:
        return None

    # The devices export also has a "Sekce" column (which section a device
    # belongs to), so a sections export is recognised by its NAME column
    # ("Název sekce" / "Section name"), not by the whole header.
    if "sekc" in header[name_idx] or "section" in header[name_idx]:
        kind = SECTION_KIND
    elif any(k in header_text for k in ("logika", "funkce", "logic", "function")):
        kind = PG_KIND
    else:
        kind = PERIPHERAL_KIND
    function_idx = next(
        (i for i, h in enumerate(header) if "funkce" in h or "function" in h), None
    )

    result = FlinkImport(kind=kind)
    for row in rows[1:]:
        if len(row) <= max(position_idx, name_idx):
            continue
        position_text = row[position_idx].strip()
        if not position_text.isdigit():
            continue
        position = int(position_text)
        name = row[name_idx].strip()
        if kind == PG_KIND and function_idx is not None and len(row) > function_idx:
            function = _fold(row[function_idx])
            if function not in _DISABLED_FUNCTIONS:
                result.used.add(position)
            if function.startswith(_IMPULSE_PREFIXES):
                result.impulse.add(position)
        if not name:
            continue
        if kind == PG_KIND and _DEFAULT_PG_NAME.match(_fold(name)):
            continue
        result.names[position] = name
    return result


def compress_ranges(values: set[int] | list[int]) -> list[str]:
    """[1,2,3,7,9,10] -> ["1-3", "7", "9-10"] for compact option tokens."""
    numbers = sorted(set(values))
    tokens: list[str] = []
    i = 0
    while i < len(numbers):
        j = i
        while j + 1 < len(numbers) and numbers[j + 1] == numbers[j] + 1:
            j += 1
        tokens.append(str(numbers[i]) if i == j else f"{numbers[i]}-{numbers[j]}")
        i = j + 1
    return tokens
