from dataclasses import fields
from io import StringIO
from pathlib import Path

import pytest

from captainslog.fgumi import FgumiReader
from captainslog.fgumi import FgumiWriter
from captainslog.fgumi import UmiGroupingMetrics
from captainslog.fgumi import metrics_class
from tests.compare import same
from tests.fgumi import FGUMI_FIXTURES


@pytest.mark.parametrize("path", FGUMI_FIXTURES, ids=lambda path: path.name)
def test_every_fixture_reads_back_as_the_same_rows(path: Path, tmp_path: Path) -> None:
    """Every row of a fixture, written and read again, is the row read from the fixture."""
    kind = metrics_class(path)
    rows = list(FgumiReader.from_path[kind](path))
    written = tmp_path / path.name
    with FgumiWriter.from_path[kind](written) as writer:
        writer.write_all(rows)
    assert same(list(FgumiReader.from_path[kind](written)), rows)


@pytest.mark.parametrize(
    "path", [p for p in FGUMI_FIXTURES if p.suffix == ".txt"], ids=lambda path: path.name
)
def test_every_fixture_is_written_back_as_fgumi_wrote_it(path: Path, tmp_path: Path) -> None:
    """Every fixture, read and written again, is the text fgumi wrote."""
    kind = metrics_class(path)
    written = tmp_path / path.name
    with FgumiWriter.from_path[kind](written) as writer:
        writer.write_all(FgumiReader.from_path[kind](path))
    assert written.read_text() == path.read_text()


def test_a_writer_of_no_rows_writes_the_header_alone(tmp_path: Path) -> None:
    """With no rows, the header is written alone, as fgumi writes it."""
    path = tmp_path / "grouping_metrics.txt"
    with FgumiWriter.from_path[UmiGroupingMetrics](path):
        pass
    names = "\t".join(field.name for field in fields(UmiGroupingMetrics))
    assert path.read_text() == f"{names}\n"


def test_a_writer_refuses_a_comment() -> None:
    """A fgumi metrics file holds no comments."""
    with (
        FgumiWriter[UmiGroupingMetrics](StringIO()) as writer,
        pytest.raises(TypeError, match="no comments"),
    ):
        writer.write_comment("# a comment")
