import re
from dataclasses import dataclass
from dataclasses import fields
from dataclasses import replace
from io import StringIO
from math import isnan
from pathlib import Path

import pytest
from typeline import Comment

from shipslog.picard import STRING_HEADER
from shipslog.picard import DuplicationMetrics
from shipslog.picard import PicardReader
from shipslog.picard import PicardWriter
from shipslog.picard import QualityYieldMetrics
from shipslog.picard import SamComparisonMetric
from shipslog.picard._format import picard_rename
from shipslog.picard._header import PicardHeader
from shipslog.picard._header import header_lines
from tests.compare import same
from tests.picard import HEADER
from tests.picard import LINES
from tests.picard import PICARD_METRICS_FIXTURES
from tests.picard import class_named_in

QUALITY_YIELD = "picard.analysis.CollectQualityYieldMetrics$QualityYieldMetrics"

STRING_HEADER_LINE = "## htsjdk.samtools.metrics.StringHeader"

TOO_LATE = (
    "Write comments before the first row or close,"
    + " since a Picard file holds them only in its header!"
)


@dataclass(frozen=True)
class NotPicard:
    """A dataclass that is not a Picard metrics dataclass."""

    total_reads: int


class Derived(QualityYieldMetrics):
    """A user's subclass of a Picard dataclass."""


def test_writer_writes_the_layout_htsjdk_writes(tmp_path: Path) -> None:
    """The header, a blank line, the section line, the columns and rows, then two blank lines."""
    path = tmp_path / "out.quality_yield_metrics"
    with PicardWriter.from_path[QualityYieldMetrics](path, header=HEADER) as writer:
        writer.write(QualityYieldMetrics(total_reads=10))
    head = header_lines(HEADER)
    columns = list(picard_rename(QualityYieldMetrics).values())
    lines = path.read_text().split("\n")
    assert lines[: len(head) + 3] == [
        *head,
        "",
        f"## METRICS CLASS\t{QUALITY_YIELD}",
        "\t".join(columns),
    ]
    assert lines[len(head) + 3].split("\t")[columns.index("TOTAL_READS")] == "10"
    assert lines[len(head) + 4 :] == ["", "", ""]


@pytest.mark.parametrize("use_write_all", [False, True], ids=["no-call", "write_all"])
def test_writer_without_records_writes_an_empty_metrics_section(
    tmp_path: Path, use_write_all: bool
) -> None:
    """With no records, no section is written, as htsjdk does, and it reads back as no rows."""
    path = tmp_path / "out.quality_yield_metrics"
    with PicardWriter.from_path[QualityYieldMetrics](path, header=HEADER) as writer:
        if use_write_all:
            writer.write_all([])
    assert path.read_text().split("\n") == [*header_lines(HEADER), "", "", "", ""]
    with PicardReader.from_path[QualityYieldMetrics](path) as reader:
        assert list(reader) == []
    assert reader.header == HEADER


@pytest.mark.parametrize("path", PICARD_METRICS_FIXTURES, ids=lambda path: path.name)
def test_every_fixture_reads_back_the_same_after_writing(path: Path, tmp_path: Path) -> None:
    """Every metrics fixture writes and reads back as the same rows and header."""
    kind = class_named_in(path)
    with PicardReader.from_path[kind](path) as reader:
        rows = list(reader)
    out = tmp_path / path.name
    with PicardWriter.from_path[kind](out, header=reader.header) as writer:
        writer.write_all(rows)
    with PicardReader.from_path[kind](out) as again:
        assert same(list(again), rows)
    assert again.header == reader.header


def test_writer_keeps_a_row_whose_first_cell_starts_with_a_comment_prefix(tmp_path: Path) -> None:
    """A library named `#1` is a row, not a comment."""
    assert fields(DuplicationMetrics)[0].name == "library"
    records = [
        DuplicationMetrics(library="#1", read_pairs_examined=4),
        DuplicationMetrics(library="lib2"),
    ]
    path = tmp_path / "out.duplication_metrics"
    with PicardWriter.from_path[DuplicationMetrics](path, header=HEADER) as writer:
        writer.write_all(records)
    assert "\n#1\t" in path.read_text()
    assert list(PicardReader.from_path[DuplicationMetrics](path)) == records


