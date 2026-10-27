import gzip
from dataclasses import dataclass
from dataclasses import fields
from io import StringIO
from pathlib import Path
from typing import Any

import pytest

from captainslog.fgumi import FgumiReader
from captainslog.fgumi import UmiGroupingMetrics
from captainslog.fgumi import metrics_class
from captainslog.fgumi._reader import HEADERS
from tests.fgumi import FGUMI_FIXTURES


@dataclass(frozen=True)
class NotFgumi:
    """A dataclass that is not a fgumi dataclass."""

    accepted_sam_records: int


class DerivedGrouping(UmiGroupingMetrics):
    """A user's subclass of a fgumi dataclass that derives a value."""

    @property
    def accepted(self) -> int:
        """The records accepted."""
        return self.accepted_sam_records


def header(kind: type[Any]) -> str:
    """The header row of a dataclass's file."""
    return "\t".join(field.name for field in fields(kind))


def test_fixtures_exist() -> None:
    """The fgumi fixtures were written by fgumi."""
    assert FGUMI_FIXTURES


@pytest.mark.parametrize("path", FGUMI_FIXTURES, ids=lambda path: path.name)
def test_metrics_class_names_the_dataclass_that_reads_every_fixture(path: Path) -> None:
    """The class that the header names reads the fixture, plain or compressed."""
    kind = metrics_class(path)
    with FgumiReader.from_path[kind](path) as reader:
        _ = list(reader)


def test_metrics_class_reads_the_header_of_a_compressed_file(tmp_path: Path) -> None:
    """A compressed file is named by the header inside it, whatever its suffix."""
    path = tmp_path / "anything.bin"
    _ = path.write_bytes(gzip.compress(f"{header(UmiGroupingMetrics)}\n".encode()))
    assert metrics_class(path) is UmiGroupingMetrics


def test_metrics_class_refuses_a_file_with_no_header(tmp_path: Path) -> None:
    """An empty file has no header to name a dataclass by."""
    path = tmp_path / "empty.txt"
    _ = path.write_text("")
    with pytest.raises(ValueError, match="no header row"):
        _ = metrics_class(path)


def test_metrics_class_refuses_a_header_of_no_dataclass(tmp_path: Path) -> None:
    """A header that is no fgumi dataclass's header names nothing."""
    path = tmp_path / "other.txt"
    _ = path.write_text("accepted_sam_records\tsomething_else\n")
    with pytest.raises(ValueError, match="not the header"):
        _ = metrics_class(path)


def test_every_header_names_its_own_dataclass() -> None:
    """Each header names the dataclass whose fields it holds."""
    for columns, kind in HEADERS.items():
        assert columns == tuple(header(kind).split("\t"))


def test_a_header_with_no_rows_reads_as_no_rows() -> None:
    """A header alone, as fgumi writes when it has nothing to count, reads as no rows."""
    assert list(FgumiReader[UmiGroupingMetrics](StringIO(f"{header(UmiGroupingMetrics)}\n"))) == []


def test_the_reader_refuses_a_class_that_is_not_a_fgumi_dataclass() -> None:
    """Only a fgumi dataclass, or a subclass of one, can be read."""
    with pytest.raises(TypeError, match="is not a fgumi dataclass"):
        _ = FgumiReader[NotFgumi](StringIO(""))


def test_the_reader_reads_into_a_subclass() -> None:
    """A subclass of a fgumi dataclass is read, with its own properties."""
    names = [field.name for field in fields(UmiGroupingMetrics)]
    text = "\t".join(names) + "\n" + "\t".join(str(i) for i in range(len(names))) + "\n"
    [row] = FgumiReader[DerivedGrouping](StringIO(text))
    assert row.accepted == names.index("accepted_sam_records")


def test_the_reader_names_a_missing_column() -> None:
    """A file without a column of the dataclass is refused, naming the column."""
    with pytest.raises(ValueError, match="Missing from header"):
        _ = list(FgumiReader[UmiGroupingMetrics](StringIO("accepted_sam_records\n1\n")))


def test_every_dataclass_reads_a_fixture_fgumi_wrote() -> None:
    """Each fgumi dataclass reads a fixture."""
    assert {metrics_class(path) for path in FGUMI_FIXTURES} == set(HEADERS.values())
