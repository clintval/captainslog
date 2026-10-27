from pathlib import Path
from typing import Any
from typing import TextIO

from typeline import ReaderOptions
from typeline import RecordType
from typeline import TsvReader
from typing_extensions import Unpack

from captainslog._binding import FromPath
from captainslog._fulcrum import FULCRUM_CODECS
from captainslog._fulcrum import by_header
from captainslog._fulcrum import check_class
from captainslog._fulcrum import class_of_header
from captainslog.fgbio._histograms import HISTOGRAMS
from captainslog.fgbio._scala import SCALA_NAMES

CLASSES: tuple[type[Any], ...] = (*SCALA_NAMES, *HISTOGRAMS)
"""Every fgbio 4.1.1 dataclass: one for each metric class, and one for each other histogram."""

HEADERS: dict[tuple[str, ...], type[Any]] = by_header(CLASSES, "fgbio")
"""Each fgbio 4.1.1 dataclass by the header row of its file, which no two of them share."""


def check_fgbio_class(record_type: type[Any]) -> None:
    """Refuse a class that neither is nor inherits from a fgbio dataclass.

    Args:
        record_type: the class to check.

    Raises:
        TypeError: if the class is not a fgbio dataclass or a subclass of one.
    """
    check_class(record_type, CLASSES, "fgbio")


def metrics_class(path: Path | str) -> type[Any]:
    """Name the fgbio dataclass of a metrics file by its header row, the first line of the file.

    A fgbio tool writes a file under whatever path it is given, so a file is named by its
    columns, not its suffix. The file may be compressed.

    Args:
        path: the path of a fgbio 4.1.1 metrics file.

    Raises:
        ValueError: if the file is empty, or its first line is the header of no fgbio dataclass.
    """
    return class_of_header(path, HEADERS, "fgbio 4.1.1")


class FgbioReader(TsvReader[RecordType]):
    """A reader of a fgbio metrics file, into its fgbio dataclass."""

    from_path: FromPath = FromPath()  # type: ignore[assignment]  # pyright: ignore[reportIncompatibleVariableOverride]  # ty: ignore[invalid-attribute-override]

    def __init__(self, handle: TextIO, /, **options: Unpack[ReaderOptions]) -> None:
        """Read the rows of a fgbio metrics file.

        A file with a header and no rows, as fgbio writes when it has nothing to count, reads as
        no rows.

        Args:
            handle: the text of the file.
            options: the options of the reader, left at fgbio's defaults when not given.

        Raises:
            TypeError: if the record type is not a fgbio dataclass or a subclass of one.
            ValueError: if the columns of the file differ from the record type's fields, naming
                those missing from the file and those it does not expect.
        """
        check_fgbio_class(self.record_type)
        _ = options.setdefault("codecs", FULCRUM_CODECS)
        _ = options.setdefault("comment_prefixes", ())
        super().__init__(handle, **options)