def test_writer_writes_nan_and_negative_infinity_as_picard_does(tmp_path: Path) -> None:
    """NaN and infinity are `?`, minus infinity is `-?`, and booleans are `Y` and `N`."""
    path = tmp_path / "out.duplication_metrics"
    records = [
        DuplicationMetrics(library="a", frac_duplication=float("nan")),
        DuplicationMetrics(library="b", frac_duplication=float("-inf")),
        DuplicationMetrics(library="c", frac_duplication=float("inf")),
    ]
    with PicardWriter.from_path[DuplicationMetrics](path, header=HEADER) as writer:
        writer.write_all(records)
    columns = list(picard_rename(DuplicationMetrics).values())
    lines = path.read_text().split("\n")
    start = lines.index("\t".join(columns)) + 1
    column = columns.index("PERCENT_DUPLICATION")
    assert [line.split("\t")[column] for line in lines[start : start + 3]] == ["?", "-?", "?"]
    read = list(PicardReader.from_path[DuplicationMetrics](path))
    nan = read[0].frac_duplication
    assert nan is not None and isnan(nan)
    assert read[1].frac_duplication == float("-inf")

    flags = tmp_path / "out.sam_comparison_metric"
    with PicardWriter.from_path[SamComparisonMetric](flags, header=HEADER) as writer:
        writer.write_all([
            SamComparisonMetric(are_equal=True),
            SamComparisonMetric(are_equal=False),
        ])
    names = list(picard_rename(SamComparisonMetric).values())
    index = names.index(picard_rename(SamComparisonMetric)["are_equal"])
    flag_lines = flags.read_text().split("\n")
    first = flag_lines.index("\t".join(names)) + 1
    assert [line.split("\t")[index] for line in flag_lines[first : first + 2]] == ["Y", "N"]


def test_writer_writes_a_subclass_under_its_base_java_name(tmp_path: Path) -> None:
    """A subclass of a Picard dataclass writes the section of its Picard parent."""
    path = tmp_path / "out.quality_yield_metrics"
    with PicardWriter.from_path[Derived](path, header=HEADER) as writer:
        writer.write(Derived(total_reads=3))
    assert f"## METRICS CLASS\t{QUALITY_YIELD}\n" in path.read_text()
    assert list(PicardReader.from_path[QualityYieldMetrics](path)) == [
        QualityYieldMetrics(total_reads=3)
    ]


def test_writer_refuses_a_class_that_is_not_a_picard_dataclass(tmp_path: Path) -> None:
    """A class that is not a Picard dataclass is refused before any file is created."""
    path = tmp_path / "out.txt"
    message = "NotPicard is not a Picard metrics dataclass!"
    with pytest.raises(TypeError, match=f"^{re.escape(message)}$"):
        _ = PicardWriter.from_path[NotPicard](path)
    assert not path.exists()


@pytest.mark.parametrize(
    ("header", "text"),
    [
        (PicardHeader(command_line="a\nb", started_on="now"), "a\nb"),
        (PicardHeader(command_line="run", started_on="then\rnow"), "then\rnow"),
        (PicardHeader(others=(("java.lang.String", "a\nb"),)), "a\nb"),
        (PicardHeader(others=(("java.lang.\nString", "text"),)), "java.lang.\nString"),
    ],
)
def test_writer_refuses_a_header_line_holding_a_line_break(
    tmp_path: Path, header: PicardHeader, text: str
) -> None:
    """A header holding a line break is refused before anything is written, naming the text."""
    path = tmp_path / "out.quality_yield_metrics"
    message = f"A header line holds a line break: {text!r}!"
    with pytest.raises(ValueError, match=f"^{re.escape(message)}$"):
        _ = PicardWriter.from_path[QualityYieldMetrics](path, header=header)
    assert not path.exists()
    handle = StringIO()
    with pytest.raises(ValueError, match=f"^{re.escape(message)}$"):
        _ = PicardWriter[QualityYieldMetrics](handle, header=header)
    assert handle.getvalue() == ""


def test_writer_keeps_a_header_holding_a_tab(tmp_path: Path) -> None:
    """A tab in a header line is written as it is, and reads back the same."""
    header = PicardHeader(command_line="a\tb", started_on="c\td")
    path = tmp_path / "out.quality_yield_metrics"
    with PicardWriter.from_path[QualityYieldMetrics](path, header=header):
        pass
    with PicardReader.from_path[QualityYieldMetrics](path) as reader:
        assert reader.header == header


