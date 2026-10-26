import re
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import TextIO

import pytest
from typeline import Comment
from typeline import TsvReader
from typeline import open_for_reading
from typing_extensions import override

from shipslog.picard._table import MARK
from shipslog.picard._table import Table
from shipslog.picard._table import as_text_io
from tests.picard import DATA
from tests.picard import LINES
from tests.picard import PICARD_METRICS_FIXTURES

METRICS = "## METRICS CLASS\tpicard.analysis.Example"
HISTOGRAM = "## HISTOGRAM\tjava.lang.Integer"
COMMENTS = [Comment(number, text) for number, text in enumerate(LINES, start=1)]


@dataclass(frozen=True)
class Metric:
    """A row of the metrics table."""

    sample: str
    reads: int


@dataclass(frozen=True)
class Sample:
    """A row of a metrics table whose fields may each be empty."""

    sample: str | None
    reads: int | None
    ratio: float | None


@dataclass(frozen=True)
class Bin:
    """A row of the histogram."""

    coverage: int
    count: int


def picard_file(*rows: str, newline: str = "\n") -> str:
    """The text of a Picard metrics file with these metrics rows, and a histogram after them."""
    lines = [*LINES, "", METRICS, "sample\treads", *rows, "", HISTOGRAM, "coverage\tcount"]
    return newline.join([*lines, "0\t10", "1\t20", "", ""])


TEXT = picard_file("a\t1", "b\t2")


def metrics(handle: TextIO) -> list[Metric]:
    """The metrics a typeline reader reads from the metrics table of a Picard file."""
    table = as_text_io(Table(handle, marker="## METRICS CLASS"))
    with TsvReader[Metric](table, comment_prefixes=(), quoting=False) as reader:
        return list(reader)


def bins(handle: TextIO) -> list[Bin]:
    """The bins a typeline reader reads from the histogram of a Picard file."""
    table = as_text_io(Table(handle, marker="## HISTOGRAM"))
    with TsvReader[Bin](table, comment_prefixes=(), quoting=False) as reader:
        return list(reader)


class Trickle(StringIO):
    """Text that reads at most a few characters at a time, however many are asked for."""

    def __init__(self, text: str, most: int) -> None:
        """Read text at most `most` characters at a time."""
        super().__init__(text)
        self._most: int = most

    @override
    def read(self, size: int | None = -1, /) -> str:
        return super().read(self._most if size is None or size < 0 else min(size, self._most))


def test_table_reads_only_the_metrics_rows() -> None:
    """The metrics table reads its rows, and none of the header or histogram."""
    assert metrics(StringIO(TEXT)) == [Metric("a", 1), Metric("b", 2)]


def test_table_reads_only_the_histogram_rows() -> None:
    """The histogram reads its rows, and none of the header or metrics table."""
    assert bins(StringIO(TEXT)) == [Bin(0, 10), Bin(1, 20)]


def test_table_reads_a_row_whose_first_value_starts_with_a_hash_as_a_row() -> None:
    """A row is a row even when it starts with `#`."""
    assert metrics(StringIO(picard_file("#x\t1"))) == [Metric("#x", 1)]


def test_table_follows_the_first_line_that_starts_with_its_marker() -> None:
    """A line that holds the marker after its start is not the marker line."""
    text = picard_file("a ## HISTOGRAM\t1")
    assert metrics(StringIO(text)) == [Metric("a ## HISTOGRAM", 1)]
    assert bins(StringIO(text)) == [Bin(0, 10), Bin(1, 20)]


def test_table_names_a_line_in_the_whole_file_and_its_path(tmp_path: Path) -> None:
    """A value that cannot be read is named by its line in the whole file, and the file's path."""
    path = tmp_path / "example.metrics"
    _ = path.write_text(picard_file("a\t1", "b\tmany"))
    with (
        open_for_reading(path) as handle,
        pytest.raises(ValueError, match=re.escape(f"'many' on line 11 of '{path}'!")),
    ):
        _ = metrics(handle)


