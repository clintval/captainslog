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
    path = DATA / "cmm.alignment_summary_metrics"
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


def test_reader_reads_question_marks_as_nan() -> None:
    """Picard writes NaN as `?`, which reads back as NaN."""
    [row] = list(PicardReader.from_path[JumpingLibraryMetrics](DATA / "jump.jumping_metrics"))
    assert isnan(row.jump_mean_insert_size)


def test_reader_reads_a_row_whose_first_value_starts_with_a_hash() -> None:
    """A row of the table is a row, even when its first value starts with `#`."""
    text = (DATA / "dup.duplication_metrics").read_text().replace("\nPond-", "\n#Pond-")
    rows = list(PicardReader[DuplicationMetrics](StringIO(text)))
    assert [row.library for row in rows] == ["NormPond-544932", "#Pond-492101"]


def test_reader_refuses_a_file_of_another_class() -> None:
    """A file whose metrics are of another class is refused, naming both classes."""
    message = r"cmm\.insert_size_metrics holds picard\.analysis\.InsertSizeMetrics, not HsMetrics!$"
    with pytest.raises(ValueError, match=message):
        _ = PicardReader.from_path[HsMetrics](DATA / "cmm.insert_size_metrics")


def test_reader_refuses_a_histogram_only_file() -> None:
    """A file of only a histogram is refused, pointing to the histogram reader."""
    message = r"holds no metrics, only a histogram! Read it with PicardHistogramReader\.$"
    with pytest.raises(ValueError, match=message):
        _ = PicardReader.from_path[AlignmentSummaryMetrics](DATA / "cmm.quality_by_cycle_metrics")


def test_reader_names_text_without_a_file_name_as_the_text() -> None:
    """A handle without a file name is named as the text."""
    text = (DATA / "cmm.quality_by_cycle_metrics").read_text()
    with pytest.raises(ValueError, match=r"^The text holds no metrics, only a histogram!"):
        _ = PicardReader[AlignmentSummaryMetrics](StringIO(text))


def test_reader_refuses_a_file_that_is_not_a_picard_metrics_file() -> None:
    """A file whose first line after the comments starts no section is refused."""
    message = r"hs\.per_target_coverage\.txt is not a Picard metrics file!$"
    with pytest.raises(ValueError, match=message):
        _ = PicardReader.from_path[HsMetrics](DATA / "hs.per_target_coverage.txt")


def test_reader_refuses_a_file_whose_lines_end_with_a_lone_carriage_return() -> None:
    """A file whose lines end with a carriage return alone is refused, not read as empty."""
    text = (DATA / "cmm.quality_yield_metrics").read_text().replace("\n", "\r")
    message = r"^The text breaks its lines with lone carriage returns, not line feeds!$"
    with pytest.raises(ValueError, match=message):
        _ = PicardReader[QualityYieldMetrics](StringIO(text))


def test_reader_refuses_a_record_type_that_is_not_a_picard_dataclass() -> None:
    """A dataclass that is not a Picard dataclass is refused before the file is read."""
    handle = StringIO((DATA / "cmm.quality_yield_metrics").read_text())
    with pytest.raises(TypeError, match=r"^Plain is not a Picard metrics dataclass!$"):
        _ = PicardReader[Plain](handle)
    assert handle.tell() == 0


def test_java_name_of_a_subclass_is_that_of_its_picard_dataclass() -> None:
    """A subclass of a Picard dataclass has the Java name of the dataclass."""
    assert java_name(HsMetrics) == "picard.analysis.directed.HsMetrics"
    assert java_name(Derived) == "picard.analysis.directed.HsMetrics"


def test_reader_accepts_a_subclass_of_the_dataclass_in_the_file() -> None:
    """A subclass of the dataclass a file holds reads the file into the subclass."""
    rows = list(PicardReader.from_path[Derived](DATA / "hs.hs_metrics"))
    assert rows
    assert all(isinstance(r, Derived) for r in rows)


def test_reader_reads_a_crlf_file_as_the_lf_file(tmp_path: Path) -> None:
    """A file whose lines end with CRLF reads as the same file with LF."""
    lf = DATA / "hs.hs_metrics"
    crlf = tmp_path / "hs.hs_metrics"
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


def test_reader_of_a_file_without_a_metrics_section_reads_no_records() -> None:
    """A file without a metrics section, as htsjdk writes for no rows, holds no records."""
    with PicardReader[QualityYieldMetrics](StringIO("\n".join([*LINES, "", "", "", ""]))) as reader:
        assert list(reader) == []
        assert reader.header == HEADER


def test_reader_passes_comments_to_the_callers_on_comment() -> None:
    """The caller's `on_comment` receives each header line, with its line number, on opening."""
    path = DATA / "cmm.quality_yield_metrics"
    lines = takewhile(lambda line: line.startswith("#"), path.read_text().split("\n"))
    expected = [Comment(number, line) for number, line in enumerate(lines, start=1)]
    assert len(expected) == 4
    received: list[Comment] = []
    with PicardReader.from_path[QualityYieldMetrics](path, on_comment=received.append) as reader:
        assert received == expected
        assert list(reader)
    assert received == expected
