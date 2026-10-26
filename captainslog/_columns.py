from collections.abc import Sequence
from operator import attrgetter
from operator import itemgetter
from typing import Any
from typing import TypeVar
from typing import get_origin
from typing import get_type_hints

C = TypeVar("C")


def transpose(rows: Sequence[Any], kind: type[C]) -> C:
    """Transpose the rows of a dataclass into one tuple per field, as a dataclass of columns.

    A field of `kind` annotated as a dict holds the extra columns of the rows by name, as a dict of
    one tuple per name.

    Args:
        rows: the rows to transpose, of at least one row, whose fields `kind` names.
        kind: the dataclass of columns to build.

    Raises:
        ValueError: if the rows do not all name the same extra columns.
    """
    hints = get_type_hints(kind)
    values: dict[str, Any] = {}
    for name, hint in hints.items():
        if get_origin(hint) is not dict:
            values[name] = tuple(map(attrgetter(name), rows))
            continue
        extras: list[dict[str, Any]] = list(map(attrgetter(name), rows))
        names = extras[0].keys()
        if any(extra.keys() != names for extra in extras):
            raise ValueError("Every row must name the same extra columns!")
        values[name] = {key: tuple(map(itemgetter(key), extras)) for key in names}
    return kind(**values)