def test_table_names_its_file_when_its_handle_is_named(tmp_path: Path) -> None:
    """A table is named after its handle's file, and has no name when its handle has none."""
    path = tmp_path / "example.metrics"
    _ = path.write_text(TEXT)
    with open_for_reading(path) as handle:
        assert Table(handle, marker="## METRICS CLASS").name == str(path)
    assert Table(StringIO(TEXT), marker="## METRICS CLASS").name is None


def test_table_without_its_marker_reads_no_records() -> None:
    """A file without the marker line has no table, so no records."""
    text = "\n".join([*LINES, "", "sample\treads", "a\t1", ""])
    table = Table(StringIO(text), marker="## METRICS CLASS")
    with TsvReader[Metric](as_text_io(table), comment_prefixes=(), quoting=False) as reader:
        assert list(reader) == []
    assert table.marker_line is None


@pytest.mark.parametrize(
    ("marker", "line"), [("## METRICS CLASS", METRICS), ("## HISTOGRAM", HISTOGRAM)]
)
def test_table_holds_the_leading_comments_and_the_marker_line(marker: str, line: str) -> None:
    """A table holds the comments before the first line that is not one, and its marker line."""
    table = Table(StringIO(TEXT), marker=marker)
    assert table.comments == COMMENTS
    _ = table.read()
    assert table.comments == COMMENTS
    assert table.marker_line == line


def test_table_of_a_file_of_only_comments_holds_them_all() -> None:
    """A file of only comment lines, the last without a line break, holds each and no table."""
    table = Table(StringIO("\n".join(LINES)), marker="## METRICS CLASS")
    assert table.comments == COMMENTS
    assert table.read() == "\n" * (len(LINES) - 1)
    assert table.marker_line is None


@pytest.mark.parametrize("newline", ["\n", "\r\n"], ids=["lf", "crlf"])
@pytest.mark.parametrize("most", [1, 2, 3])
@pytest.mark.parametrize("size", [1, 2, 3, 7, 1000])
@pytest.mark.parametrize(
    ("marker", "line", "skipped", "rows"),
    [
        ("## METRICS CLASS", METRICS, 8, ["sample\treads", "a\t1", "b\t2"]),
        ("## HISTOGRAM", HISTOGRAM, 13, ["coverage\tcount", "0\t10", "1\t20"]),
    ],
    ids=["metrics", "histogram"],
)
def test_table_reads_alike_however_its_text_is_split(
    newline: str, most: int, size: int, marker: str, line: str, skipped: int, rows: list[str]
) -> None:
    """A table reads the same text, comments, and marker line, in pieces of any size."""
    text = picard_file("a\t1", "b\t2", newline=newline)
    expected = "\n" * skipped + "".join(f"{row}{newline}" for row in rows)
    whole = Table(StringIO(text), marker=marker).read(-1)
    table = Table(Trickle(text, most), marker=marker)
    pieces = list(iter(lambda: table.read(size), ""))
    assert all(len(piece) <= size for piece in pieces)
    assert "".join(pieces) == whole == expected
    assert table.read(size) == ""
    assert table.comments == COMMENTS
    assert table.section_line == METRICS
    assert table.marker_line == line


@pytest.mark.parametrize("marker", ["## METRICS CLASS", "## HISTOGRAM"])
@pytest.mark.parametrize(
    ("text", "section"),
    [
        (TEXT, METRICS),
        (picard_file("a\t1", newline="\r\n"), METRICS),
        ("\n".join([*LINES, "", "", HISTOGRAM, "coverage\tcount", "0\t10", "", ""]), HISTOGRAM),
        ("\n".join([*LINES, "", " ", "\x0c\r", METRICS, "sample\treads", ""]), METRICS),
        ("\n".join([*LINES, "", "", "", ""]), None),
        ("\n".join(LINES), None),
        ("sample\treads\na\t1\n", "sample\treads"),
        ("\n\t\nsample\treads\n", "\t"),
        ("", None),
    ],
    ids=[
        "metrics",
        "crlf",
        "histogram-only",
        "after-blank-lines",
        "no-section",
        "only-comments",
        "no-comments",
        "a-tab",
        "empty",
    ],
)
def test_table_holds_the_first_line_after_its_comments_that_is_not_blank(
    marker: str, text: str, section: str | None
) -> None:
    """The section line is the first line after the comments that is not blank, or None."""
    table = Table(Trickle(text, 1), marker=marker)
    assert table.section_line == section


