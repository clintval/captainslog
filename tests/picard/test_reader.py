import re
from dataclasses import dataclass
from io import StringIO
from itertools import takewhile
from math import isnan
from pathlib import Path

import pytest
from typeline import Comment

from captainslog.picard import AlignmentSummaryMetrics
from captainslog.picard import DuplicationMetrics
from captainslog.picard import HsMetrics
from captainslog.picard import InsertSizeMetrics
from captainslog.picard import JumpingLibraryMetrics
from captainslog.picard import PicardReader
from captainslog.picard import QualityYieldMetrics
from captainslog.picard._reader import java_name
from tests.compare import same
from tests.picard import DATA
from tests.picard import HEADER
from tests.picard import LINES
from tests.picard import PICARD_METRICS_FIXTURES
from tests.picard import class_named_in


@dataclass(frozen=True)
class Plain:
    """A dataclass that is not a Picard metrics dataclass."""

    total_reads: int


class Derived(HsMetrics):
    """A user's subclass of a Picard dataclass that derives a metric."""

    @property
    def on_target_fraction(self) -> float:
        """The fraction of aligned bases that are on target."""
        return self.on_target_bases / self.pf_bases_aligned


def test_reader_reads_every_level_of_the_alignment_summary_metrics() -> None:
    """A multilevel file holds rows of every accumulation level, and its header."""
    path = DATA / "cmm.alignment_summary_metrics.txt"
    with PicardReader.from_path[AlignmentSummaryMetrics](path) as reader:
        rows = list(reader)
    levels = {(r.sample is None, r.library is None, r.read_group is None) for r in rows}
    assert levels == {
        (True, True, True),
        (False, True, True),
        (False, False, True),
        (False, False, False),
    }
    assert reader.header.command_line.startswith("CollectMultipleMetrics")


@pytest.mark.parametrize("path", PICARD_METRICS_FIXTURES, ids=lambda path: path.name)
def test_reader_reads_every_metrics_fixture(path: Path) -> None:
    """Every metrics file Picard wrote reads as rows of the dataclass its section names."""
    kind = class_named_in(path)
    with PicardReader.from_path[kind](path) as reader:
        assert list(reader)


CONCATENATED = "holds another Picard file after its first, as a concatenation does!"


@pytest.mark.parametrize("path", PICARD_METRICS_FIXTURES, ids=lambda path: path.name)
def test_reader_refuses_a_metrics_fixture_written_twice_into_one_file(
    tmp_path: Path, path: Path
) -> None:
    """Two Picard files written into one, as `cat` writes them, are refused once read."""
    kind = class_named_in(path)
    doubled = tmp_path / path.name
    _ = doubled.write_text(path.read_text() * 2)
    message = f"{doubled} {CONCATENATED}"
    with (
        PicardReader.from_path[kind](doubled) as reader,
        pytest.raises(ValueError, match=f"^{re.escape(message)}$"),
    ):
        _ = list(reader)


@pytest.mark.parametrize(
    "after",
    [
        ["## METRICS CLASS\tpicard.analysis.InsertSizeMetrics", "PAIR_ORIENTATION", "FR"],
        ["## HISTOGRAM\tjava.lang.Integer", "insert_size\tAll_Reads.fr_count", "1\t2"],
        ["## htsjdk.samtools.metrics.StringHeader", "# CollectInsertSizeMetrics"],
    ],
    ids=["metrics", "histogram", "header"],
)
def test_reader_refuses_a_second_file_after_metrics_and_their_histogram(after: list[str]) -> None:
    """After the metrics, only the histogram and blank lines may follow, however many chunks."""
    text = (DATA / "cmm.insert_size_metrics.txt").read_text()
    with (
        PicardReader[InsertSizeMetrics](StringIO("\n".join([text, *after, ""]))) as reader,
        pytest.raises(ValueError, match=f"^The text {re.escape(CONCATENATED)}$"),
    ):
        _ = list(reader)


