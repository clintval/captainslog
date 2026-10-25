from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any
from typing import Protocol
from typing import TypeVar
from typing import cast

from typeline import DelimitedDataReader
from typeline import ReaderOptions
from typeline import RecordType
from typeline import SubscriptableClassmethod
from typing_extensions import Unpack

from captainslog._files import open_text

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


def read_path(
    cls: type[DelimitedDataReader[Any]], path: Path | str, /, **options: Unpack[ReaderOptions]
) -> DelimitedDataReader[Any]:
    """Construct a reader from a file path.

    The file is read as UTF-8, decompressed when it is gzip, bzip2, or xz, and closed once read to
    the end, when a record fails, or when the reader refuses it.

    Args:
        cls: the reader to construct.
        path: the path to the file to read.
        options: the options of the reader, left at the reader's defaults when not given.
    """
    handle = open_text(path)
    try:
        reader = cls(handle, **options)
    except BaseException:
        handle.close()
        raise
    reader._rows.close_when_read = True  # pyright: ignore[reportPrivateUsage]
    return reader


class FromPath:
    """A typeline `from_path` whose constructor builds the class it is read through.

    It opens its file with captainslog's `open_text`, and type checkers see the constructor it
    gives, once subscripted with a record type, build the captainslog class over that type.
    """

    def __init__(self) -> None:
        """Wrap the constructor of a reader from a file path."""
        self._method: SubscriptableClassmethod[...] = SubscriptableClassmethod(read_path)

    def __set_name__(self, owner: type[Any], name: str) -> None:
        """Take the name of the attribute that holds it, to name it in errors."""
        self._method.__set_name__(owner, name)

    def __get__(self, obj: object, owner: type[OwnerType]) -> BoundFromPath[type[OwnerType]]:
        """Bind to the class it is read through."""
        bound = self._method.__get__(obj, owner)
        return cast(BoundFromPath[type[OwnerType]], cast(object, bound))