@pytest.mark.parametrize(
    ("text", "ends"),
    [
        ("\n".join(LINES), True),
        ("\n".join(LINES) + "\n", True),
        ("\r\n".join(LINES) + "\r\n", True),
        ("\n".join([*LINES, ""]) + "\n", False),
        ("\n".join([*LINES, " "]), False),
        ("\n".join([*LINES, HISTOGRAM]), False),
        ("", False),
        ("\n", False),
    ],
    ids=["no-line-break", "lf", "crlf", "blank-line", "whitespace", "section", "empty", "blank"],
)
def test_table_notes_a_file_that_ends_in_its_comments(text: str, ends: bool) -> None:
    """A file ends in its comments when no blank line or section line follows them."""
    for most in (1, 1000):
        assert Table(Trickle(text, most), marker="## METRICS CLASS").ends_in_comments is ends


@pytest.mark.parametrize("line", [METRICS, HISTOGRAM])
def test_table_ends_its_comments_at_a_section_without_a_blank_line_before_it(line: str) -> None:
    """A section line that follows the comments directly is a section line, not a comment."""
    text = "\n".join([*LINES, line, "sample\treads", "a\t1", ""])
    table = Table(StringIO(text), marker="## METRICS CLASS")
    assert table.comments == COMMENTS
    assert table.section_line == line


def test_table_reads_a_metrics_table_without_a_blank_line_before_it() -> None:
    """The rows of a section that follows the comments directly are read."""
    text = "\n".join([*LINES, METRICS, "sample\treads", "a\t1", ""])
    assert metrics(StringIO(text)) == [Metric("a", 1)]


@pytest.mark.parametrize("most", [1, 2, 1000])
def test_table_keeps_the_blank_lines_it_reads_to_find_the_section_line(most: int) -> None:
    """The blank lines read to find the section line still count toward each line's number."""
    text = "\n".join([*LINES, "", " ", "", METRICS, "sample\treads", "a\t1", "b\tmany", ""])
    with pytest.raises(ValueError, match="'many' on line 13!"):
        _ = metrics(Trickle(text, most))


def test_table_drops_a_byte_order_mark() -> None:
    """A byte order mark before the first line is not part of it."""
    table = Table(StringIO(f"\ufeff{TEXT}"), marker="## METRICS CLASS")
    assert table.comments == COMMENTS
    assert metrics(StringIO(f"\ufeff{TEXT}")) == [Metric("a", 1), Metric("b", 2)]


@pytest.mark.parametrize("end", ["", "\n"], ids=["without-line-break", "with-line-break"])
def test_table_ends_at_the_end_of_a_file_without_a_closing_blank_line(end: str) -> None:
    """A table that the file ends reads every row."""
    text = "\n".join([*LINES, "", METRICS, "sample\treads", "a\t1", "b\t2"]) + end
    assert metrics(StringIO(text)) == [Metric("a", 1), Metric("b", 2)]


@pytest.mark.parametrize("blank", ["", " ", " \r", "\x0c"], ids=repr)
def test_table_ends_at_a_line_of_only_whitespace_without_a_tab(blank: str) -> None:
    """A table ends at its first blank line, of whitespace other than tabs, after its first line."""
    text = "\n".join([*LINES, "", METRICS, "sample\treads", "a\t1", blank, "b\t2", ""])
    assert metrics(StringIO(text)) == [Metric("a", 1)]


@pytest.mark.parametrize("line", ["\t\t", " \t\r"], ids=repr)
def test_table_reads_a_line_of_whitespace_with_a_tab_as_a_row(line: str) -> None:
    """A line of whitespace that holds a tab is a row, here one typeline cannot read."""
    text = "\n".join([*LINES, "", METRICS, "sample\treads", "a\t1", line, "b\t2", ""])
    with pytest.raises(ValueError, match=r" on line 11\b"):
        _ = metrics(StringIO(text))