def test_reader_reads_metrics_followed_by_their_histogram_and_blank_lines() -> None:
    """The histogram and the blank lines htsjdk writes after the metrics are no second file."""
    path = DATA / "cmm.insert_size_metrics.txt"
    text = path.read_text() + "\n \n\n"
    rows = list(PicardReader.from_path[InsertSizeMetrics](path))
    assert len(rows) == 6
    assert list(PicardReader[InsertSizeMetrics](StringIO(text))) == rows


def test_reader_reads_question_marks_as_nan() -> None:
    """Picard writes NaN as `?`, which reads back as NaN."""
    [row] = list(PicardReader.from_path[JumpingLibraryMetrics](DATA / "jump.jumping_metrics.txt"))
    assert isnan(row.jump_mean_insert_size)


def test_reader_reads_a_row_whose_first_value_starts_with_a_hash() -> None:
    """A row of the table is a row, even when its first value starts with `#`."""
    text = (DATA / "dup.duplication_metrics.txt").read_text().replace("\nPond-", "\n#Pond-")
    rows = list(PicardReader[DuplicationMetrics](StringIO(text)))
    assert [row.library for row in rows] == ["NormPond-544932", "#Pond-492101"]


def test_reader_refuses_a_file_of_another_class() -> None:
    """A file whose metrics are of another class is refused, naming both classes."""
    message = (
        r"cmm\.insert_size_metrics\.txt holds picard\.analysis\.InsertSizeMetrics, not HsMetrics!$"
    )
    with pytest.raises(ValueError, match=message):
        _ = PicardReader.from_path[HsMetrics](DATA / "cmm.insert_size_metrics.txt")


def test_reader_refuses_a_histogram_only_file() -> None:
    """A file of only a histogram is refused, pointing to the histogram reader."""
    message = r"holds no metrics, only a histogram! Read it with PicardHistogramReader\.$"
    with pytest.raises(ValueError, match=message):
        _ = PicardReader.from_path[AlignmentSummaryMetrics](
            DATA / "cmm.quality_by_cycle_metrics.txt"
        )


def test_reader_names_text_without_a_file_name_as_the_text() -> None:
    """A handle without a file name is named as the text."""
    text = (DATA / "cmm.quality_by_cycle_metrics.txt").read_text()
    with pytest.raises(ValueError, match=r"^The text holds no metrics, only a histogram!"):
        _ = PicardReader[AlignmentSummaryMetrics](StringIO(text))


def test_reader_refuses_a_file_that_is_not_a_picard_metrics_file() -> None:
    """A file whose first line after the comments starts no section is refused."""
    message = r"hs\.per_target_coverage\.txt is not a Picard metrics file!$"
    with pytest.raises(ValueError, match=message):
        _ = PicardReader.from_path[HsMetrics](DATA / "hs.per_target_coverage.txt")


@pytest.mark.parametrize("keep", ["## METRICS CLASS", "TOTAL_READS"], ids=["marker", "header"])
def test_reader_refuses_a_file_cut_short(tmp_path: Path, keep: str) -> None:
    """A file cut short after its marker line, or after its header, is refused."""
    lines = (DATA / "cmm.quality_yield_metrics.txt").read_text().split("\n")
    marker = next(line for line in lines if line.startswith("## METRICS CLASS"))
    stop = next(index for index, line in enumerate(lines) if line.startswith(keep))
    path = tmp_path / "cut.quality_yield_metrics"
    _ = path.write_text("".join(f"{line}\n" for line in lines[: stop + 1]))
    message = f"{path} holds no rows after its '{marker}' line, so it may be cut short!"
    with pytest.raises(ValueError, match=f"^{re.escape(message)}$"):
        _ = PicardReader.from_path[QualityYieldMetrics](path)


@pytest.mark.parametrize("text", ["", "\n \n\n"], ids=["empty", "blank"])
def test_reader_refuses_a_file_without_a_header_or_a_section(tmp_path: Path, text: str) -> None:
    """An empty or blank file, which htsjdk never writes, is not a Picard metrics file."""
    path = tmp_path / "blank.quality_yield_metrics"
    _ = path.write_text(text)
    message = f"{path} is not a Picard metrics file!"
    with pytest.raises(ValueError, match=f"^{re.escape(message)}$"):
        _ = PicardReader.from_path[QualityYieldMetrics](path)


