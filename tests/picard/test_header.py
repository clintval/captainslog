import re

from typeline import Comment

from captainslog.picard import IndependentReplicateMetric
from captainslog.picard import QualityYieldMetrics
from captainslog.picard._format import picard_rename
from captainslog.picard._header import HeaderParser
from captainslog.picard._header import PicardHeader
from captainslog.picard._header import default_header
from captainslog.picard._header import header_lines
from tests.picard import HEADER
from tests.picard import LINES


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


def test_default_header_names_captainslog_and_the_time_it_starts() -> None:
    """The default header names captainslog, and the local time as htsjdk writes it."""
    header = default_header()
    assert header.command_line == "captainslog"
    assert re.fullmatch(r"\w{3} \w{3} \d{2} \d{2}:\d{2}:\d{2} .+ \d{4}", header.started_on)
    assert header.others == ()


def test_picard_rename_upper_cases_each_field() -> None:
    """A field's column is its name in upper case."""
    assert picard_rename(QualityYieldMetrics)["total_reads"] == "TOTAL_READS"


def test_picard_rename_keeps_the_java_label_of_a_camel_case_field() -> None:
    """A field whose Java label is not its name in upper case keeps that label."""
    assert picard_rename(IndependentReplicateMetric)["n_sites"] == "nSites"


def test_picard_rename_gives_a_subclass_the_columns_of_its_picard_dataclass() -> None:
    """A subclass of a Picard dataclass that adds only a property has its parent's columns."""

    class Yield(QualityYieldMetrics):
        @property
        def pf_fraction(self) -> float:
            return self.pf_reads / self.total_reads

    class Replicate(IndependentReplicateMetric):
        @property
        def sites(self) -> int | None:
            return self.n_sites

    assert picard_rename(Yield) == picard_rename(QualityYieldMetrics)
    assert picard_rename(Replicate) == picard_rename(IndependentReplicateMetric)
    assert picard_rename(Replicate)["n_sites"] == "nSites"