@pytest.mark.parametrize("most", [1, 2, 3, 1000])
def test_table_reads_a_row_of_empty_fields_and_the_rows_after_it(most: int) -> None:
    """A row of only empty fields is a row of None, and does not end the table."""
    header = "sample\treads\tratio"
    text = "\n".join([*LINES, "", METRICS, header, "a\t1\t0.5", "\t\t", "c\t3\t1.5", "", ""])
    table = as_text_io(Table(Trickle(text, most), marker="## METRICS CLASS"))
    with TsvReader[Sample](table, comment_prefixes=(), quoting=False) as reader:
        rows = list(reader)
    assert rows == [Sample("a", 1, 0.5), Sample(None, None, None), Sample("c", 3, 1.5)]


@pytest.mark.parametrize("most", [1, 2, 3, 1000])
@pytest.mark.parametrize("newline", ["\n", "\r\n"], ids=["lf", "crlf"])
def test_table_keys_each_repeat_of_a_histogram_label(most: int, newline: str) -> None:
    """The n-th repeat of a label of a histogram reads as the label, `MARK`, and n."""
    labels = "size\tS.count\tS.count\tT.count\tS.count"
    rows = [labels, "1\t2\t3\t4\t5"]
    text = newline.join([*LINES, "", METRICS, "sample\tsample", "a\tb", "", HISTOGRAM, *rows, ""])
    marked = f"size\tS.count\tS.count{MARK}2\tT.count\tS.count{MARK}3"
    histogram = Table(Trickle(text, most), marker="## HISTOGRAM").read().lstrip("\n")
    assert histogram == f"{marked}{newline}1\t2\t3\t4\t5{newline}"
    table = Table(Trickle(text, most), marker="## METRICS CLASS").read().lstrip("\n")
    assert table == f"sample\tsample{newline}a\tb{newline}"


@pytest.mark.parametrize("most", [1, 2, 1000])
def test_table_keys_the_repeats_of_a_label_row_after_blank_lines(most: int) -> None:
    """A label row after blank lines keys its repeats, in a file that ends without a line break."""
    text = "\n".join([*LINES, "", HISTOGRAM, "", "  ", "size\tS.count\tS.count\r", "1\t2\t3"])
    table = Table(Trickle(text, most), marker="## HISTOGRAM").read()
    assert table.endswith(f"\n\n  \nsize\tS.count\tS.count{MARK}2\r\n1\t2\t3")


def test_table_starts_at_a_line_holding_a_tab() -> None:
    """The first line of a table is the first line after the marker that is not blank."""
    table = Table(StringIO("## M\n \n\t\nx\n\nsample\treads\n"), marker="## M")
    assert table.read() == "\n \n\t\nx\n"


def test_table_of_only_a_header_is_refused_as_cut_short() -> None:
    """A table of only its header line may be cut short, since htsjdk writes no empty table."""
    text = "\n".join([
        *LINES,
        "",
        METRICS,
        "sample\treads",
        "",
        HISTOGRAM,
        "coverage\tcount",
        "0\t1",
    ])
    message = (
        f"^The text holds no rows after its '{re.escape(METRICS)}' line, so it may be cut short!$"
    )
    with pytest.raises(ValueError, match=message):
        _ = metrics(StringIO(text))
    assert bins(StringIO(text)) == [Bin(0, 1)]


@pytest.mark.parametrize("most", [1, 2, 1000])
@pytest.mark.parametrize(
    "after",
    [
        [],
        [""],
        ["", " ", ""],
        ["coverage\tcount"],
        ["coverage\tcount", ""],
        ["coverage\tcount", " "],
        ["coverage\tcount", "", "0\t1"],
        ["coverage\tcount\r", "\r", ""],
    ],
    ids=[
        "marker-without-a-line-break",
        "marker",
        "blank-lines",
        "header-without-a-line-break",
        "header",
        "header-and-whitespace",
        "header-and-a-blank-line",
        "crlf-header-and-a-blank-line",
    ],
)
def test_table_refuses_a_histogram_cut_short(most: int, after: list[str]) -> None:
    """A histogram without a header and a row before its end may be cut short."""
    text = "\n".join([*LINES, "", METRICS, "sample\treads", "a\t1", "", HISTOGRAM, *after])
    message = (
        f"^The text holds no rows after its '{re.escape(HISTOGRAM)}' line, so it may be cut short!$"
    )
    with pytest.raises(ValueError, match=message):
        _ = bins(Trickle(text, most))