@pytest.mark.parametrize(
    ("old", "new", "error"),
    [("TOTAL_READS", "TOTAL_READZ", "do not match fields"), ("984\t", "many\t", "'many'")],
    ids=["header", "value"],
)
def test_reader_names_the_line_and_file_of_a_typeline_error(
    tmp_path: Path, old: str, new: str, error: str
) -> None:
    """An error typeline raises names its line in the whole file, and the file's path."""
    lines = (DATA / "cmm.quality_yield_metrics.txt").read_text().split("\n")
    number = next(number for number, line in enumerate(lines, start=1) if line.startswith(old))
    lines[number - 1] = lines[number - 1].replace(old, new, 1)
    path = tmp_path / "bad.quality_yield_metrics"
    _ = path.write_text("\n".join(lines))
    place = re.escape(f"on line {number} of '{path}'!")
    with pytest.raises(ValueError, match=f"{re.escape(error)}.* {place}"):
        _ = list(PicardReader.from_path[QualityYieldMetrics](path))


def test_reader_refuses_a_file_whose_lines_end_with_a_lone_carriage_return() -> None:
    """A file whose lines end with a carriage return alone is refused, not read as empty."""
    text = (DATA / "cmm.quality_yield_metrics.txt").read_text().replace("\n", "\r")
    message = r"^The text breaks its lines with lone carriage returns, not line feeds!$"
    with pytest.raises(ValueError, match=message):
        _ = PicardReader[QualityYieldMetrics](StringIO(text))


def test_reader_refuses_a_record_type_that_is_not_a_picard_dataclass() -> None:
    """A dataclass that is not a Picard dataclass is refused before the file is read."""
    handle = StringIO((DATA / "cmm.quality_yield_metrics.txt").read_text())
    with pytest.raises(TypeError, match=r"^Plain is not a Picard metrics dataclass!$"):
        _ = PicardReader[Plain](handle)
    assert handle.tell() == 0


def test_java_name_of_a_subclass_is_that_of_its_picard_dataclass() -> None:
    """A subclass of a Picard dataclass has the Java name of the dataclass."""
    assert java_name(HsMetrics) == "picard.analysis.directed.HsMetrics"
    assert java_name(Derived) == "picard.analysis.directed.HsMetrics"


def test_reader_accepts_a_subclass_of_the_dataclass_in_the_file() -> None:
    """A subclass of the dataclass a file holds reads the file into the subclass."""
    rows = list(PicardReader.from_path[Derived](DATA / "hs.hs_metrics.txt"))
    assert rows
    assert all(isinstance(r, Derived) for r in rows)


def test_reader_reads_a_crlf_file_as_the_lf_file(tmp_path: Path) -> None:
    """A file whose lines end with CRLF reads as the same file with LF."""
    lf = DATA / "hs.hs_metrics.txt"
    crlf = tmp_path / "hs.hs_metrics.txt"
    _ = crlf.write_text(lf.read_text(), newline="\r\n")
    assert crlf.read_bytes().count(b"\r\n") == lf.read_bytes().count(b"\n")
    with (
        PicardReader.from_path[HsMetrics](crlf) as crlf_reader,
        PicardReader.from_path[HsMetrics](lf) as lf_reader,
    ):
        crlf_rows, lf_rows = list(crlf_reader), list(lf_reader)
        assert crlf_rows
        assert same(crlf_rows, lf_rows)
        assert crlf_reader.header == lf_reader.header


@pytest.mark.parametrize("blank_lines", [1, 3])
def test_reader_of_a_file_without_a_metrics_section_reads_no_records(blank_lines: int) -> None:
    """A file without a metrics section, as htsjdk writes for no rows, holds no records."""
    text = "\n".join([*LINES, *[""] * (blank_lines + 1)])
    with PicardReader[QualityYieldMetrics](StringIO(text)) as reader:
        assert list(reader) == []
        assert reader.header == HEADER


