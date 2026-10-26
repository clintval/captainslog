from dataclasses import fields
from typing import Any

from typeline import Codecs
from typeline.codecs import boolean
from typeline.codecs import nan

from shipslog.picard._java import COLUMN_LABELS
from shipslog.picard._java import JAVA_NAMES

PICARD_CODECS: Codecs = {bool: boolean(true="Y", false="N"), float: nan("?", inf="?", neg_inf="-?")}
"""How Picard writes booleans, as `Y` and `N`, and floats, with `?` for NaN and the infinities."""


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
