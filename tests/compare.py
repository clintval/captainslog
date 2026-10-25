from dataclasses import fields
from dataclasses import is_dataclass
from math import isnan
from typing import cast


def same(left: object, right: object) -> bool:
    """Whether two records, or two lists of records, are equal, where NaN equals NaN.

    Example:
        ```pycon
        >>> same([0.5, float("nan")], [0.5, float("nan")])
        True
        >>> same([0.5, float("nan")], [0.5, 0.0])
        False

        ```
    """
    if is_dataclass(left) and not isinstance(left, type):
        return type(left) is type(right) and all(
            same(getattr(left, field.name), getattr(right, field.name)) for field in fields(left)
        )
    if isinstance(left, float) and isinstance(right, float) and isnan(left):
        return isnan(right)
    if isinstance(left, list) and isinstance(right, list):
        lefts, rights = cast(list[object], left), cast(list[object], right)
        return len(lefts) == len(rights) and all(map(same, lefts, rights))
    return left == right
