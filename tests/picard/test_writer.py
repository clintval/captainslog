import re
from dataclasses import dataclass
from dataclasses import fields
from math import isnan
from pathlib import Path

import pytest

from captainslog.picard import DuplicationMetrics
from captainslog.picard import PicardReader
from captainslog.picard import PicardWriter
from captainslog.picard import QualityYieldMetrics
from captainslog.picard import SamComparisonMetric
from captainslog.picard._format import picard_rename
from captainslog.picard._header import header_lines
from tests.compare import same
from tests.picard import HEADER
from tests.picard import PICARD_METRICS_FIXTURES
from tests.picard import class_named_in

QUALITY_YIELD = "picard.analysis.CollectQualityYieldMetrics$QualityYieldMetrics"


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
        DuplicationMetrics(library="a", percent_duplication=float("nan")),
        DuplicationMetrics(library="b", percent_duplication=float("-inf")),
    ]
    with PicardWriter.from_path[DuplicationMetrics](path, header=HEADER) as writer:
        writer.write_all(records)
    columns = list(picard_rename(DuplicationMetrics).values())
    rows = [
        line.split("\t") for line in path.read_text().split("\n") if line.startswith(("a", "b"))
    ]
    column = columns.index("PERCENT_DUPLICATION")
    assert [row[column] for row in rows] == ["?", "-?"]
    read = list(PicardReader.from_path[DuplicationMetrics](path))
    assert isnan(read[0].percent_duplication or 0.0)
    assert read[1].percent_duplication == float("-inf")

    flags = tmp_path / "out.sam_comparison_metric"
    with PicardWriter.from_path[SamComparisonMetric](flags, header=HEADER) as writer:
        writer.write_all([
            SamComparisonMetric(are_equal=True),
            SamComparisonMetric(are_equal=False),
        ])
    names = list(picard_rename(SamComparisonMetric).values())
    index = names.index(picard_rename(SamComparisonMetric)["are_equal"])
    body = [line.split("\t") for line in flags.read_text().split("\n")]
    values = [row[index] for row in body if len(row) == len(names)][1:]
    assert values == ["Y", "N"]


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


def test_writer_writes_the_default_header_when_given_none(tmp_path: Path) -> None:
    """Without a header, the command line is `captainslog`, then the start time follows."""
    path = tmp_path / "out.quality_yield_metrics"
    with PicardWriter.from_path[QualityYieldMetrics](path):
        pass
    lines = path.read_text().split("\n")
    assert lines[:3] == ["## htsjdk.samtools.metrics.StringHeader", "# captainslog", lines[2]]
    assert lines[2] == "## htsjdk.samtools.metrics.StringHeader"
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
        pytest.raises(ValueError, match="library"),
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