def test_writer_writes_the_default_header_when_given_none(tmp_path: Path) -> None:
    """Without a header, the command line is `shipslog`, then the start time follows."""
    path = tmp_path / "out.quality_yield_metrics"
    with PicardWriter.from_path[QualityYieldMetrics](path):
        pass
    lines = path.read_text().split("\n")
    assert lines[:3] == [
        "## htsjdk.samtools.metrics.StringHeader",
        "# shipslog",
        "## htsjdk.samtools.metrics.StringHeader",
    ]
    assert lines[3].startswith("# Started on: ")


def test_writer_writes_gzip_by_its_suffix(tmp_path: Path) -> None:
    """A path ending in `.gz` is written gzip compressed, and reads back the same."""
    path = tmp_path / "out.quality_yield_metrics.gz"
    records = [QualityYieldMetrics(total_reads=7), QualityYieldMetrics(total_reads=8)]
    with PicardWriter.from_path[QualityYieldMetrics](path, header=HEADER) as writer:
        writer.write_all(records)
    assert path.read_bytes().startswith(b"\x1f\x8b")
    with PicardReader.from_path[QualityYieldMetrics](path) as reader:
        assert same(list(reader), records)
    assert reader.header == HEADER


def test_writer_refuses_a_cell_holding_a_tab(tmp_path: Path) -> None:
    """A text cell holding a tab cannot be written, since Picard has no quoting."""
    path = tmp_path / "out.duplication_metrics"
    with (
        pytest.raises(ValueError, match=r"field 'library' in column 'LIBRARY'"),
        PicardWriter.from_path[DuplicationMetrics](path, header=HEADER) as writer,
    ):
        writer.write(DuplicationMetrics(library="a\tb"))


def test_writer_writes_records_through_write_and_write_all_alike(tmp_path: Path) -> None:
    """Records written one at a time and all at once give the same text."""
    records = [QualityYieldMetrics(total_reads=n) for n in (1, 2, 3)]
    one, many = tmp_path / "one.txt", tmp_path / "many.txt"
    with PicardWriter.from_path[QualityYieldMetrics](one, header=HEADER) as writer:
        for record in records:
            writer.write(record)
    with PicardWriter.from_path[QualityYieldMetrics](many, header=HEADER) as writer:
        writer.write_all(records)
    assert one.read_text() == many.read_text()


def test_writer_closes_twice_and_inside_a_with_block(tmp_path: Path) -> None:
    """Closing again leaves the file as a single close does."""
    once, twice, inside = (tmp_path / name for name in ("once", "twice", "inside"))
    records = [QualityYieldMetrics(total_reads=5)]
    for path in (once, twice, inside):
        writer = PicardWriter.from_path[QualityYieldMetrics](path, header=HEADER)
        with writer:
            writer.write_all(records)
            if path is inside:
                writer.close()
        if path is twice:
            writer.close()
    assert twice.read_text() == once.read_text() == inside.read_text()
    assert same(list(PicardReader.from_path[QualityYieldMetrics](twice)), records)


def test_writer_write_header_writes_nothing(tmp_path: Path) -> None:
    """The column header is written with the first record, so `write_header` changes nothing."""
    plain, called = tmp_path / "plain", tmp_path / "called"
    with PicardWriter.from_path[QualityYieldMetrics](plain, header=HEADER) as writer:
        writer.write(QualityYieldMetrics(total_reads=1))
    with PicardWriter.from_path[QualityYieldMetrics](called, header=HEADER) as writer:
        writer.write_header()
        writer.write(QualityYieldMetrics(total_reads=1))
        writer.write_header()
    assert called.read_text() == plain.read_text()


