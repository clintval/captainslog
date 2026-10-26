from collections.abc import Mapping
from collections.abc import Sequence
from dataclasses import fields
from pathlib import Path
from typing import Any
from typing import TextIO

from typeline import ReaderOptions
from typeline import RecordType
from typeline import TsvReader
from typing_extensions import Unpack

from captainslog._binding import FromPath
from captainslog._files import open_text
from captainslog.picard._format import PICARD_CODECS
from captainslog.picard._format import picard_rename
from captainslog.picard._header import HeaderParser
from captainslog.picard._header import PicardHeader
from captainslog.picard._histograms import HISTOGRAMS
from captainslog.picard._histograms import Histogram
from captainslog.picard._java import JAVA_NAMES
from captainslog.picard._table import CHUNK
from captainslog.picard._table import HISTOGRAM
from captainslog.picard._table import METRICS_CLASS
from captainslog.picard._table import NOT_BLANK
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


def find_section(table: Table, name: str) -> str | None:
    """Read the first section line of a file, refusing a file that cannot hold a metrics table.

    Args:
        table: the table of the file, whose comments and section line are read.
        name: how to name the file in an error.

    Returns:
        The section line, or None for a file with a header and no section, since htsjdk writes no
        section for no rows.

    Raises:
        ValueError: if the file breaks its lines with lone carriage returns, or is not a Picard
            metrics file: it has neither a header nor a section, or its first line after the
            header starts no section.
    """
    line = table.section_line
    head = [comment.text for comment in table.comments] + ([] if line is None else [line])
    if any("\r" in text for text in head):
        raise ValueError(f"{name} breaks its lines with lone carriage returns, not line feeds!")
    if line is None and table.comments:
        return None
    if line is None or not line.startswith((f"{METRICS_CLASS}\t", HISTOGRAM)):
        raise ValueError(f"{name} is not a Picard metrics file!")
    return line


def section_java(line: str | None) -> str | None:
    """Name the Java class of the metrics a section line starts.

    Args:
        line: the section line of a file, or None for a file without a section.

    Returns:
        The Java class a `## METRICS CLASS` line names, or None for no section or a histogram.
    """
    if line is None or not line.startswith(f"{METRICS_CLASS}\t"):
        return None
    return line.removeprefix(f"{METRICS_CLASS}\t")


def check_section(table: Table, java: str, record_name: str) -> None:
    """Refuse a file whose first section is not a metrics table of a Java class.

    A file with a header and no section holds no metrics, since htsjdk writes no section for no
    rows.

    Args:
        table: the metrics table of the file, whose comments and section line are read.
        java: the Java class the table must hold.
        record_name: the name of the dataclass to read the rows into.

    Raises:
        ValueError: if the file breaks its lines with lone carriage returns, holds metrics of
            another Java class or only a histogram, or is not a Picard metrics file: it has
            neither a header nor a section, or its first line after the header starts no section.
    """
    name = table.display_name
    line = find_section(table, name)
    if line is None:
        return
    found = section_java(line)
    if found is None:
        raise ValueError(
            f"{name} holds no metrics, only a histogram! Read it with PicardHistogramReader."
        )
    if found != java:
        raise ValueError(f"{name} holds {found}, not {record_name}!")


def histogram_of(record_type: type[Any]) -> Histogram:
    """Find how Picard writes a histogram dataclass, or the one a class inherits from.

    Args:
        record_type: the dataclass to find the histogram of.

    Raises:
        TypeError: if the class neither is nor inherits from a Picard histogram dataclass.
    """
    found = next((HISTOGRAMS[kind] for kind in record_type.__mro__ if kind in HISTOGRAMS), None)
    if found is None:
        raise TypeError(f"{record_type.__name__} is not a Picard histogram dataclass!")
    return found


