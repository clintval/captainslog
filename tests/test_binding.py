import gzip
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any
from typing import assert_type

import pytest
from typeline import RecordType

from captainslog._binding import FromPath
from captainslog.picard import HsMetrics
from captainslog.picard import InsertSizeHistogram
from captainslog.picard import PerBaseCoverage
from captainslog.picard import PerTargetCoverage
from captainslog.picard import PicardCoverageReader
from captainslog.picard import PicardCoverageWriter
from captainslog.picard import PicardHeader
from captainslog.picard import PicardHistogramReader
from captainslog.picard import PicardHistogramWriter
from captainslog.picard import PicardReader
from captainslog.picard import PicardWriter
from captainslog.picard import QualityScoreDistribution
from captainslog.picard import QualityYieldMetrics
from tests.compare import same
from tests.picard import DATA
from tests.picard import HEADER

SHARED = FromPath()


class OwnReader(PicardReader[RecordType]):
    """A user's subclass of the Picard reader."""


class FirstReader(PicardReader[RecordType]):
    """A reader that holds the same `from_path` as another reader."""

    from_path: FromPath = SHARED


class SecondReader(PicardReader[RecordType]):
    """A reader that holds the same `from_path` as another reader."""

    from_path: FromPath = SHARED


class OwnHistogramReader(PicardHistogramReader[RecordType]):
    """A user's subclass of the histogram reader that holds its own `from_path`."""

    from_path: FromPath = FromPath()


class OwnHistogramWriter(PicardHistogramWriter[RecordType]):
    """A user's subclass of the histogram writer that holds its own `from_path`."""

    from_path: FromPath = FromPath()


class OwnCoverageReader(PicardCoverageReader[RecordType]):
    """A user's subclass of the coverage reader that holds its own `from_path`."""

    from_path: FromPath = FromPath()


class Lonely:
    """A class that inherits no `from_path` for its own to hand back."""

    from_path: FromPath = FromPath()


@pytest.fixture
def opened(monkeypatch: pytest.MonkeyPatch) -> list[Any]:
    """Every file opened by its path while the test runs."""
    handles: list[Any] = []
    original: Callable[..., Any] = Path.open

    def recording_open(self: Path, *args: Any, **kwargs: Any) -> Any:
        handle = original(self, *args, **kwargs)
        handles.append(handle)
        return handle

    monkeypatch.setattr(Path, "open", recording_open)
    return handles


def test_from_path_types_the_reader_as_the_subscripted_picard_reader() -> None:
    """Type checkers see `from_path` build the reader it is read through, over its record type."""
    with PicardReader.from_path[QualityYieldMetrics](
        DATA / "cmm.quality_yield_metrics.txt"
    ) as reader:
        _ = assert_type(reader, PicardReader[QualityYieldMetrics])
        _ = assert_type(reader.header, PicardHeader)
        assert type(reader).__name__ == "PicardReader[QualityYieldMetrics]"


def test_from_path_types_the_histogram_reader_as_the_subscripted_histogram_reader() -> None:
    """Type checkers see the histogram reader's `from_path` build it over its record type."""
    path = DATA / "cmm.insert_size_metrics.txt"
    with PicardHistogramReader.from_path[InsertSizeHistogram](path) as reader:
        _ = assert_type(reader, PicardHistogramReader[InsertSizeHistogram])
        _ = assert_type(reader.header, PicardHeader)
        assert type(reader).__name__ == "PicardHistogramReader[InsertSizeHistogram]"


def test_from_path_types_the_writer_as_the_subscripted_picard_writer(tmp_path: Path) -> None:
    """Type checkers see `from_path` build the writer it is read through, over its record type."""
    with PicardWriter.from_path[QualityYieldMetrics](tmp_path / "out.txt", header=HEADER) as writer:
        _ = assert_type(writer, PicardWriter[QualityYieldMetrics])
        assert type(writer).__name__ == "PicardWriter[QualityYieldMetrics]"


def test_from_path_of_the_writer_takes_only_a_header(tmp_path: Path) -> None:
    """The writer's `from_path` refuses an option the Picard format fixes."""
    with pytest.raises(TypeError):
        _ = PicardWriter.from_path[QualityYieldMetrics](tmp_path / "out.txt", quoting=True)  # type: ignore[call-arg]  # pyright: ignore[reportCallIssue, reportUnknownVariableType]  # ty: ignore[unknown-argument]


def test_from_path_types_the_histogram_writer_as_the_subscripted_histogram_writer(
    tmp_path: Path,
) -> None:
    """Type checkers see the histogram writer's `from_path` build it over its record type."""
    path = tmp_path / "out.txt"
    with PicardHistogramWriter.from_path[QualityScoreDistribution](path, header=HEADER) as writer:
        _ = assert_type(writer, PicardHistogramWriter[QualityScoreDistribution])
        assert type(writer).__name__ == "PicardHistogramWriter[QualityScoreDistribution]"


def test_from_path_of_the_histogram_writer_takes_only_a_header(tmp_path: Path) -> None:
    """The histogram writer's `from_path` refuses an option the Picard format fixes."""
    path = tmp_path / "out.txt"
    with pytest.raises(TypeError):
        _ = PicardHistogramWriter.from_path[QualityScoreDistribution](path, quoting=True)  # type: ignore[call-arg]  # pyright: ignore[reportCallIssue, reportUnknownVariableType]  # ty: ignore[unknown-argument]


