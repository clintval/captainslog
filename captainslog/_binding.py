from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any
from typing import Protocol
from typing import TypeVar
from typing import overload

from typeline import ReaderOptions
from typeline import RecordType
from typeline import WriterOptions
from typing_extensions import Unpack

if TYPE_CHECKING:
    from captainslog.picard._coverage import PicardCoverageReader
    from captainslog.picard._coverage import PicardCoverageWriter
    from captainslog.picard._header import PicardHeader
    from captainslog.picard._reader import PicardHistogramReader
    from captainslog.picard._reader import PicardReader
    from captainslog.picard._writer import PicardHistogramWriter
    from captainslog.picard._writer import PicardWriter

BuiltType_co = TypeVar("BuiltType_co", covariant=True)
"""The reader or writer a `from_path` builds."""


class OpensPath(Protocol[BuiltType_co]):
    """A constructor of a reader of a file, from the file's path and the reader's options."""

    def __call__(self, path: Path | str, /, **options: Unpack[ReaderOptions]) -> BuiltType_co:
        """Open the file at a path, and build its reader."""
        ...


class WritesPath(Protocol[BuiltType_co]):
    """A constructor of a writer of a Picard metrics file, from its path and its header."""

    def __call__(
        self, path: Path | str, /, *, header: "PicardHeader | None" = None
    ) -> BuiltType_co:
        """Open the file at a path, and build its writer."""
        ...


class WritesOptions(Protocol[BuiltType_co]):
    """A constructor of a writer of a plain table, from the file's path and the writer's options."""

    def __call__(self, path: Path | str, /, **options: Unpack[WriterOptions]) -> BuiltType_co:
        """Open the file at a path, and build its writer."""
        ...


class BoundReaderFromPath(Protocol):
    """The `from_path` of a reader class, waiting to be subscripted with a record type."""

    def __getitem__(
        self, record_type: type[RecordType], /
    ) -> "OpensPath[PicardReader[RecordType]]":
        """Bind the record type, giving a constructor of the reader over it."""
        ...


class BoundHistogramReaderFromPath(Protocol):
    """The `from_path` of a histogram reader class, waiting to be subscripted with a record type."""

    def __getitem__(
        self, record_type: type[RecordType], /
    ) -> "OpensPath[PicardHistogramReader[RecordType]]":
        """Bind the record type, giving a constructor of the histogram reader over it."""
        ...


class BoundWriterFromPath(Protocol):
    """The `from_path` of a writer class, waiting to be subscripted with a record type."""

    def __getitem__(
        self, record_type: type[RecordType], /
    ) -> "WritesPath[PicardWriter[RecordType]]":
        """Bind the record type, giving a constructor of the writer over it."""
        ...


class BoundHistogramWriterFromPath(Protocol):
    """The `from_path` of a histogram writer class, waiting to be subscripted with a record type."""

    def __getitem__(
        self, record_type: type[RecordType], /
    ) -> "WritesPath[PicardHistogramWriter[RecordType]]":
        """Bind the record type, giving a constructor of the histogram writer over it."""
        ...


class BoundCoverageReaderFromPath(Protocol):
    """The `from_path` of a coverage reader class, waiting to be subscripted with a record type."""

    def __getitem__(
        self, record_type: type[RecordType], /
    ) -> "OpensPath[PicardCoverageReader[RecordType]]":
        """Bind the record type, giving a constructor of the coverage reader over it."""
        ...


class BoundCoverageWriterFromPath(Protocol):
    """The `from_path` of a coverage writer class, waiting to be subscripted with a record type."""

    def __getitem__(
        self, record_type: type[RecordType], /
    ) -> "WritesOptions[PicardCoverageWriter[RecordType]]":
        """Bind the record type, giving a constructor of the coverage writer over it."""
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

    @overload
    def __get__(self, obj: object, owner: type["PicardReader[Any]"]) -> BoundReaderFromPath: ...

    @overload
    def __get__(
        self, obj: object, owner: type["PicardHistogramReader[Any]"]
    ) -> BoundHistogramReaderFromPath: ...

    @overload
    def __get__(self, obj: object, owner: type["PicardWriter[Any]"]) -> BoundWriterFromPath: ...

    @overload
    def __get__(
        self, obj: object, owner: type["PicardHistogramWriter[Any]"]
    ) -> BoundHistogramWriterFromPath: ...

    @overload
    def __get__(
        self, obj: object, owner: type["PicardCoverageReader[Any]"]
    ) -> BoundCoverageReaderFromPath: ...

    @overload
    def __get__(
        self, obj: object, owner: type["PicardCoverageWriter[Any]"]
    ) -> BoundCoverageWriterFromPath: ...

    @overload
    def __get__(self, obj: object, owner: type[object]) -> object: ...

    def __get__(self, obj: object, owner: type[Any]) -> Any:
        """Hand back the inherited typeline `from_path`, bound to the class it is read through.

        Raises:
            TypeError: if no class after the one holding it, in the class's MRO, has the name.
        """
        name, mro = self._name, owner.__mro__
        at = next((i for i, base in enumerate(mro) if vars(base).get(name) is self), len(mro))
        inherited = next((base for base in mro[at + 1 :] if name in vars(base)), None)
        if inherited is None:
            raise TypeError(f"{owner.__name__} inherits no {name} for FromPath to hand back!")
        return vars(inherited)[name].__get__(obj, owner)
