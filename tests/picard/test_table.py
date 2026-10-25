import re
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import TextIO
from typing import cast

import pytest
from typeline import Comment
from typeline import TsvReader
from typing_extensions import override

from captainslog._files import open_text
from captainslog.picard._table import Table
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
class Bin:
    """A row of the histogram."""

    coverage: int
    count: int


def picard_file(*rows: str, newline: str = "\n") -> str:
    """The text of a Picard metrics file with these metrics rows, and a histogram after them."""
    lines = [*LINES, "", METRICS, "sample\treads", *rows, "", HISTOGRAM, "coverage\tcount"]
    return newline.join([*lines, "0\t10", "1\t20", "", ""])


TEXT = picard_file("a\t1", "b\t2")


def as_handle(table: Table) -> TextIO:
    """A table typed as the handle of a typeline reader, which uses its name, read, and close."""
    return cast(TextIO, cast(object, table))


def metrics(handle: TextIO) -> list[Metric]:
    """The metrics a typeline reader reads from the metrics table of a Picard file."""
    table = as_handle(Table(handle, marker="## METRICS CLASS"))
    with TsvReader[Metric](table, comment_prefixes=(), quoting=False) as reader:
        return list(reader)


def bins(handle: TextIO) -> list[Bin]:
    """The bins a typeline reader reads from the histogram of a Picard file."""
    table = as_handle(Table(handle, marker="## HISTOGRAM"))
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
        open_text(path) as handle,
        pytest.raises(ValueError, match=re.escape(f"'many' on line 11 of '{path}'!")),
    ):
        _ = metrics(handle)


def test_table_names_its_file_when_its_handle_is_named(tmp_path: Path) -> None:
    """A table is named after its handle's file, and has no name when its handle has none."""
    path = tmp_path / "example.metrics"
    _ = path.write_text(TEXT)
    with open_text(path) as handle:
        assert Table(handle, marker="## METRICS CLASS").name == str(path)
    assert Table(StringIO(TEXT), marker="## METRICS CLASS").name is None


def test_table_without_its_marker_reads_no_records() -> None:
    """A file without the marker line has no table, so no records."""
    text = "\n".join([*LINES, "", "sample\treads", "a\t1", ""])
    table = Table(StringIO(text), marker="## METRICS CLASS")
    with TsvReader[Metric](as_handle(table), comment_prefixes=(), quoting=False) as reader:
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
    assert table.marker_line == line


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


@pytest.mark.parametrize("blank", ["", " ", "\t\t", " \t\r"], ids=repr)
def test_table_ends_at_a_line_of_only_whitespace(blank: str) -> None:
    """A table ends at the first line of only whitespace after its first line."""
    text = "\n".join([*LINES, "", METRICS, "sample\treads", "a\t1", blank, "b\t2", ""])
    assert metrics(StringIO(text)) == [Metric("a", 1)]


def test_table_of_only_a_header_reads_no_records() -> None:
    """A table of only its header line has no records, and the table after it reads on."""
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
    assert metrics(StringIO(text)) == []
    assert bins(StringIO(text)) == [Bin(0, 1)]


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
    stop = next(index for index in range(at + 2, len(lines)) if not lines[index].strip())
    with open_text(path) as handle:
        text = Table(handle, marker="## METRICS CLASS").read()
    assert text == "\n" * (at + 1) + "".join(f"{line}\n" for line in lines[at + 1 : stop])


def test_close_closes_the_handle() -> None:
    """Closing a table closes its handle."""
    handle = StringIO(TEXT)
    Table(handle, marker="## METRICS CLASS").close()
    assert handle.closed