@pytest.mark.parametrize("use_write_all", [False, True], ids=["write", "write_all"])
def test_writer_writes_comments_as_string_headers_after_the_header(
    tmp_path: Path, use_write_all: bool
) -> None:
    """Comments are string headers after the start time and other headers, read back in order."""
    plain, path = tmp_path / "plain", tmp_path / "out.quality_yield_metrics"
    record = QualityYieldMetrics(total_reads=10)
    with PicardWriter.from_path[QualityYieldMetrics](plain, header=HEADER) as writer:
        writer.write(record)
    with PicardWriter.from_path[QualityYieldMetrics](path, header=HEADER) as writer:
        writer.write_comment("first")
        writer.write_comment("second")
        if use_write_all:
            writer.write_all([record])
        else:
            writer.write(record)
    after = plain.read_text().split("\n")[len(LINES) :]
    assert path.read_text().split("\n") == [
        *LINES,
        STRING_HEADER_LINE,
        "# first",
        STRING_HEADER_LINE,
        "# second",
        *after,
    ]
    with PicardReader.from_path[QualityYieldMetrics](path) as reader:
        assert same(list(reader), [record])
    assert reader.header.others == (
        *HEADER.others,
        (STRING_HEADER, "first"),
        (STRING_HEADER, "second"),
    )


def test_writer_writes_a_comment_into_the_header_of_a_file_without_rows(tmp_path: Path) -> None:
    """With no rows, a comment joins the header at close, and is never read as the command line."""
    path = tmp_path / "out.quality_yield_metrics"
    with PicardWriter.from_path[QualityYieldMetrics](path, header=HEADER) as writer:
        writer.write_comment("note")
    expected = [*LINES, STRING_HEADER_LINE, "# note", "", "", "", ""]
    assert path.read_text() == "\n".join(expected)
    with PicardReader.from_path[QualityYieldMetrics](path) as reader:
        assert list(reader) == []
    assert reader.header == replace(HEADER, others=(*HEADER.others, (STRING_HEADER, "note")))


def test_writer_writes_a_readable_file_for_an_empty_header(tmp_path: Path) -> None:
    """A header with no command line and no comments writes no header lines, and reads back."""
    path = tmp_path / "out.quality_yield_metrics"
    record = QualityYieldMetrics(total_reads=10)
    with PicardWriter.from_path[QualityYieldMetrics](path, header=PicardHeader()) as writer:
        writer.write(record)
    assert path.read_text().startswith("\n## METRICS CLASS")
    with PicardReader.from_path[QualityYieldMetrics](path) as reader:
        assert same(list(reader), [record])
    assert reader.header == PicardHeader()


@pytest.mark.parametrize("text", ["", "   ", " \t"], ids=["empty", "spaces", "tab"])
def test_writer_refuses_a_comment_holding_no_text(tmp_path: Path, text: str) -> None:
    """A comment of only whitespace is refused, as htsjdk cannot read it, and is not kept."""
    plain, called = tmp_path / "plain", tmp_path / "called"
    with PicardWriter.from_path[QualityYieldMetrics](plain, header=HEADER):
        pass
    message = f"A header line holds no text, which htsjdk cannot read: {text!r}!"
    with (
        PicardWriter.from_path[QualityYieldMetrics](called, header=HEADER) as writer,
        pytest.raises(ValueError, match=f"^{re.escape(message)}$"),
    ):
        writer.write_comment(text)
    assert called.read_text() == plain.read_text()


@pytest.mark.parametrize(
    ("text", "kept"),
    [
        ("hello\n", ["hello"]),
        ("hello\r\n", ["hello"]),
        ("hello\r", ["hello"]),
        ("a\nb\n", ["a", "b"]),
    ],
    ids=repr,
)
def test_writer_writes_a_comment_with_a_trailing_line_break(
    tmp_path: Path, text: str, kept: list[str]
) -> None:
    """One line break at the end of a comment ends its last line, and adds no empty one."""
    path = tmp_path / "metrics"
    with PicardWriter.from_path[QualityYieldMetrics](path, header=HEADER) as writer:
        writer.write_comment(text)
    with PicardReader.from_path[QualityYieldMetrics](path) as reader:
        assert [text for _, text in reader.header.others[-len(kept) :]] == kept


def test_writer_writes_a_comment_read_from_a_file_line(tmp_path: Path) -> None:
    """A line read from a file, with its line break, is a comment of its text."""
    note = tmp_path / "note.txt"
    _ = note.write_text("from a file\n")
    path = tmp_path / "metrics"
    with (
        PicardWriter.from_path[QualityYieldMetrics](path, header=HEADER) as writer,
        note.open() as lines,
    ):
        for line in lines:
            writer.write_comment(line)
    with PicardReader.from_path[QualityYieldMetrics](path) as reader:
        assert reader.header.others[-1][1] == "from a file"


