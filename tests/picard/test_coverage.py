import re
from dataclasses import dataclass
from io import StringIO
from math import isnan
from pathlib import Path

import pytest
from typeline import RecordType

from captainslog.picard import PerBaseCoverage
from captainslog.picard import PerTargetCoverage
from captainslog.picard import PicardCoverageReader
from captainslog.picard import PicardCoverageWriter
from tests.compare import same
from tests.picard import DATA

PER_TARGET = DATA / "hs.per_target_coverage.txt"
PER_BASE = DATA / "hs.per_base_coverage.txt"


@dataclass(frozen=True)
class NotCoverage:
    """A dataclass that is not a Picard coverage dataclass."""

    chrom: str


class DerivedCoverage(PerBaseCoverage):
    """A user's subclass of a Picard coverage dataclass that derives a name."""

    @property
    def locus(self) -> str:
        """The contig and position of the base."""
        return f"{self.chrom}:{self.pos}"


class DerivedTarget(PerTargetCoverage):
    """A user's subclass of the per-target dataclass that derives a span."""

    @property
    def span(self) -> str:
        """The contig, start and end of the target."""
        return f"{self.chrom}:{self.start}-{self.end}"


def test_reader_reads_the_per_target_coverage_fixture() -> None:
    """The first row of the per-target file reads into its fields, and every row is read."""
    with PicardCoverageReader.from_path[PerTargetCoverage](PER_TARGET) as reader:
        rows = list(reader)
    assert len(rows) == 5
    assert rows[0] == PerTargetCoverage(
        chrom="1",
        start=201,
        end=300,
        length=100,
        name="rs7555566",
        pct_gc=0.41,
        mean_coverage=77.49,
        normalized_coverage=1.098526,
        min_normalized_coverage=0.921463,
        max_normalized_coverage=1.261695,
        min_coverage=65,
        max_coverage=89,
        pct_0x=0.0,
        read_count=140,
    )


def test_reader_reads_the_per_base_coverage_fixture() -> None:
    """The first row of the per-base file reads into its fields, and every row is read."""
    with PicardCoverageReader.from_path[PerBaseCoverage](PER_BASE) as reader:
        rows = list(reader)
    assert len(rows) == 500
    assert rows[0] == PerBaseCoverage(chrom="1", pos=201, target="rs7555566", coverage=70)


@pytest.mark.parametrize(
    ("path", "kind"),
    [
        pytest.param(PER_TARGET, PerTargetCoverage, id=PER_TARGET.name),
        pytest.param(PER_BASE, PerBaseCoverage, id=PER_BASE.name),
    ],
)
def test_coverage_fixtures_read_back_the_same_after_writing(
    path: Path, kind: type[RecordType], tmp_path: Path
) -> None:
    """A fixture written and read back holds the same rows, under the same header line."""
    out = tmp_path / path.name
    with PicardCoverageReader.from_path[kind](path) as reader:
        rows = list(reader)
    with PicardCoverageWriter.from_path[kind](out) as writer:
        writer.write_all(rows)
    with PicardCoverageReader.from_path[kind](out) as reader:
        assert same(list(reader), rows)
    assert out.read_bytes().partition(b"\n")[0:2] == path.read_bytes().partition(b"\n")[0:2]


def test_reader_and_writer_keep_a_contig_that_starts_with_a_hash(tmp_path: Path) -> None:
    """A contig whose name starts with a hash is not mistaken for a comment."""
    path = tmp_path / "out.txt"
    row = PerBaseCoverage(chrom="#1", pos=5, target="t", coverage=3)
    with PicardCoverageWriter.from_path[PerBaseCoverage](path) as writer:
        writer.write(row)
    with PicardCoverageReader.from_path[PerBaseCoverage](path) as reader:
        assert list(reader) == [row]


def test_writer_writes_the_lone_header_for_no_rows(tmp_path: Path) -> None:
    """With no rows, the writer writes only the header line, which reads as no rows."""
    path = tmp_path / "out.txt"
    with PicardCoverageWriter.from_path[PerBaseCoverage](path):
        pass
    assert path.read_text() == "chrom\tpos\ttarget\tcoverage\n"
    with PicardCoverageReader.from_path[PerBaseCoverage](path) as reader:
        assert list(reader) == []


