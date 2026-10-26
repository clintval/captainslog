import re
from collections import Counter
from collections.abc import Callable
from collections.abc import Sequence
from typing import TextIO
from typing import cast

from typeline import Comment

CHUNK: int = 65536
"""The number of characters to read from a handle at a time."""

METRICS_CLASS: str = "## METRICS CLASS"
"""The start of the line before the metrics table, which names the table's Java class."""

HISTOGRAM: str = "## HISTOGRAM"
"""The start of the line before the histogram, which names the Java class of its bins."""

BLANK_LINE: re.Pattern[str] = re.compile(r"\n[^\S\n\t]*\n")
"""A line break, and the blank line after it with its own line break."""

NOT_BLANK: re.Pattern[str] = re.compile(r"[\S\t]")
"""A character that no blank line holds: a tab, or any that is not whitespace."""

MARK: str = "\x1f"
"""The control character that keys a repeat of a histogram label, which no Picard label holds."""

MARKED: re.Pattern[str] = re.compile(f"{MARK}[0-9]+")
"""The key of a repeat after its label: `MARK` and the repeat's count."""


def mark_repeats(labels: Sequence[str]) -> list[str]:
    """Key the n-th repeat of a label, for n of 2 or more, as the label, `MARK`, and n.

    Args:
        labels: the labels, in order.
    """
    seen: Counter[str] = Counter()
    keys: list[str] = []
    for label in labels:
        seen[label] += 1
        keys.append(label if seen[label] == 1 else f"{label}{MARK}{seen[label]}")
    return keys


def unmark(text: str) -> str:
    """Remove the key of each repeat from a label, or from a row of labels.

    Args:
        text: the label or the row of labels.
    """
    return MARKED.sub("", text)


class Table:
    """The text of the one table of a Picard metrics file that follows a marker line.

    Each line up to and including the first line that starts with the marker reads as an empty
    line, so a reader skips it and still counts it, and names each line of the table as the whole
    file numbers it. The table then reads as it is, up to the first blank line after its first
    line, or the end of the file. With no marker line, every line reads as an empty line.

    A table after a marker line holds a header line and at least one row, since htsjdk writes no
    empty table, so one without them is refused as cut short once its end is read.

    The header line of a histogram, after a `## HISTOGRAM` line, reads with the n-th repeat of a
    label, for n of 2 or more, keyed as the label, `MARK`, and n, since Picard repeats a column for
    a sample and a library of one name. The first of a label keeps it.

    A blank line holds only whitespace other than tabs, as for typeline, so a row of empty fields
    is a row.

    The leading comment lines, and the first line after them that is not blank, which starts the
    file's first section, are read when the table is built, and so is whether the file ends in
    them.
    """

    def __init__(self, handle: TextIO, /, marker: str) -> None:
        """Read the leading comments of a Picard metrics file and its section line, not its table.

        Args:
            handle: the text of a Picard metrics file.
            marker: the start of the line before the table, e.g. `## METRICS CLASS`.
        """
        name = getattr(handle, "name", None)
        self.name: str | None = name if isinstance(name, str) else None
        """The name of the file the handle reads, when it has one."""
        self.comments: list[Comment] = []
        """The leading lines that start with `#`, up to one that does not or starts a section."""
        self.section_line: str | None = None
        """The first line after the comments that is not blank, without its line break, or None."""
        self.ends_in_comments: bool = False
        """Whether the file ends in its comments, with no blank line or section line after them."""
        self.marker_line: str | None = None
        """The marker line without its line break, or None until read or when there is none."""
        self._handle: TextIO = handle
        self._marker: str = marker
        self._ended: bool = False
        self._text: str = ""
        self._ready: str = ""
        self._step: Callable[[str, bool], None] | None = self._skip
        self._past_header: bool = False
        self._has_row: bool = False
        self._read_head()

    @property
    def display_name(self) -> str:
        """How an error names the file: by its name, or as `The text` when it has none."""
        return "The text" if self.name is None else self.name

    def read(self, size: int = -1, /) -> str:
        """Read at most `size` characters of the table, or all that is left when it is negative.

        Args:
            size: the most characters to read, or a negative number to read the rest.

        Raises:
            ValueError: if the table after the marker line ends without a header and a row.
        """
        while (step := self._step) is not None and (size < 0 or not self._ready):
            step(self._text + self._pull(), self._ended)
        if self._step is None and self.marker_line is not None and not self._has_row:
            raise ValueError(
                f"{self.display_name} holds no rows after its '{self.marker_line}' line,"
                + " so it may be cut short!"
            )
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

    def _read_head(self) -> None:
        """Read the comments and the section line, keeping the text read to read as the table."""
        text = self._pull().removeprefix("\ufeff")
        start = 0
        leading = True
        while True:
            stop = text.find("\n", start)
            if stop < 0 and not self._ended:
                text += self._pull()
                continue
            line = (text[start:] if stop < 0 else text[start:stop]).removesuffix("\r")
            if leading and line.startswith("#") and not line.startswith((METRICS_CLASS, HISTOGRAM)):
                self.comments.append(Comment(len(self.comments) + 1, line))
            elif NOT_BLANK.search(line) is not None:
                self.section_line = line
                break
            elif stop >= 0 or line:
                leading = False
            if stop < 0:
                break
            start = stop + 1
        self.ends_in_comments = leading and bool(self.comments) and self.section_line is None
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
            start = text.rfind("\n", 0, found.start()) + 1
            self._ready += text[:start]
            self._step = self._header
            self._header(text[start:], end)
            return
        self._ready += text
        self._text = ""
        self._step = None if end else self._lead

    def _header(self, text: str, end: bool) -> None:
        """Hold the table's first line until it is whole, then key the repeats of a histogram's."""
        stop = text.find("\n")
        if stop < 0 and not end:
            self._text = text
            return
        if self._marker == HISTOGRAM:
            line = text if stop < 0 else text[:stop]
            labels = line.removesuffix("\r")
            keyed = "\t".join(mark_repeats(labels.split("\t")))
            text = f"{keyed}{line[len(labels) :]}{text[len(line) :]}"
        self._step = self._rows
        self._rows(text, end)

    def _rows(self, text: str, end: bool) -> None:
        """Pass on the table's lines up to its first blank line, holding back a partial line."""
        blank = BLANK_LINE.search(text)
        if blank is not None:
            self._look_for_a_row(text, blank.start() + 1)
            self._ready += text[: blank.start() + 1]
            self._text = ""
            self._step = None
            return
        cut = text.rfind("\n")
        if end or cut < 0:
            cut = len(text)
        self._look_for_a_row(text, cut)
        self._ready += text[:cut]
        self._text = text[cut:]
        self._step = None if end else self._rows

    def _look_for_a_row(self, text: str, stop: int) -> None:
        """Note whether the table's text passed on so far holds a row after its header line."""
        if self._has_row:
            return
        start = 0
        if not self._past_header:
            at = text.find("\n", 0, stop)
            if at < 0:
                return
            self._past_header = True
            start = at + 1
        self._has_row = NOT_BLANK.search(text, start, stop) is not None


def as_text_io(table: Table) -> TextIO:
    """Type a table as the text a typeline reader takes, of which it uses `name`, `read`, `close`.

    Args:
        table: the table to read.
    """
    return cast(TextIO, cast(object, table))
