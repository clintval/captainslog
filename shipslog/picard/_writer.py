import os
import re
from collections.abc import Iterable
from collections.abc import Mapping
from dataclasses import replace
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
from shipslog.picard._header import STRING_HEADER
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
        self,
        handle: TextIO,
        section: str,
        rename: Mapping[str, str],
        header: PicardHeader | None,
        blank_lines: int = 1,
    ) -> None:
        """Start a Picard metrics file, whose header is written before anything else reaches it.

        The header and the blank lines after it are written before the table's first row, or at
        `close` when no row is written, so comments written before then join the header. The
        table's section line and labels are written with its first row.

        Args:
            handle: a text stream to write the file to, opened with `newline=""`.
            section: the line that starts the table, e.g. its `## METRICS CLASS` line.
            rename: the label of the column of each field, by field name.
            header: the header to write at the top, or None to write `default_header()`.
            blank_lines: the number of blank lines written after the header.

        Raises:
            ValueError: if a header's class name or text holds a line break, or only whitespace.
        """
        self._stream: SectionStream = SectionStream(handle, section, on_start=self._write_head)
        super().__init__(as_text_io(self._stream), **table_options(rename))
        self._file: TextIO = handle
        self._blank_lines: int = blank_lines
        self._picard_header: PicardHeader = default_header() if header is None else header
        self._head: str | None = self._head_of(self._picard_header)

    def _head_of(self, header: PicardHeader) -> str:
        """The text of a header's lines and the blank lines after them."""
        lines = [*header_lines(header), *[""] * self._blank_lines]
        return "".join(f"{line}{os.linesep}" for line in lines)

    def _write_head(self) -> None:
        """Write the header and the blank lines after it, unless they are already written."""
        if self._head is not None:
            _ = self._file.write(self._head)
            self._head = None

    @override
    def write_comment(self, comment: str | Comment) -> None:
        """Add a comment to the header, as string headers after the header's own.

        Each line of a string is one header. A `Comment`, such as one a reader of a plain table
        sent to `on_comment`, is one header of its text, without its leading `#` characters and one
        space after them; to copy a Picard file's header, pass `header=reader.header` instead.
        The comments read back in order, at the end of `reader.header.others`, as
        `(STRING_HEADER, text)` pairs. htsjdk trims the text of each header line when it reads it
        back.

        Args:
            comment: the comment to add.

        Raises:
            ValueError: if the header is already written, with the first row, the histogram, or at
                `close`, or if a comment holds a line break in a `Comment` or only whitespace on a
                line, which htsjdk cannot read.
        """
        if self._head is None:
            raise ValueError(
                "Write comments before the first row or close,"
                + " since a Picard file holds them only in its header!"
            )
        if isinstance(comment, str):
            texts = re.split(r"\r\n|\r|\n", comment)
        else:
            texts = [comment.text.lstrip("#").removeprefix(" ")]
        others = (*self._picard_header.others, *((STRING_HEADER, text) for text in texts))
        header = replace(self._picard_header, others=others)
        self._head = self._head_of(header)
        self._picard_header = header

    @override
    def close(self) -> None:
        """Write the header if nothing else was, then the blank line that ends the file, and close.

        Closing a writer that is already closed does nothing.
        """
        try:
            if not self._file.closed:
                self._write_head()
                _ = self._file.write(os.linesep)
        finally:
            super().close()


class PicardWriter(_PicardTableWriter[RecordType]):
    """A writer of a Picard metrics file, from a Picard dataclass, and of the histogram after it.

    Each float is written as the shortest text that reads back as the same number, such as
    `0.30000000000000004` or `1e-7`, not rounded to htsjdk's six places. htsjdk reads either form.
    """

    from_path: FromPath = FromPath()

    def __init__(self, handle: TextIO, /, *, header: PicardHeader | None = None) -> None:
        """Start a Picard metrics file, whose header and table are written with its first record.

        With no record written, no table is written, as htsjdk writes none for no rows, and the
        header is written at `close`.

        Args:
            handle: a text stream to write the file to, opened with `newline=""`.
            header: the header to write at the top, or None to write `default_header()`.

        Raises:
            TypeError: if the record type is not a Picard metrics dataclass or a subclass of one.
            ValueError: if a header's class name or text holds a line break, or only whitespace.
        """
        record_type = self.record_type
        self._java: str = java_name(record_type)
        section = f"{METRICS_CLASS}\t{self._java}"
        super().__init__(handle, section, picard_rename(record_type), header)

    def write_histogram(self, rows: Iterable[object], /) -> None:
        """Write the histogram after the metrics, as htsjdk does, ending the metrics table.

        With no bins, nothing is written, and the histogram may still be written later.

        The columns a histogram keeps by name are written after its fixed columns, so a
        `DuplicationMetrics` histogram's `optical_sets` moves to the end of the row. htsjdk reads
        it by its label.

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
        """End the file as htsjdk does, and close the writer.

        Write the header if nothing was written, end the metrics table with a blank line, unless the
        histogram already did, then end the file with another.

        Closing a writer that is already closed does nothing.
        """
        try:
            if not self._file.closed:
                self._write_head()
                if not self._stream.ended:
                    _ = self._file.write(os.linesep)
        finally:
            super().close()


class PicardHistogramWriter(_PicardTableWriter[RecordType]):
    """A writer of a Picard metrics file of only a histogram, from a Picard histogram dataclass.

    Each float is written as the shortest text that reads back as the same number, such as
    `0.30000000000000004` or `1e-7`, not rounded to htsjdk's six places. htsjdk reads either form.

    The columns a histogram keeps by name are written after its fixed columns, so a
    `DuplicationMetrics` histogram's `optical_sets` moves to the end of the row. htsjdk reads it by
    its label.
    """

    from_path: FromPath = FromPath()

    def __init__(self, handle: TextIO, /, *, header: PicardHeader | None = None) -> None:
        """Start a Picard metrics file of only a histogram, written with its first bin.

        With no bin written, no histogram is written, as htsjdk writes none for no bins, and the
        header is written at `close`.

        Args:
            handle: a text stream to write the file to, opened with `newline=""`.
            header: the header to write at the top, or None to write `default_header()`.

        Raises:
            TypeError: if the record type is not a Picard histogram dataclass or a subclass of one,
                or is one that Picard writes after metrics.
            ValueError: if a header's class name or text holds a line break, or only whitespace.
        """
        record_type = self.record_type
        histogram = histogram_of(record_type)
        if histogram.owners:
            owners = " or ".join(sorted(histogram.owners))
            raise TypeError(
                f"{record_type.__name__} belongs in {owners} files!"
                + " Write it with PicardWriter.write_histogram."
            )
        section = f"{HISTOGRAM}\t{histogram.key}"
        # htsjdk ends the metrics section with a blank line even when it holds no metrics.
        super().__init__(handle, section, histogram.labels, header, blank_lines=2)
