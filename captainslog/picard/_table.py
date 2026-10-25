import re
from collections.abc import Callable
from typing import TextIO
from typing import cast

from typeline import Comment

CHUNK: int = 65536
"""The number of characters to read from a handle at a time."""

BLANK_LINE: re.Pattern[str] = re.compile(r"\n[^\S\n\t]*\n")
"""A line break, and the blank line after it with its own line break."""

NOT_BLANK: re.Pattern[str] = re.compile(r"[\S\t]")
"""A character that no blank line holds: a tab, or any that is not whitespace."""


class Table:
    """The text of the one table of a Picard metrics file that follows a marker line.

    Each line up to and including the first line that starts with the marker reads as an empty
    line, so a reader skips it and still counts it, and names each line of the table as the whole
    file numbers it. The table then reads as it is, up to the first blank line after its first
    line, or the end of the file. With no marker line, every line reads as an empty line.

    A blank line holds only whitespace other than tabs, as for typeline, so a row of empty fields
    is a row.
    """

    def __init__(self, handle: TextIO, /, marker: str) -> None:
        """Read the leading comment lines of a Picard metrics file, and wait to read its table.

        Args:
            handle: the text of a Picard metrics file.
            marker: the start of the line before the table, e.g. `## METRICS CLASS`.
        """
        name = getattr(handle, "name", None)
        self.name: str | None = name if isinstance(name, str) else None
        """The name of the file the handle reads, when it has one."""
        self.comments: list[Comment] = []
        """The leading lines that start with `#`, before the first line that does not."""
        self.marker_line: str | None = None
        """The marker line without its line break, or None until read or when there is none."""
        self._handle: TextIO = handle
        self._marker: str = marker
        self._ended: bool = False
        self._text: str = ""
        self._ready: str = ""
        self._step: Callable[[str, bool], None] | None = self._skip
        self._read_comments()

    def read(self, size: int = -1, /) -> str:
        """Read at most `size` characters of the table, or all that is left when it is negative.

        Args:
            size: the most characters to read, or a negative number to read the rest.
        """
        while (step := self._step) is not None and (size < 0 or not self._ready):
            step(self._text + self._pull(), self._ended)
        size = len(self._ready) if size < 0 else size
        text, self._ready = self._ready[:size], self._ready[size:]
        return text

    def close(self) -> None:
        """Close the handle."""
        self._handle.close()

    def _pull(self) -> str:
        """Read the next chunk of the handle, or nothing at its end."""
        chunk = "" if self._ended else self._handle.read(CHUNK)
        self._ended = not chunk
        return chunk

    def _read_comments(self) -> None:
        """Read the leading comment lines, keeping all the text read to read again as the table."""
        text = self._pull().removeprefix("\ufeff")
        start = 0
        while True:
            if start == len(text) and not self._ended:
                text += self._pull()
                continue
            if not text.startswith("#", start):
                break
            stop = text.find("\n", start)
            if stop < 0 and not self._ended:
                text += self._pull()
                continue
            line = text[start:] if stop < 0 else text[start:stop]
            self.comments.append(Comment(len(self.comments) + 1, line.removesuffix("\r")))
            if stop < 0:
                break
            start = stop + 1
        self._text = text

    def _skip(self, text: str, end: bool) -> None:
        """Read each line up to and including the marker line as an empty line."""
        at = f"\n{text}".find(f"\n{self._marker}")
        if at < 0:
            self._ready += "\n" * text.count("\n")
            self._text = text[text.rfind("\n") + 1 :]
            self._step = None if end else self._skip
            return
        self._ready += "\n" * text.count("\n", 0, at)
        stop = text.find("\n", at)
        if stop < 0 and not end:
            self._text = text[at:]
            return
        self.marker_line = (text[at:] if stop < 0 else text[at:stop]).removesuffix("\r")
        self._text = ""
        self._step = None
        if stop >= 0:
            self._ready += "\n"
            self._step = self._lead
            self._lead(text[stop + 1 :], end)

    def _lead(self, text: str, end: bool) -> None:
        """Pass on the blank lines after the marker line, up to the first line of the table."""
        found = NOT_BLANK.search(text)
        if found is not None:
            self._step = self._rows
            self._rows(text, end, start=found.start())
            return
        self._ready += text
        self._text = ""
        self._step = None if end else self._lead

    def _rows(self, text: str, end: bool, start: int = 0) -> None:
        """Pass on the table's lines up to its first blank line, holding back a partial line."""
        blank = BLANK_LINE.search(text, start)
        if blank is not None:
            self._ready += text[: blank.start() + 1]
            self._text = ""
            self._step = None
            return
        cut = text.rfind("\n", start)
        if end or cut < 0:
            cut = len(text)
        self._ready += text[:cut]
        self._text = text[cut:]
        self._step = None if end else self._rows


def as_text_io(table: Table) -> TextIO:
    """Type a table as the text a typeline reader takes, of which it uses `name`, `read`, `close`.

    Args:
        table: the table to read.
    """
    return cast(TextIO, cast(object, table))
