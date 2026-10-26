import os
from collections.abc import Iterable
from collections.abc import Mapping
from itertools import chain
from typing import Any
from typing import TextIO

from typeline import Comment
from typeline import RecordType
from typeline import TsvWriter
from typeline import WriterOptions
from typing_extensions import override

from shipslog._binding import FromPath
from shipslog._stream import SectionStream
from shipslog._stream import as_text_io
from shipslog.picard._format import PICARD_CODECS
from shipslog.picard._format import picard_rename
from shipslog.picard._header import PicardHeader
from shipslog.picard._header import default_header
from shipslog.picard._header import header_lines
from shipslog.picard._reader import histogram_of
from shipslog.picard._reader import java_name
from shipslog.picard._table import HISTOGRAM
from shipslog.picard._table import METRICS_CLASS


def table_options(rename: Mapping[str, str]) -> WriterOptions:
    """The options typeline writes a table of a Picard metrics file with: its labels, then its rows.

    No cell starts with a line break, so no row is mistaken for a comment.

    Args:
        rename: the label of the column of each field, by field name.
    """
    return {
        "codecs": PICARD_CODECS,
        "comment_prefixes": ("\n",),
        "header": True,
        "quoting": False,
        "rename": rename,
    }


class _PicardTableWriter(TsvWriter[RecordType]):
    """A writer of one table of a Picard metrics file, below the header htsjdk writes at its top."""

    from_path: FromPath = FromPath()  # type: ignore[assignment]  # pyright: ignore[reportIncompatibleVariableOverride]  # ty: ignore[invalid-attribute-override]

    def __init__(
        self, handle: TextIO, section: str, rename: Mapping[str, str], header: PicardHeader | None
    ) -> None:
        """Write the header of a Picard metrics file and the blank line after it.

        The table's section line and labels are written with its first row.

        Args:
            handle: a text stream to write the file to, opened with `newline=""`.
            section: the line that starts the table, e.g. its `## METRICS CLASS` line.
            rename: the label of the column of each field, by field name.
            header: the header to write at the top, or None to write `default_header()`.
        """
        self._stream: SectionStream = SectionStream(handle, section)
        super().__init__(as_text_io(self._stream), **table_options(rename))
        self._file: TextIO = handle
        for line in header_lines(default_header() if header is None else header):
            _ = handle.write(f"{line}{os.linesep}")
        _ = handle.write(os.linesep)

    @override
    def write_comment(self, comment: str | Comment) -> None:
        """Refuse a comment, since a Picard metrics file holds none outside its header.

        Raises:
            TypeError: always.
        """
        raise TypeError(
            "A Picard metrics file holds no comments: give its header lines as the writer's header!"
        )

    @override
    def close(self) -> None:
        """Write the blank line that ends the file, and close.

        Closing a writer that is already closed does nothing.
        """
        try:
            if not self._file.closed:
                _ = self._file.write(os.linesep)
        finally:
            super().close()


class PicardWriter(_PicardTableWriter[RecordType]):
    """A writer of a Picard metrics file, from a Picard dataclass, and of the histogram after it."""

    from_path: FromPath = FromPath()

    def __init__(self, handle: TextIO, /, *, header: PicardHeader | None = None) -> None:
        """Write the header of a Picard metrics file, then its table with the first record.

        With no record written, no table is written, as htsjdk writes none for no rows.

        Args:
            handle: a text stream to write the file to, opened with `newline=""`.
            header: the header to write at the top, or None to write `default_header()`.

        Raises:
            TypeError: if the record type is not a Picard metrics dataclass or a subclass of one.
        """
        record_type = self._bound_record_type()
        self._java: str = java_name(record_type)
        section = f"{METRICS_CLASS}\t{self._java}"
        super().__init__(handle, section, picard_rename(record_type), header)

    def write_histogram(self, rows: Iterable[object], /) -> None:
        """Write the histogram after the metrics, as htsjdk does, ending the metrics table.

        With no bins, nothing is written, and the histogram may still be written later.

        Args:
            rows: the bins of the histogram, of a Picard histogram dataclass that files of the
                metrics class hold, or of a subclass of one.

        Raises:
            TypeError: if the bins are not of a Picard histogram dataclass, or are of one that the
                files of the metrics class do not hold.
            ValueError: if the histogram is already written, or no metrics are written before it.
        """
        if self._stream.ended:
            raise ValueError("The histogram is already written!")
        bins = iter(rows)
        try:
            first = next(bins)
        except StopIteration:
            return
        kind: type[Any] = type(first)
        histogram = histogram_of(kind)
        if self._java not in histogram.owners:
            raise TypeError(f"{kind.__name__} is not a histogram of {self._java} files!")
        if not self._stream.started:
            raise ValueError("Write the metrics before their histogram!")
        # Type checkers refuse `TsvWriter[kind]` for a class known only when the program runs.
        bound: type[TsvWriter[Any]] = TsvWriter.__class_getitem__(kind)
        writer = bound(self._file, **table_options(histogram.labels))
        self._stream.end()
        _ = self._file.write(f"{os.linesep}{HISTOGRAM}\t{histogram.key}{os.linesep}")
        writer.write_all(chain([first], bins))

    @override
    def close(self) -> None:
        """End the metrics table with a blank line, unless the histogram has, then the file.

        Closing a writer that is already closed does nothing.
        """
        try:
            if not self._stream.ended and not self._file.closed:
                _ = self._file.write(os.linesep)
        finally:
            super().close()


class PicardHistogramWriter(_PicardTableWriter[RecordType]):
    """A writer of a Picard metrics file of only a histogram, from a Picard histogram dataclass."""

    from_path: FromPath = FromPath()

    def __init__(self, handle: TextIO, /, *, header: PicardHeader | None = None) -> None:
        """Write the header of a Picard metrics file of only a histogram, then its bins.

        With no bin written, no histogram is written, as htsjdk writes none for no bins.

        Args:
            handle: a text stream to write the file to, opened with `newline=""`.
            header: the header to write at the top, or None to write `default_header()`.

        Raises:
            TypeError: if the record type is not a Picard histogram dataclass or a subclass of one,
                or is one that Picard writes after metrics.
        """
        record_type = self._bound_record_type()
        histogram = histogram_of(record_type)
        if histogram.owners:
            owners = " or ".join(sorted(histogram.owners))
            raise TypeError(
                f"{record_type.__name__} belongs in {owners} files!"
                + " Write it with PicardWriter.write_histogram."
            )
        section = f"{HISTOGRAM}\t{histogram.key}"
        super().__init__(handle, section, histogram.labels, header)
        # htsjdk ends the metrics section with a blank line even when it holds no metrics.
        _ = handle.write(os.linesep)