@pytest.mark.parametrize("most", [1, 2, 1000])
@pytest.mark.parametrize("row", ["0\t1", "0\t1\n", "0\t1\n\n"], ids=repr)
def test_table_of_a_header_and_one_row_is_whole(most: int, row: str) -> None:
    """A table of a header and one row, however it ends, is not cut short."""
    text = "\n".join([*LINES, "", HISTOGRAM, "coverage\tcount", row])
    assert bins(Trickle(text, most)) == [Bin(0, 1)]


def test_table_of_a_file_cut_short_names_the_file(tmp_path: Path) -> None:
    """A table cut short is named by the path of its file."""
    path = tmp_path / "example.metrics"
    _ = path.write_text("\n".join([*LINES, "", METRICS, "sample\treads", ""]))
    message = "^" + re.escape(f"{path} holds no rows after its '{METRICS}' line")
    with (
        open_for_reading(path) as handle,
        pytest.raises(ValueError, match=message),
    ):
        _ = metrics(handle)


@pytest.mark.parametrize(
    "path",
    sorted(path for path in DATA.glob("*") if "\n## HISTOGRAM" in path.read_text()),
    ids=lambda path: path.name,
)
def test_table_of_each_picard_histogram_is_whole(path: Path) -> None:
    """No histogram Picard wrote is refused as cut short."""
    with open_for_reading(path) as handle:
        assert Table(handle, marker="## HISTOGRAM").read().strip("\n")


def test_table_passes_on_blank_lines_before_its_first_line() -> None:
    """Blank lines between the marker line and the table's first line do not end the table."""
    text = "\n".join([*LINES, "", METRICS, "", " ", "sample\treads", "a\t1", "b\tmany", ""])
    with pytest.raises(ValueError, match="'many' on line 13!"):
        _ = metrics(StringIO(text))


@pytest.mark.parametrize("path", PICARD_METRICS_FIXTURES, ids=lambda path: path.name)
def test_table_of_each_picard_file_is_its_metrics_table(path: Path) -> None:
    """The metrics table of a file Picard wrote is the lines after its marker, up to a blank one."""
    lines = path.read_text().split("\n")
    at = next(index for index, line in enumerate(lines) if line.startswith("## METRICS CLASS"))
    blank = [not line.strip() and "\t" not in line for line in lines]
    stop = next(index for index in range(at + 2, len(lines)) if blank[index])
    with open_for_reading(path) as handle:
        text = Table(handle, marker="## METRICS CLASS").read()
    assert text == "\n" * (at + 1) + "".join(f"{line}\n" for line in lines[at + 1 : stop])


@pytest.mark.parametrize("most", [1, 2, 3, 1000])
@pytest.mark.parametrize("marker", ["## METRICS CLASS", "## HISTOGRAM"])
def test_table_refuses_a_second_file_after_it_however_its_text_is_split(
    most: int, marker: str
) -> None:
    """A second file after the table is found in pieces of any size, once the table is read."""
    table = Table(Trickle(TEXT * 2, most), marker=marker)
    pieces: list[str] = []
    message = "^The text holds another Picard file after its first, as a concatenation does!$"
    with pytest.raises(ValueError, match=message):
        while piece := table.read(2):
            pieces.append(piece)
    assert "".join(pieces) == Table(StringIO(TEXT), marker=marker).read()


@pytest.mark.parametrize("most", [1, 2, 3, 1000])
@pytest.mark.parametrize("marker", ["## METRICS CLASS", "## HISTOGRAM"])
def test_table_reads_the_blank_lines_after_a_file_however_its_text_is_split(
    most: int, marker: str
) -> None:
    """Blank lines after the last table, in pieces of any size, are no second file."""
    whole = Table(StringIO(TEXT), marker=marker).read()
    table = Table(Trickle(f"{TEXT}\n \r\n\t\n", most), marker=marker)
    assert "".join(iter(lambda: table.read(2), "")) == whole


def test_close_closes_the_handle() -> None:
    """Closing a table closes its handle."""
    handle = StringIO(TEXT)
    Table(handle, marker="## METRICS CLASS").close()
    assert handle.closed