@pytest.mark.parametrize(
    "text",
    ["\n".join(LINES), "\n".join(LINES) + "\n", "\r\n".join(LINES) + "\r\n"],
    ids=["no-line-break", "lf", "crlf"],
)
def test_reader_refuses_a_file_that_ends_after_its_header(tmp_path: Path, text: str) -> None:
    """A header without the blank line htsjdk writes after it may be cut short."""
    path = tmp_path / "cut.quality_yield_metrics"
    _ = path.write_bytes(text.encode())
    message = f"{path} ends after its header, so it may be cut short!"
    with pytest.raises(ValueError, match=f"^{re.escape(message)}$"):
        _ = PicardReader.from_path[QualityYieldMetrics](path)
    message = "The text ends after its header, so it may be cut short!"
    with pytest.raises(ValueError, match=f"^{re.escape(message)}$"):
        _ = PicardReader[QualityYieldMetrics](StringIO(text))


@pytest.mark.parametrize("end", ["", "\n"], ids=repr)
def test_reader_reads_a_table_the_file_ends_without_a_blank_line(end: str) -> None:
    """A metrics table that ends the file, without a blank line after it, reads every row."""
    path = DATA / "cmm.quality_yield_metrics.txt"
    text = path.read_text().rstrip("\n") + end
    with (
        PicardReader[QualityYieldMetrics](StringIO(text)) as cut_reader,
        PicardReader.from_path[QualityYieldMetrics](path) as reader,
    ):
        rows = list(reader)
        assert rows
        assert list(cut_reader) == rows


def test_reader_passes_comment_rows_of_the_table_to_the_callers_on_comment() -> None:
    """A row typeline skips as a comment reaches the caller's `on_comment`, after the header."""
    lines = (
        (DATA / "dup.duplication_metrics.txt")
        .read_text()
        .replace("\nPond-", "\n#Pond-")
        .split("\n")
    )
    number = next(number for number, line in enumerate(lines, start=1) if line.startswith("#Pond-"))
    received: list[Comment] = []
    reader = PicardReader[DuplicationMetrics](
        StringIO("\n".join(lines)), comment_prefixes=("#",), on_comment=received.append
    )
    assert [row.library for row in reader] == ["NormPond-544932"]
    assert received[:4] == [Comment(n, line) for n, line in enumerate(lines[:4], start=1)]
    assert received[4:] == [Comment(number, lines[number - 1])]


def test_reader_passes_comments_to_the_callers_on_comment() -> None:
    """The caller's `on_comment` receives each header line, with its line number, on opening."""
    path = DATA / "cmm.quality_yield_metrics.txt"
    lines = takewhile(lambda line: line.startswith("#"), path.read_text().split("\n"))
    expected = [Comment(number, line) for number, line in enumerate(lines, start=1)]
    assert len(expected) == 4
    received: list[Comment] = []
    with PicardReader.from_path[QualityYieldMetrics](path, on_comment=received.append) as reader:
        assert received == expected
        assert list(reader)
    assert received == expected


TRAILING = "holds text after its last table, which htsjdk does not write!"


@pytest.mark.parametrize("line", ["# done", "\t", "0\t1", " x"], ids=repr)
def test_reader_refuses_text_after_its_last_table(line: str) -> None:
    """Other than blank lines and the histogram, nothing follows the metrics table."""
    text = (DATA / "cmm.insert_size_metrics.txt").read_text()
    head = text[: text.index("## HISTOGRAM")]
    with (
        PicardReader[InsertSizeMetrics](StringIO(f"{head}\n \n{line}\n")) as reader,
        pytest.raises(ValueError, match=f"^The text {re.escape(TRAILING)}$"),
    ):
        _ = list(reader)


def test_reader_reads_metrics_followed_by_blank_lines() -> None:
    """Blank lines after the metrics table, and the histogram after them, are no trailing text."""
    path = DATA / "cmm.insert_size_metrics.txt"
    rows = list(PicardReader.from_path[InsertSizeMetrics](path))
    text = path.read_text() + " \n\n\r\n"
    assert list(PicardReader[InsertSizeMetrics](StringIO(text))) == rows
