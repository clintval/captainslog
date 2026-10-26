import re
from dataclasses import astuple
from dataclasses import dataclass
from dataclasses import fields
from io import StringIO
from pathlib import Path
from typing import assert_type

import pytest

from shipslog.riker import AlignmentMetrics
from shipslog.riker import HybcapMetrics
from shipslog.riker import RikerReader
from shipslog.riker import RikerWriter
from shipslog.riker import RnaBiotype
from shipslog.riker import metrics_class
from tests.compare import same
from tests.riker import RIKER_FIXTURES


@dataclass(frozen=True)
class NotRiker:
    """A dataclass that is not a Riker dataclass."""

    sample: str


@pytest.mark.parametrize("path", RIKER_FIXTURES, ids=lambda path: path.name)
def test_every_fixture_reads_back_the_same_after_writing(path: Path, tmp_path: Path) -> None:
    """Each fixture's records read back as they were after a write."""
    kind = metrics_class(path)
    with RikerReader.from_path[kind](path) as reader:
        rows = list(reader)
    out = tmp_path / path.name
    with RikerWriter.from_path[kind](out) as writer:
        writer.write_all(rows)
    with RikerReader.from_path[kind](out) as reader:
        assert same(list(reader), rows)


@pytest.mark.parametrize("how", ["close", "write_all", "write_header"])
def test_writer_without_records_leaves_the_file_empty(how: str, tmp_path: Path) -> None:
    """Closing with no record writes not even the header, as Riker writes."""
    path = tmp_path / "s.alignment-metrics.txt"
    with RikerWriter.from_path[AlignmentMetrics](path) as writer:
        if how == "write_all":
            writer.write_all([])
        elif how == "write_header":
            writer.write_header()
    assert path.read_text() == ""


def test_writer_writes_what_riker_writes_for_quoted_and_empty_cells() -> None:
    """Cells with a tab, quote or line break are quoted, a missing optional is empty."""
    rows = [
        HybcapMetrics(sample="a\tb", hs_library_size=None),
        HybcapMetrics(sample='a"b', hs_library_size=7),
        HybcapMetrics(sample="a\nb"),
        HybcapMetrics(sample="a\rb"),
    ]
    handle = StringIO(newline="")
    with RikerWriter[HybcapMetrics](handle) as writer:
        writer.write_all(rows)
        text = handle.getvalue()
    header = "\t".join(f.name for f in fields(HybcapMetrics))
    quoted = ['"a\tb"', '"a""b"', '"a\nb"', '"a\rb"']
    lines = [
        "\t".join([cell, *("" if v is None else str(v) for v in astuple(row)[1:])])
        for cell, row in zip(quoted, rows, strict=True)
    ]
    expected = "\n".join([header, *lines]) + "\n"
    assert text == expected
    with RikerReader[HybcapMetrics](StringIO(text)) as reader:
        assert same(list(reader), rows)


def test_writer_writes_a_sample_that_starts_with_a_hash_bare() -> None:
    """A sample named `#x` is not quoted or treated as a comment."""
    handle = StringIO(newline="")
    with RikerWriter[RnaBiotype](handle) as writer:
        writer.write(RnaBiotype(sample="#x", biotype="mRNA", reads=3, frac_reads=0.5))
        text = handle.getvalue()
    assert text.splitlines() == ["sample\tbiotype\treads\tfrac_reads", "#x\tmRNA\t3\t0.5"]


def test_writer_refuses_a_comment() -> None:
    """A Riker file holds no comments."""
    message = "A Riker metrics file holds no comments!"
    with (
        RikerWriter[RnaBiotype](StringIO()) as writer,
        pytest.raises(TypeError, match=f"^{re.escape(message)}$"),
    ):
        writer.write_comment("note")


def test_writer_refuses_a_class_that_is_not_a_riker_dataclass(tmp_path: Path) -> None:
    """A record type that is no Riker dataclass is refused before anything is written."""
    message = "NotRiker is not a Riker dataclass!"
    handle = StringIO()
    with pytest.raises(TypeError, match=f"^{re.escape(message)}$"):
        _ = RikerWriter[NotRiker](handle)
    assert handle.getvalue() == ""
    path = tmp_path / "out.txt"
    with pytest.raises(TypeError, match=f"^{re.escape(message)}$"):
        _ = RikerWriter.from_path[NotRiker](path)
    assert not path.exists()


def test_writer_writes_the_header_once() -> None:
    """Writing the header by hand does not repeat it with the first record."""
    handle = StringIO(newline="")
    with RikerWriter[RnaBiotype](handle) as writer:
        writer.write_header()
        writer.write(RnaBiotype(sample="s"))
        text = handle.getvalue()
    assert text.count("sample\tbiotype") == 1


def test_from_path_types_the_riker_writer(tmp_path: Path) -> None:
    """Type checkers see `from_path` build the writer over its record type."""
    with RikerWriter.from_path[RnaBiotype](tmp_path / "out.txt") as writer:
        _ = assert_type(writer, RikerWriter[RnaBiotype])
        assert type(writer).__name__ == "RikerWriter[RnaBiotype]"


def test_from_path_of_the_writer_refuses_an_unknown_option(tmp_path: Path) -> None:
    """The writer's `from_path` refuses an option typeline does not have."""
    with pytest.raises(TypeError):
        _ = RikerWriter.from_path[RnaBiotype](tmp_path / "out.txt", bogus=True)  # type: ignore[call-arg]  # pyright: ignore[reportCallIssue, reportUnknownVariableType]  # ty: ignore[unknown-argument]


@pytest.mark.parametrize("count", [1, 3])
def test_writer_without_a_header_writes_every_record(count: int) -> None:
    """With `header=False`, the first record is written, and no header line."""
    handle = StringIO(newline="")
    rows = [
        RnaBiotype(sample=f"s{i}", biotype="mRNA", reads=i, frac_reads=0.5) for i in range(count)
    ]
    with RikerWriter[RnaBiotype](handle, header=False) as writer:
        writer.write_all(rows)
        text = handle.getvalue()
    assert text.splitlines() == [f"s{i}\tmRNA\t{i}\t0.5" for i in range(count)]
