import os
from collections.abc import Callable
from typing import TextIO
from typing import cast


class SectionStream:
    """A text stream that starts a section of a metrics file once a row follows its labels.

    typeline writes the label row first, and alone when no row follows it, so the label row is
    held back until a row follows it, then written after the section line, when there is one. A
    label row with no row after it never reaches the file, as htsjdk and Riker write no section
    without rows.

    An `on_start` hook runs once, before the stream first writes to its handle.
    """

    def __init__(
        self, handle: TextIO, section: str | None, on_start: Callable[[], None] | None = None
    ) -> None:
        self._handle: TextIO = handle
        self._section: str | None = section
        self._on_start: Callable[[], None] | None = on_start
        self._labels: str = ""
        self._started: bool = False
        self._ended: bool = False

    @property
    def started(self) -> bool:
        """Whether a row has been written, and with it the section line and the label row."""
        return self._started

    @property
    def ended(self) -> bool:
        """Whether the section has ended, so no row may follow."""
        return self._ended

    def write(self, text: str) -> int:
        """Hold the label row, then write the section line, the label row, and each row after it.

        Raises:
            ValueError: if a row is written after the section has ended.
        """
        rows = text
        if not self._labels.endswith("\n"):
            labels, newline, rows = text.partition("\n")
            self._labels += labels + newline
        if not rows:
            return len(text)
        if self._ended:
            raise ValueError("Cannot write metrics after the histogram!")
        if not self._started:
            if self._on_start is not None:
                self._on_start()
            line = "" if self._section is None else f"{self._section}{os.linesep}"
            _ = self._handle.write(f"{line}{self._labels}")
            self._started = True
        _ = self._handle.write(rows)
        return len(text)

    def end(self) -> None:
        """End the section, refusing any row after it and dropping a label row still held."""
        self._ended = True

    def close(self) -> None:
        """Close the handle, dropping a label row still held."""
        self._handle.close()


def as_text_io(stream: SectionStream) -> TextIO:
    """Type a section stream as the text a typeline writer takes, of which it uses `write`, `close`.

    Args:
        stream: the stream to write through.
    """
    return cast(TextIO, cast(object, stream))
