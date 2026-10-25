import os
from typing import TextIO
from typing import cast

from typeline import Comment
from typeline import RecordType
from typeline import TsvWriter
from typing_extensions import override

from captainslog._binding import FromPath
from captainslog.picard._format import PICARD_CODECS
from captainslog.picard._format import picard_rename
from captainslog.picard._header import PicardHeader
from captainslog.picard._header import default_header
from captainslog.picard._header import header_lines
from captainslog.picard._reader import java_name
from captainslog.picard._table import METRICS_CLASS


class _MetricsStream:
    """A text stream that opens the metrics section before the first text written through it."""

    def __init__(self, handle: TextIO, opening: tuple[str, str]) -> None:
        self._handle: TextIO = handle
        self._opening: tuple[str, str] | None = opening

    def write(self, text: str) -> int:
        if text and self._opening is not None:
            for line in self._opening:
                _ = self._handle.write(f"{line}{os.linesep}")
            self._opening = None
        return self._handle.write(text)

    def close(self) -> None:
        self._handle.close()


def as_text_io(stream: _MetricsStream) -> TextIO:
    """Type a metrics stream as the text a typeline writer takes, of which it uses `write`, `close`.

    Args:
        stream: the stream to write through.
    """
    return cast(TextIO, cast(object, stream))


class PicardWriter(TsvWriter[RecordType]):
    """A writer of the metrics table of a Picard metrics file, from a Picard dataclass."""

    from_path: FromPath = FromPath()  # type: ignore[assignment]  # pyright: ignore[reportIncompatibleVariableOverride]  # ty: ignore[invalid-attribute-override]

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
        rename = picard_rename(record_type)
        opening = (f"{METRICS_CLASS}\t{java_name(record_type)}", "\t".join(rename.values()))
        # No cell starts with a line break, so no row is mistaken for a comment.
        super().__init__(
            as_text_io(_MetricsStream(handle, opening)),
            codecs=PICARD_CODECS,
            comment_prefixes=("\n",),
            header=False,
            quoting=False,
            rename=rename,
        )
        self._file: TextIO = handle
        lines = header_lines(default_header() if header is None else header)
        for line in lines:
            _ = handle.write(f"{line}{os.linesep}")
        _ = handle.write(os.linesep)

    @override
    def write_header(self) -> None:
        """Write nothing: the column header is written with the first record, as htsjdk does."""

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
        """Write the blank line that ends the metrics section and the last blank line, and close.

        Closing a writer that is already closed does nothing.
        """
        try:
            if not self._file.closed:
                _ = self._file.write(os.linesep)
                _ = self._file.write(os.linesep)
        finally:
            super().close()
