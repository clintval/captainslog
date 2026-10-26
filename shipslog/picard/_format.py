from dataclasses import fields
from typing import Any

from typeline import Codecs
from typeline import FieldCodec
from typeline.codecs import boolean
from typeline.codecs import nan

from shipslog.picard._java import COLUMN_LABELS
from shipslog.picard._java import JAVA_NAMES

NAN: float = float("nan")
"""The float Picard writes as `?`."""

NEG_INF: float = float("-inf")
"""The float Picard writes as `-?`."""


def read_picard_float(text: str) -> float:
    """Read a float as Picard writes it, with `?` for NaN and `-?` for negative infinity.

    htsjdk writes each float in the JVM's default locale, so under a German or French one Picard
    writes `0,983183`, whose comma is read as a decimal point.

    Args:
        text: the text of the float.

    Raises:
        ValueError: if the text is not a float.
    """
    if text == "?":
        return NAN
    if text == "-?":
        return NEG_INF
    try:
        return float(text.replace(",", ".") if "," in text else text)
    except ValueError:
        raise ValueError(f"Expected a float but found '{text}'!") from None


PICARD_FLOAT: FieldCodec[float] = FieldCodec(
    from_text=read_picard_float, into_text=nan("?", inf="?", neg_inf="-?").into_text
)
"""How Picard writes a float: `?` for NaN and infinity, `-?` for negative infinity, else a number.

`?` reads as NaN, and a number reads with a decimal point or a decimal comma and is written with a
point.
"""

PICARD_CODECS: Codecs = {bool: boolean(true="Y", false="N"), float: PICARD_FLOAT}
"""How Picard writes booleans, as `Y` and `N`, and floats, as `PICARD_FLOAT` reads and writes."""


def picard_rename(record_type: type[Any]) -> dict[str, str]:
    """Name the column of each field of a Picard dataclass, or of a class that inherits from one.

    A field's column is its Java label when that is not its name in upper case, and else its name
    in upper case, without a trailing `_`.

    Args:
        record_type: the dataclass whose fields to name.
    """
    picard = next((kind for kind in record_type.__mro__ if kind in JAVA_NAMES), None)
    labels = {} if picard is None else COLUMN_LABELS.get(picard, {})
    return {
        field.name: labels.get(field.name, field.name.removesuffix("_").upper())
        for field in fields(record_type)
    }