def test_from_path_types_the_coverage_reader_as_the_subscripted_coverage_reader() -> None:
    """Type checkers see the coverage reader's `from_path` build it over its record type."""
    path = DATA / "hs.per_target_coverage.txt"
    with PicardCoverageReader.from_path[PerTargetCoverage](path) as reader:
        _ = assert_type(reader, PicardCoverageReader[PerTargetCoverage])
        assert type(reader).__name__ == "PicardCoverageReader[PerTargetCoverage]"


def test_from_path_types_the_coverage_writer_as_the_subscripted_coverage_writer(
    tmp_path: Path,
) -> None:
    """Type checkers see the coverage writer's `from_path` build it over its record type."""
    with PicardCoverageWriter.from_path[PerBaseCoverage](tmp_path / "out.txt") as writer:
        _ = assert_type(writer, PicardCoverageWriter[PerBaseCoverage])
        assert type(writer).__name__ == "PicardCoverageWriter[PerBaseCoverage]"


def test_from_path_of_a_subclass_of_the_coverage_reader_builds_the_subclass() -> None:
    """A user's subclass of the coverage reader, with its own `from_path`, builds itself."""
    path = DATA / "hs.per_base_coverage.txt"
    with OwnCoverageReader.from_path[PerBaseCoverage](path) as reader:
        assert isinstance(reader, OwnCoverageReader)
        assert type(reader).__name__ == "OwnCoverageReader[PerBaseCoverage]"
        assert list(reader)


def test_from_path_reads_a_gzipped_file_as_the_plain_file(tmp_path: Path) -> None:
    """A gzipped file reads as the same records and header as the plain file."""
    plain = DATA / "hs.hs_metrics.txt"
    gzipped = tmp_path / "hs.hs_metrics.txt.gz"
    _ = gzipped.write_bytes(gzip.compress(plain.read_bytes()))
    with (
        PicardReader.from_path[HsMetrics](gzipped) as gzipped_reader,
        PicardReader.from_path[HsMetrics](plain) as plain_reader,
    ):
        gzipped_rows, plain_rows = list(gzipped_reader), list(plain_reader)
        assert gzipped_rows
        assert same(gzipped_rows, plain_rows)
        assert gzipped_reader.header == plain_reader.header


def test_from_path_closes_the_file_once_read_to_the_end(opened: list[Any]) -> None:
    """A reader from `from_path` closes its file once every record is read."""
    assert list(PicardReader.from_path[QualityYieldMetrics](DATA / "cmm.quality_yield_metrics.txt"))
    assert opened
    assert all(handle.closed for handle in opened)


def test_from_path_closes_the_file_when_the_reader_refuses_it(opened: list[Any]) -> None:
    """A file of another class is closed before its refusal is raised."""
    with pytest.raises(ValueError, match=r"holds picard\.analysis\.InsertSizeMetrics"):
        _ = PicardReader.from_path[HsMetrics](DATA / "cmm.insert_size_metrics.txt")
    assert opened
    assert all(handle.closed for handle in opened)


def test_from_path_on_a_subclass_of_the_reader_builds_the_subclass() -> None:
    """A user's subclass of the reader builds itself from a path."""
    with OwnReader.from_path[QualityYieldMetrics](DATA / "cmm.quality_yield_metrics.txt") as reader:
        assert isinstance(reader, OwnReader)
        assert type(reader).__name__ == "OwnReader[QualityYieldMetrics]"
        assert list(reader)


def test_from_path_of_a_subclass_of_the_histogram_reader_builds_the_subclass() -> None:
    """A user's subclass of the histogram reader, with its own `from_path`, builds itself."""
    path = DATA / "cmm.insert_size_metrics.txt"
    with OwnHistogramReader.from_path[InsertSizeHistogram](path) as reader:
        assert isinstance(reader, OwnHistogramReader)
        assert type(reader).__name__ == "OwnHistogramReader[InsertSizeHistogram]"
        assert list(reader)


def test_from_path_of_a_subclass_of_the_histogram_writer_builds_the_subclass(
    tmp_path: Path,
) -> None:
    """A user's subclass of the histogram writer, with its own `from_path`, builds itself."""
    path = tmp_path / "out.quality_distribution_metrics"
    row = QualityScoreDistribution(quality=30, count_of_q=5)
    with OwnHistogramWriter.from_path[QualityScoreDistribution](path, header=HEADER) as writer:
        assert isinstance(writer, OwnHistogramWriter)
        assert type(writer).__name__ == "OwnHistogramWriter[QualityScoreDistribution]"
        writer.write(row)
    with PicardHistogramReader.from_path[QualityScoreDistribution](path) as reader:
        assert list(reader) == [row]


def test_from_path_held_by_two_classes_builds_each() -> None:
    """One `from_path` held by two classes builds whichever class it is read through."""
    path = DATA / "cmm.quality_yield_metrics.txt"
    for kind in (FirstReader, SecondReader):
        with kind.from_path[QualityYieldMetrics](path) as reader:
            assert type(reader).__name__ == f"{kind.__name__}[QualityYieldMetrics]"
            assert list(reader)


def test_from_path_without_an_inherited_from_path_is_refused() -> None:
    """A class that inherits no `from_path` cannot hand one back."""
    message = "Lonely inherits no from_path for FromPath to hand back!"
    with pytest.raises(TypeError, match=f"^{re.escape(message)}$"):
        _ = Lonely.from_path
