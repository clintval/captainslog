from dataclasses import dataclass
from datetime import datetime

from typeline import Comment

STRING_HEADER: str = "htsjdk.samtools.metrics.StringHeader"
"""The Java class of the headers that hold the command line and the start time."""

STARTED_ON: str = "Started on: "
"""The start of the text of the header that holds the start time."""


@dataclass(frozen=True, kw_only=True)
class PicardHeader:
    """The headers that htsjdk writes at the top of a Picard metrics file."""

    command_line: str = ""
    """The command line of the program that wrote the file."""

    started_on: str = ""
    """When the program started, e.g. `Sat Oct 24 10:00:00 HST 2026`."""

    others: tuple[tuple[str, str], ...] = ()
    """Every other header, as its Java class name and its text, in order."""


class HeaderParser:
    """Read the header of a Picard metrics file from its comment lines, fed one at a time.

    A `##` line names the Java class of the header whose text is on the `#` line after it.
    """

    def __init__(self) -> None:
        """Start with an empty header."""
        self._java: str | None = None
        self._command_line: str | None = None
        self._started_on: str | None = None
        self._others: list[tuple[str, str]] = []

    def feed(self, comment: Comment) -> None:
        """Read the next comment line of the file.

        Args:
            comment: the next comment line.
        """
        text = comment.text
        if text.startswith("##"):
            self._java = text[2:].strip()
            return
        java, self._java = self._java, None
        if java is None or not text.startswith("#"):
            return
        value = text[1:].removeprefix(" ")
        if java == STRING_HEADER and self._command_line is None:
            self._command_line = value
        elif java == STRING_HEADER and self._started_on is None and value.startswith(STARTED_ON):
            self._started_on = value.removeprefix(STARTED_ON)
        else:
            self._others.append((java, value))

    @property
    def header(self) -> PicardHeader:
        """The header of the comment lines fed so far."""
        return PicardHeader(
            command_line=self._command_line or "",
            started_on=self._started_on or "",
            others=tuple(self._others),
        )


def header_lines(header: PicardHeader) -> list[str]:
    """Write a header as the `##` and `#` lines that htsjdk writes, in order, without line breaks.

    A header with a start time or a string header needs a command line, since an empty one would be
    written as a line that htsjdk cannot read.

    Args:
        header: the header to write.

    Raises:
        ValueError: if a header's class name or text holds a line break, or only whitespace.
    """
    for text in (
        header.command_line,
        header.started_on,
        *(t for pair in header.others for t in pair),
    ):
        if "\r" in text or "\n" in text:
            raise ValueError(f"A header line holds a line break: {text!r}!")
    strings = [text for java, text in header.others if java == STRING_HEADER]
    pairs: list[tuple[str, str]] = []
    if header.command_line or header.started_on or strings:
        pairs.append((STRING_HEADER, header.command_line))
    if header.started_on or any(text.startswith(STARTED_ON) for text in strings):
        pairs.append((STRING_HEADER, f"{STARTED_ON}{header.started_on}"))
    pairs.extend(header.others)
    for _, text in pairs:
        if not text.strip():
            raise ValueError(f"A header line holds no text, which htsjdk cannot read: {text!r}!")
    return [line for java, text in pairs for line in (f"## {java}", f"# {text}")]


def default_header() -> PicardHeader:
    """The header captainslog writes when it is given none: its name, and the local time now."""
    started_on = datetime.now().astimezone().strftime("%a %b %d %H:%M:%S %Z %Y")
    return PicardHeader(command_line="captainslog", started_on=started_on)