def check_histogram_section(table: Table, owners: frozenset[str], record_name: str) -> None:
    """Refuse a file that cannot hold a histogram, from the Java classes whose files hold it.

    A file with a header and no section holds no histogram, since htsjdk writes no section for no
    data.

    Args:
        table: the histogram table of the file, whose comments and section line are read.
        owners: the Java classes whose files hold the histogram, or none for a histogram alone.
        record_name: the name of the dataclass to read the bins into.

    Raises:
        ValueError: if the file breaks its lines with lone carriage returns, holds metrics of a
            class whose files hold no such histogram, holds only a histogram where the histogram
            follows metrics, or is not a Picard metrics file.
    """
    name = table.display_name
    line = find_section(table, name)
    if line is None:
        return
    found = section_java(line)
    if found is not None and found not in owners:
        raise ValueError(f"{name} holds {found}, whose files hold no {record_name}!")
    if found is None and owners:
        raise ValueError(f"{name} holds only a histogram, which is not {record_name}!")


def histogram_classes(java: str | None, labels: Sequence[str]) -> list[type[Any]]:
    """Find the histogram dataclasses that match the metrics class and label row of a file.

    A dataclass with a `NamedExtraColumns` field matches a row that starts with the label of its
    key and holds each of its fixed labels, with its other columns anywhere. A dataclass without
    one matches only a row of its fixed labels.

    Args:
        java: the Java class the file's `## METRICS CLASS` line names, or None for a file of only
            a histogram.
        labels: the label of each column of the histogram, in order.
    """
    row = list(labels)
    return [
        kind
        for kind, histogram in HISTOGRAMS.items()
        if (java in histogram.owners if histogram.owners else java is None)
        and labels_match(
            len(fields(kind)) > len(histogram.labels), list(histogram.labels.values()), row
        )
    ]


def labels_match(extra: bool, fixed: list[str], row: list[str]) -> bool:
    """Whether a histogram label row holds the columns of a histogram dataclass.

    Args:
        extra: whether the dataclass keeps the columns no fixed field takes, by name.
        fixed: the labels of the columns of its fixed fields, in order.
        row: the label of each column of the histogram, in order.
    """
    if not extra:
        return row == fixed
    return row[:1] == fixed[:1] and set(fixed) <= set(row)


def read_labels(table: Table) -> list[str] | None:
    """Read the label row of the histogram of a file, and none of the bins after it.

    Args:
        table: the histogram table of the file.

    Returns:
        The label of each column, in order, or None when the file holds no histogram.

    Raises:
        ValueError: if the histogram has no rows after its `## HISTOGRAM` line, so may be cut short.
    """
    text = ""
    while chunk := table.read(CHUNK):
        text += chunk
        found = NOT_BLANK.search(text)
        if found is None:
            text = text[text.rfind("\n") + 1 :]
            continue
        stop = text.find("\n", found.start())
        if stop >= 0:
            start = text.rfind("\n", 0, found.start()) + 1
            return text[start:stop].removesuffix("\r").split("\t")
    return None


def histogram_class(path: Path | str) -> type[Any]:
    """Find the dataclass of the histogram of a Picard metrics file, from its first lines.

    The file is read up to the label row of its histogram, and no further.

    Args:
        path: the path to the file, which may be gzip, bzip2, or xz compressed.

    Raises:
        ValueError: if the file holds no histogram, holds one of a shape or metrics class no
            Picard 3.5.0 histogram has, holds no rows after its `## HISTOGRAM` line, so may be cut
            short, is not a Picard metrics file, or breaks its lines with lone carriage returns.
    """
    with open_text(path) as handle:
        table = Table(handle, marker=HISTOGRAM)
        line = find_section(table, str(path))
        labels = read_labels(table)
    if labels is None:
        raise ValueError(f"{path} holds no histogram!")
    kinds = histogram_classes(section_java(line), labels)
    if not kinds:
        raise ValueError(
            f"{path} holds a histogram captainslog does not know: {', '.join(labels)}!"
        )
    return kinds[0]


def metrics_class(path: Path | str) -> type[Any]:
    """Find the dataclass of the metrics table of a Picard metrics file, from its first lines.

    Args:
        path: the path to the file, which may be gzip, bzip2, or xz compressed.

    Raises:
        ValueError: if the file holds a class that is not a Picard 3.5.0 metrics class, holds no
            metrics table, is not a Picard metrics file, or breaks its lines with lone carriage
            returns.
    """
    with open_text(path) as handle:
        found = section_java(find_section(Table(handle, marker=METRICS_CLASS), str(path)))
    if found is None:
        raise ValueError(
            f"{path} holds no metrics table! "
            + "If it holds only a histogram, find its type with histogram_class."
        )
    kind = next((kind for kind, java in JAVA_NAMES.items() if java == found), None)
    if kind is None:
        raise ValueError(f"{path} holds {found}, which is not a Picard 3.5.0 metrics class!")
    return kind


