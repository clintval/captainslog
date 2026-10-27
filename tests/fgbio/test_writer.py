from dataclasses import fields
from io import StringIO
from pathlib import Path

import pytest

from captainslog.fgbio import FgbioReader
from captainslog.fgbio import FgbioWriter
from captainslog.fgbio import UmiGroupingMetric
from captainslog.fgbio import metrics_class
from tests.compare import same
from tests.fgbio import FGBIO_FIXTURES


@pytest.mark.parametrize("path", FGBIO_FIXTURES, ids=lambda path: path.name)
def test_every_fixture_reads_back_as_the_same_rows(path: Path, tmp_path: Path) -> None:
    """Every row of a fixture, written and read again, is the row read from the fixture."""
    kind = metrics_class(path)
    rows = list(FgbioReader.from_path[kind](path))
    written = tmp_path / path.name
    with FgbioWriter.from_path[kind](written) as writer:
        writer.write_all(rows)
    assert same(list(FgbioReader.from_path[kind](written)), rows)


def same_cell(left: str, right: str) -> bool:
    """Whether two cells hold the same text, or the same number spelled two ways."""
    if left == right:
        return True
    try:
        return float(left) == float(right)
    except ValueError:
        return False


@pytest.mark.parametrize(
    "path", [p for p in FGBIO_FIXTURES if p.suffix == ".txt"], ids=lambda path: path.name
)
def test_every_fixture_is_written_back_as_fgbio_wrote_it(path: Path, tmp_path: Path) -> None:
    """Every fixture, read and written again, is the text fgbio wrote, but for a float's spelling.

    fgbio writes a float near zero as `-2.22045E-16`, where the writer writes the shortest text
    that reads back as the same number, `-2.22045e-16`.
    """
    kind = metrics_class(path)
    written = tmp_path / path.name
    with FgbioWriter.from_path[kind](written) as writer:
        writer.write_all(FgbioReader.from_path[kind](path))
    lines = zip(written.read_text().splitlines(), path.read_text().splitlines(), strict=True)
    for left, right in lines:
        cells = zip(left.split("\t"), right.split("\t"), strict=True)
        assert all(same_cell(*pair) for pair in cells), (left, right)


def test_a_writer_of_no_rows_writes_the_header_alone(tmp_path: Path) -> None:
    """With no rows, the header is written alone, as fgbio writes it."""
    path = tmp_path / "grouping_metrics.txt"
    with FgbioWriter.from_path[UmiGroupingMetric](path):
        pass
    names = "\t".join(field.name for field in fields(UmiGroupingMetric))
    assert path.read_text() == f"{names}\n"


def test_a_writer_refuses_a_comment() -> None:
    """A fgbio metrics file holds no comments."""
    with (
        FgbioWriter[UmiGroupingMetric](StringIO()) as writer,
        pytest.raises(TypeError, match="no comments"),
    ):
        writer.write_comment("# a comment")
