from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any
from typing import Protocol
from typing import TypeVar
from typing import cast

from typeline import ReaderOptions
from typeline import RecordType
from typing_extensions import Unpack

if TYPE_CHECKING:
    from captainslog.picard._reader import PicardReader

OwnerType = TypeVar("OwnerType")
"""The class a `from_path` is read through."""

OwnerType_co = TypeVar("OwnerType_co", covariant=True)
"""The class a bound `from_path` was read through."""

BuiltType_co = TypeVar("BuiltType_co", covariant=True)
"""The reader or writer a `from_path` builds."""


class OpensPath(Protocol[BuiltType_co]):
    """A constructor of a reader of a file, from the file's path and the reader's options."""

    def __call__(self, path: Path | str, /, **options: Unpack[ReaderOptions]) -> BuiltType_co:
        """Open the file at a path, and build its reader."""
        ...


class BoundFromPath(Protocol[OwnerType_co]):
    """The `from_path` of a captainslog class, waiting to be subscripted with a record type."""

    def __getitem__(
        self: "BoundFromPath[type[PicardReader[Any]]]", record_type: type[RecordType], /
    ) -> "OpensPath[PicardReader[RecordType]]":
        """Bind the record type, giving a constructor of the class over it."""
        ...


class FromPath:
    """The typeline `from_path` a class inherits, which type checkers see build that class.

    Once subscripted with a record type, it builds the class it is read through over that type, e.g.
    `PicardReader.from_path[HsMetrics](path)` builds a `PicardReader[HsMetrics]`.
    """

    def __init__(self) -> None:
        """Wait to learn the name it is held by."""
        self._name: str = ""

    def __set_name__(self, owner: type[Any], name: str) -> None:
        """Take the name it is held by, to find the `from_path` it hides."""
        self._name = name

    def __get__(self, obj: object, owner: type[OwnerType]) -> BoundFromPath[type[OwnerType]]:
        """Hand back the inherited typeline `from_path`, bound to the class it is read through.

        Raises:
            TypeError: if no class after the one holding it, in the class's MRO, has the name.
        """
        name, mro = self._name, owner.__mro__
        at = next((i for i, base in enumerate(mro) if vars(base).get(name) is self), len(mro))
        inherited = next((base for base in mro[at + 1 :] if name in vars(base)), None)
        if inherited is None:
            raise TypeError(f"{owner.__name__} inherits no {name} for FromPath to hand back!")
        return cast(BoundFromPath[type[OwnerType]], vars(inherited)[name].__get__(obj, owner))
