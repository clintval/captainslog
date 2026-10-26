import re

import pytest
from typeline import Comment

from shipslog.picard._header import HeaderParser
from shipslog.picard._header import PicardHeader
from shipslog.picard._header import default_header
from shipslog.picard._header import header_lines
from tests.picard import HEADER
from tests.picard import LINES

STRING_HEADER = "htsjdk.samtools.metrics.StringHeader"
VERSION_HEADER = "htsjdk.samtools.metrics.VersionHeader"


def test_header_parser_reads_the_command_line_start_time_and_other_headers() -> None:
    """The first two string headers are the command line and start time; the rest are others."""
    parser = HeaderParser()
    for number, text in enumerate(LINES, start=1):
        parser.feed(Comment(number, text))
    assert parser.header == HEADER


def test_header_parser_keeps_a_later_string_header_among_the_others() -> None:
    """A string header after the command line and start time is another header."""
    parser = HeaderParser()
    lines = [*LINES, "## htsjdk.samtools.metrics.StringHeader", "# Started on: later"]
    for number, text in enumerate(lines, start=1):
        parser.feed(Comment(number, text))
    later = ("htsjdk.samtools.metrics.StringHeader", "Started on: later")
    assert parser.header.others == (*HEADER.others, later)


def test_header_parser_without_comments_reads_an_empty_header() -> None:
    """A file without a header has an empty header."""
    assert HeaderParser().header == PicardHeader()


def test_header_parser_skips_a_text_line_without_a_class_line_before_it() -> None:
    """A `#` line is the text of a header only right after the `##` line naming its class."""
    parser = HeaderParser()
    for number, text in enumerate(["# stray", *LINES, "# stray"], start=1):
        parser.feed(Comment(number, text))
    assert parser.header == HEADER


def test_header_lines_are_the_lines_htsjdk_writes() -> None:
    """A header is written as the `##` and `#` lines of each of its headers, in order."""
    assert header_lines(HEADER) == LINES


def test_header_lines_of_an_empty_header_are_none() -> None:
    """An empty header is written as no lines."""
    assert header_lines(PicardHeader()) == []


@pytest.mark.parametrize(
    ("header", "text"),
    [
        (PicardHeader(started_on="today"), ""),
        (PicardHeader(others=((STRING_HEADER, "note"),)), ""),
        (PicardHeader(command_line="   ", started_on="today"), "   "),
        (PicardHeader(command_line="tool", others=((STRING_HEADER, " \t"),)), " \t"),
        (PicardHeader(others=((VERSION_HEADER, ""),)), ""),
    ],
    ids=[
        "no-command-line",
        "no-command-line-string",
        "blank-command-line",
        "blank-text",
        "blank-other",
    ],
)
def test_header_lines_refuse_a_line_holding_no_text(header: PicardHeader, text: str) -> None:
    """A line of only whitespace, such as the place of an empty command line, is refused."""
    message = f"A header line holds no text, which htsjdk cannot read: {text!r}!"
    with pytest.raises(ValueError, match=f"^{re.escape(message)}$"):
        _ = header_lines(header)


@pytest.mark.parametrize(
    "header",
    [
        HEADER,
        PicardHeader(command_line="CollectQualityYieldMetrics I=in.bam O=out.txt"),
        PicardHeader(command_line="tool", started_on="Sat Oct 24 10:00:00 HST 2026"),
        PicardHeader(others=((VERSION_HEADER, "picard\t3.5.0"),)),
        PicardHeader(command_line="tool", others=((STRING_HEADER, "Started on: later"),)),
        PicardHeader(command_line="tool", others=((STRING_HEADER, "note"),)),
        PicardHeader(),
    ],
    ids=[
        "full",
        "command-line",
        "command-line-and-start-time",
        "version-header",
        "command-line-and-start-time-string-header",
        "command-line-and-string-header",
        "empty",
    ],
)
def test_header_lines_read_back_as_the_same_header(header: PicardHeader) -> None:
    """The lines written for any header read back as that header."""
    parser = HeaderParser()
    for number, text in enumerate(header_lines(header), start=1):
        parser.feed(Comment(number, text))
    assert parser.header == header


def test_default_header_names_shipslog_and_the_time_it_starts() -> None:
    """The default header names shipslog, and the local time as htsjdk writes it."""
    header = default_header()
    assert header.command_line == "shipslog"
    assert re.fullmatch(r"\w{3} \w{3} \d{2} \d{2}:\d{2}:\d{2} .+ \d{4}", header.started_on)
    assert header.others == ()