def test_reader_reads_nan_as_picard_writes_it(tmp_path: Path) -> None:
    """Picard writes a NaN as a question mark, which reads back as NaN."""
    path = tmp_path / "out.txt"
    lines = PER_TARGET.read_text().splitlines()
    cells = lines[1].split("\t")
    cells[7:10] = ["?", "?", "?"]
    _ = path.write_text("\n".join([lines[0], "\t".join(cells)]) + "\n")
    with PicardCoverageReader.from_path[PerTargetCoverage](path) as reader:
        (row,) = list(reader)
    assert isnan(row.normalized_coverage)
    assert isnan(row.min_normalized_coverage)
    assert isnan(row.max_normalized_coverage)
    assert row.mean_coverage == 77.49


def test_reader_refuses_a_class_that_is_not_a_coverage_dataclass() -> None:
    """A record type that is no coverage dataclass is refused before the text is read."""
    handle = StringIO(PER_BASE.read_text())
    message = "NotCoverage is not a Picard coverage dataclass!"
    with pytest.raises(TypeError, match=f"^{re.escape(message)}$"):
        _ = PicardCoverageReader[NotCoverage](handle)
    assert handle.tell() == 0


def test_writer_refuses_a_class_that_is_not_a_coverage_dataclass(tmp_path: Path) -> None:
    """A record type that is no coverage dataclass is refused before the file is created."""
    path = tmp_path / "out.txt"
    message = "NotCoverage is not a Picard coverage dataclass!"
    with pytest.raises(TypeError, match=f"^{re.escape(message)}$"):
        _ = PicardCoverageWriter.from_path[NotCoverage](path)
    assert not path.exists()


def test_reader_reads_a_users_subclass_of_a_coverage_dataclass() -> None:
    """A subclass of a coverage dataclass reads, under the columns of its parent."""
    with PicardCoverageReader.from_path[DerivedCoverage](PER_BASE) as reader:
        first = next(iter(reader))
    assert isinstance(first, DerivedCoverage)
    assert first.locus == "1:201"


def test_reader_reads_a_subclass_of_per_target_coverage_under_its_renamed_column() -> None:
    """A subclass of the per-target dataclass inherits the `%gc` column of its parent."""
    with PicardCoverageReader.from_path[DerivedTarget](PER_TARGET) as reader:
        first = next(iter(reader))
    assert isinstance(first, DerivedTarget)
    assert first.pct_gc == 0.41
    assert first.span == "1:201-300"


def test_reader_lets_a_callers_option_win_over_a_default() -> None:
    """A rename the caller gives replaces the reader's own."""
    text = "contig\tpos\ttarget\tcoverage\n1\t5\tt\t3\n"
    rename = {"chrom": "contig"}
    reader = PicardCoverageReader[PerBaseCoverage](StringIO(text), rename=rename)
    assert list(reader) == [PerBaseCoverage(chrom="1", pos=5, target="t", coverage=3)]


def test_writer_lets_a_callers_option_win_over_a_default() -> None:
    """With `header=False` the writer writes no header line."""
    handle = StringIO()
    writer = PicardCoverageWriter[PerBaseCoverage](handle, header=False)
    writer.write(PerBaseCoverage(chrom="1", pos=5, target="t", coverage=3))
    assert handle.getvalue() == "1\t5\tt\t3\n"


def test_writer_refuses_a_comment(tmp_path: Path) -> None:
    """A Picard coverage file holds no comments, so none is written."""
    path = tmp_path / "out.txt"
    message = "A Picard coverage file holds no comments!"
    with (
        PicardCoverageWriter.from_path[PerBaseCoverage](path) as writer,
        pytest.raises(TypeError, match=f"^{re.escape(message)}$"),
    ):
        writer.write_comment("note")
    assert path.read_text() == "chrom\tpos\ttarget\tcoverage\n"