@pytest.mark.parametrize("text", ["a\n\nb", "\n", "a\n\n"], ids=repr)
def test_writer_refuses_an_empty_line_in_a_comment(tmp_path: Path, text: str) -> None:
    """An empty line in the middle of a comment, or a second one at its end, is still refused."""
    with (
        PicardWriter.from_path[QualityYieldMetrics](tmp_path / "metrics", header=HEADER) as writer,
        pytest.raises(ValueError, match="^A header line holds no text"),
    ):
        writer.write_comment(text)


def test_writer_refuses_a_comment_when_the_header_has_no_command_line(tmp_path: Path) -> None:
    """A comment would need an empty command line before it, so it is refused and not kept."""
    plain, called = tmp_path / "plain", tmp_path / "called"
    with PicardWriter.from_path[QualityYieldMetrics](plain, header=PicardHeader()):
        pass
    message = "A header line holds no text, which htsjdk cannot read: ''!"
    with (
        PicardWriter.from_path[QualityYieldMetrics](called, header=PicardHeader()) as writer,
        pytest.raises(ValueError, match=f"^{re.escape(message)}$"),
    ):
        writer.write_comment("note")
    assert called.read_text() == plain.read_text()


def test_writer_writes_a_string_header_for_each_line_of_a_comment(tmp_path: Path) -> None:
    """Each line of a string is a header, and a `Comment` drops its `#`."""
    path = tmp_path / "out.quality_yield_metrics"
    with PicardWriter.from_path[QualityYieldMetrics](path, header=HEADER) as writer:
        writer.write_comment("one\ntwo\r\nthree")
        writer.write_comment(Comment(line_number=1, text="## four"))
        writer.write_comment(Comment(line_number=2, text="#  five"))
    assert path.read_text().split("\n") == [
        *LINES,
        STRING_HEADER_LINE,
        "# one",
        STRING_HEADER_LINE,
        "# two",
        STRING_HEADER_LINE,
        "# three",
        STRING_HEADER_LINE,
        "# four",
        STRING_HEADER_LINE,
        "#  five",
        "",
        "",
        "",
        "",
    ]
    with PicardReader.from_path[QualityYieldMetrics](path) as reader:
        assert list(reader) == []
    texts = ["one", "two", "three", "four", " five"]
    assert reader.header.others == (*HEADER.others, *((STRING_HEADER, text) for text in texts))


def test_writer_keeps_a_comment_holding_a_unicode_line_separator_as_one_header(
    tmp_path: Path,
) -> None:
    """Only a carriage return and a line feed split a comment, so a `NEL` stays in one header."""
    path = tmp_path / "out.quality_yield_metrics"
    with PicardWriter.from_path[QualityYieldMetrics](path, header=HEADER) as writer:
        writer.write_comment("a\x85b")
    with PicardReader.from_path[QualityYieldMetrics](path) as reader:
        assert list(reader) == []
    assert reader.header.others == (*HEADER.others, (STRING_HEADER, "a\x85b"))


@pytest.mark.parametrize("use_write_all", [False, True], ids=["write", "write_all"])
def test_writer_refuses_a_comment_after_the_first_row(use_write_all: bool) -> None:
    """A comment after the header is written is refused, and nothing is written."""
    handle = StringIO()
    writer = PicardWriter[QualityYieldMetrics](handle, header=HEADER)
    record = QualityYieldMetrics(total_reads=1)
    if use_write_all:
        writer.write_all([record])
    else:
        writer.write(record)
    before = handle.getvalue()
    with pytest.raises(ValueError, match=f"^{re.escape(TOO_LATE)}$"):
        writer.write_comment("x")
    assert handle.getvalue() == before


def test_writer_refuses_a_comment_holding_a_line_break(tmp_path: Path) -> None:
    """A `Comment` holding a line break is refused as a header line, and is not kept."""
    plain, called = tmp_path / "plain", tmp_path / "called"
    with PicardWriter.from_path[QualityYieldMetrics](plain, header=HEADER):
        pass
    message = "A header line holds a line break: 'a\\nb'!"
    with (
        PicardWriter.from_path[QualityYieldMetrics](called, header=HEADER) as writer,
        pytest.raises(ValueError, match=f"^{re.escape(message)}$"),
    ):
        writer.write_comment(Comment(line_number=1, text="# a\nb"))
    assert called.read_text() == plain.read_text()
