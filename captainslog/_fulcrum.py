"""What fgbio and fgumi share: how they write values, and a header row that names its dataclass."""

import dataclasses
import math
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from typeline import Codecs
from typeline import FieldCodec
from typeline import open_for_reading
from typeline.codecs import boolean
from typeline.codecs import nan

_NON_FINITE: FieldCodec[float] = nan("NaN", inf="Infinity", neg_inf="-Infinity")


def _float_text(value: float) -> str:
    """A float as fgbio and fgumi write one: a whole number without a point, NaN as `NaN`."""
    if math.isfinite(value) and float(value).is_integer():
        return str(int(value))
    return _NON_FINITE.into_text(value)


FULCRUM_FLOAT: FieldCodec[float] = FieldCodec(
    from_text=_NON_FINITE.from_text, into_text=_float_text
)
"""A float as fgbio and fgumi write one: `NaN`, `Infinity`, and `-Infinity` for the non-finite
floats, which fgbio's `Metric.read` reads and Python's `nan` and `inf` are not, and a whole
number without a decimal point, such as `0`.
"""

FULCRUM_CODECS: Codecs = {bool: boolean(true="true", false="false"), float: FULCRUM_FLOAT}
"""How fgbio and fgumi write booleans, as `true` and `false`, and floats, as `FULCRUM_FLOAT`."""


def columns(record_type: type[Any]) -> tuple[str, ...]:
    """The header row of a dataclass's file: its field names, in order."""
    return tuple(field.name for field in dataclasses.fields(record_type))


def by_header(classes: Iterable[type[Any]], tool: str) -> dict[tuple[str, ...], type[Any]]:
    """Each dataclass by its header row, refusing two dataclasses with one header.

    Raises:
        ValueError: if two of the dataclasses have the same header row.
    """
    found: dict[tuple[str, ...], type[Any]] = {}
    for kind in classes:
        if (other := found.setdefault(columns(kind), kind)) is not kind:
            raise ValueError(
                f"The {tool} dataclasses {other.__name__} and {kind.__name__} share a header!"
            )
    return found


def class_of_header(
    path: Path | str, headers: dict[tuple[str, ...], type[Any]], tool: str
) -> type[Any]:
    """The dataclass whose header row is the first line of a file, plain or compressed.

    Raises:
        ValueError: if the file is empty, or its first line is no header of a dataclass.
    """
    with open_for_reading(path) as handle:
        line = handle.readline().rstrip("\r\n")
    if not line:
        raise ValueError(f"{path} has no header row to name its {tool} dataclass by!")
    kind = headers.get(tuple(line.split("\t")))
    if kind is None:
        raise ValueError(f"The header row of {path} is not the header of a {tool} metrics file!")
    return kind


def check_class(record_type: type[Any], classes: Iterable[type[Any]], tool: str) -> None:
    """Refuse a class that neither is nor inherits from one of a tool's dataclasses.

    Raises:
        TypeError: if the class is not one of the dataclasses or a subclass of one.
    """
    known = set(classes)
    if not any(kind in known for kind in record_type.__mro__):
        raise TypeError(f"{record_type.__name__} is not a {tool} dataclass!")
