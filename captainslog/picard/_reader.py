from typing import Any
from typing import TextIO

from typeline import ReaderOptions
from typeline import RecordType
from typeline import TsvReader
from typing_extensions import Unpack

from captainslog._binding import FromPath
from captainslog.picard._format import PICARD_CODECS
from captainslog.picard._format import picard_rename
from captainslog.picard._header import HeaderParser
from captainslog.picard._header import PicardHeader
from captainslog.picard._java import JAVA_NAMES
from captainslog.picard._table import HISTOGRAM
from captainslog.picard._table import METRICS_CLASS
from captainslog.picard._table import Table
from captainslog.picard._table import as_text_io


def java_name(record_type: type[Any]) -> str:
    """Name the Java class of a Picard dataclass, or of the Picard dataclass a class inherits from.

    Args:
        record_type: the dataclass to name the Java class of.

    Raises:
        TypeError: if the class neither is nor inherits from a Picard metrics dataclass.
    """
    java = next((JAVA_NAMES[kind] for kind in record_type.__mro__ if kind in JAVA_NAMES), None)
    if java is None:
        raise TypeError(f"{record_type.__name__} is not a Picard metrics dataclass!")
    return java


def check_section(table: Table, java: str, record_name: str) -> None:
    """Refuse a file whose first section is not a metrics table of a Java class.

    A file without a section holds no metrics, since htsjdk writes no section for no rows.

    Args:
        table: the metrics table of the file, whose comments and section line are read.
        java: the Java class the table must hold.
        record_name: the name of the dataclass to read the rows into.
    """
    name = "The text" if table.name is None else table.name
    line = table.section_line
    head = [comment.text for comment in table.comments] + ([] if line is None else [line])
    if any("\r" in text for text in head):
        raise ValueError(f"{name} breaks its lines with lone carriage returns, not line feeds!")
    if line is None:
        return
    if line.startswith(f"{METRICS_CLASS}\t"):
        found = line.removeprefix(f"{METRICS_CLASS}\t")
        if found != java:
            raise ValueError(f"{name} holds {found}, not {record_name}!")
    elif line.startswith(HISTOGRAM):
        raise ValueError(
            f"{name} holds no metrics, only a histogram! Read it with PicardHistogramReader."
        )
    else:
        raise ValueError(f"{name} is not a Picard metrics file!")


class PicardReader(TsvReader[RecordType]):
    """A reader of the metrics table of a Picard metrics file, into a Picard dataclass."""

    from_path: FromPath = FromPath()  # type: ignore[assignment]  # pyright: ignore[reportIncompatibleVariableOverride]  # ty: ignore[invalid-attribute-override]

    def __init__(self, handle: TextIO, /, **options: Unpack[ReaderOptions]) -> None:
        """Read the header of a Picard metrics file, and check that its table holds the record type.

        A caller's `on_comment` receives each header line here, before any record is read.

        Args:
            handle: the text of a Picard metrics file.
            options: the options of the reader, left at Picard's defaults when not given.

        Raises:
            TypeError: if the record type is not a Picard metrics dataclass or a subclass of one.
            ValueError: if the file holds another class or only a histogram, is not a Picard
                metrics file, or breaks its lines with lone carriage returns.
        """
        record_type = self._bound_record_type()
        java = java_name(record_type)
        table = Table(handle, marker=METRICS_CLASS)
        check_section(table, java, record_type.__name__)
        on_comment = options.pop("on_comment", None)
        parser = HeaderParser()
        for comment in table.comments:
            parser.feed(comment)
            if on_comment is not None:
                on_comment(comment)
        self._header: PicardHeader = parser.header
        _ = options.setdefault("codecs", PICARD_CODECS)
        _ = options.setdefault("comment_prefixes", ())
        _ = options.setdefault("quoting", False)
        _ = options.setdefault("rename", picard_rename(record_type))
        super().__init__(as_text_io(table), **options)

    @property
    def header(self) -> PicardHeader:
        """The header htsjdk wrote at the top of the file."""
        return self._header