def with_table_defaults(options: ReaderOptions, rename: Mapping[str, str]) -> None:
    """Leave the options of a reader of a Picard table at Picard's defaults, where not given.

    Args:
        options: the options of the reader, which the defaults are set in.
        rename: the column of each field, unless the options name their own.
    """
    _ = options.setdefault("codecs", PICARD_CODECS)
    _ = options.setdefault("comment_prefixes", ())
    _ = options.setdefault("quoting", False)
    _ = options.setdefault("rename", rename)


class _PicardTableReader(TsvReader[RecordType]):
    """A reader of one table of a Picard metrics file, and of the header htsjdk wrote above it."""

    from_path: FromPath = FromPath()  # type: ignore[assignment]  # pyright: ignore[reportIncompatibleVariableOverride]  # ty: ignore[invalid-attribute-override]

    def __init__(self, table: Table, rename: Mapping[str, str], options: ReaderOptions) -> None:
        """Read the header from the comments of a table, then start reading the table.

        A caller's `on_comment` receives each header line here, and the options not given are left
        at Picard's defaults.

        Args:
            table: the table of the file, whose comments are the header.
            rename: the column of each field, unless the options name their own.
            options: the options of the reader.
        """
        on_comment = options.get("on_comment")
        parser = HeaderParser()
        for comment in table.comments:
            parser.feed(comment)
            if on_comment is not None:
                on_comment(comment)
        self._header: PicardHeader = parser.header
        with_table_defaults(options, rename)
        super().__init__(as_text_io(table), **options)

    @property
    def header(self) -> PicardHeader:
        """The header htsjdk wrote at the top of the file."""
        return self._header


class PicardReader(_PicardTableReader[RecordType]):
    """A reader of the metrics table of a Picard metrics file, into a Picard dataclass."""

    from_path: FromPath = FromPath()

    def __init__(self, handle: TextIO, /, **options: Unpack[ReaderOptions]) -> None:
        """Read the header of a Picard metrics file, and check that its table holds the record type.

        A caller's `on_comment` receives each header line here, before any record is read, then
        each line of the table that `comment_prefixes` skips, as it is read.

        Args:
            handle: the text of a Picard metrics file.
            options: the options of the reader, left at Picard's defaults when not given.

        Raises:
            TypeError: if the record type is not a Picard metrics dataclass or a subclass of one.
            ValueError: if the file holds another class or only a histogram, is not a Picard
                metrics file, breaks its lines with lone carriage returns, or holds no rows after
                its `## METRICS CLASS` line, so may be cut short.
        """
        record_type = self._bound_record_type()
        java = java_name(record_type)
        table = Table(handle, marker=METRICS_CLASS)
        check_section(table, java, record_type.__name__)
        super().__init__(table, picard_rename(record_type), options)


class PicardHistogramReader(_PicardTableReader[RecordType]):
    """A reader of the histogram of a Picard metrics file, into a Picard histogram dataclass."""

    from_path: FromPath = FromPath()

    def __init__(self, handle: TextIO, /, **options: Unpack[ReaderOptions]) -> None:
        """Read the header of a Picard metrics file, and check that the file can hold the histogram.

        A caller's `on_comment` receives each header line here, before any bin is read, then
        each line of the histogram that `comment_prefixes` skips, as it is read.

        A file whose metrics hold the histogram, but which holds none, reads as no bins.

        Args:
            handle: the text of a Picard metrics file.
            options: the options of the reader, left at Picard's defaults when not given.

        Raises:
            TypeError: if the record type is not a Picard histogram dataclass or a subclass of one.
            ValueError: if the file holds metrics whose files hold no such histogram, holds only a
                histogram where the histogram follows metrics, is not a Picard metrics file,
                breaks its lines with lone carriage returns, or holds no rows after its
                `## HISTOGRAM` line, so may be cut short.
        """
        record_type = self._bound_record_type()
        histogram = histogram_of(record_type)
        table = Table(handle, marker=HISTOGRAM)
        check_histogram_section(table, histogram.owners, record_type.__name__)
        super().__init__(table, histogram.labels, options)
