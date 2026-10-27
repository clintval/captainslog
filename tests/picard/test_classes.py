import gzip
import re
from pathlib import Path
from typing import TextIO

import pytest
from typeline import open_for_reading

from captainslog.picard import PicardReader
from captainslog.picard import QualityYieldMetrics
from captainslog.picard import _reader as reader
from captainslog.picard import metrics_class
from tests.picard import DATA
from tests.picard import LINES
from tests.picard import PICARD_METRICS_FIXTURES
from tests.picard import class_named_in


@pytest.mark.parametrize("path", PICARD_METRICS_FIXTURES, ids=lambda path: path.name)
def test_metrics_class_names_the_dataclass_of_every_fixture(path: Path) -> None:
    """Every fixture file gives the dataclass that its `## METRICS CLASS` line names."""
    assert metrics_class(path) is class_named_in(path)


def test_metrics_class_and_the_reader_read_a_gzipped_file(tmp_path: Path) -> None:
    """A gzipped file gives the same metrics class and the same rows as its plain file."""
    source = DATA / "cmm.quality_yield_metrics"
    path = tmp_path / "zipped.quality_yield_metrics.gz"
    _ = path.write_bytes(gzip.compress(source.read_bytes()))
    assert metrics_class(path) is QualityYieldMetrics
    plain = list(PicardReader.from_path[QualityYieldMetrics](source))
    assert list(PicardReader.from_path[QualityYieldMetrics](path)) == plain


def test_metrics_class_accepts_a_path_given_as_text() -> None:
    """A path given as text gives the same metrics class as a `Path`."""
    assert metrics_class(str(DATA / "cmm.quality_yield_metrics")) is QualityYieldMetrics


def test_metrics_class_points_a_histogram_only_file_to_histogram_class() -> None:
    """A file holding only a histogram is refused, pointing to `histogram_class`."""
    path = DATA / "cmm.quality_by_cycle_metrics"
    message = (
        rf"^{re.escape(str(path))} holds no metrics table! "
        r"If it holds only a histogram, find its type with histogram_class\.$"
    )
    with pytest.raises(ValueError, match=message):
        _ = metrics_class(path)


def test_metrics_class_points_a_file_of_a_header_alone_to_histogram_class(tmp_path: Path) -> None:
    """A file of only a header and its blank lines is refused, pointing to `histogram_class`."""
    path = tmp_path / "header.metrics"
    _ = path.write_text("\n".join([*LINES, "", "", "", ""]))
    message = (
        rf"^{re.escape(str(path))} holds no metrics table! "
        r"If it holds only a histogram, find its type with histogram_class\.$"
    )
    with pytest.raises(ValueError, match=message):
        _ = metrics_class(path)


@pytest.mark.parametrize("end", ["", "\n"], ids=repr)
def test_metrics_class_refuses_a_file_that_ends_after_its_header(tmp_path: Path, end: str) -> None:
    """A header without the blank line htsjdk writes after it may be cut short."""
    path = tmp_path / "cut.metrics"
    _ = path.write_text("\n".join(LINES) + end)
    message = f"{path} ends after its header, so it may be cut short!"
    with pytest.raises(ValueError, match=f"^{re.escape(message)}$"):
        _ = metrics_class(path)


def test_metrics_class_refuses_a_class_it_does_not_know(tmp_path: Path) -> None:
    """A `## METRICS CLASS` line naming a class with no dataclass is refused, naming the class."""
    path = tmp_path / "other.metrics"
    _ = path.write_text("\n".join(LINES) + "\n\n## METRICS CLASS\tpicard.analysis.Nonesuch\nA\n1\n")
    message = (
        rf"^{re.escape(str(path))} holds picard\.analysis\.Nonesuch, "
        r"which is not a Picard 3\.5\.0 metrics class!$"
    )
    with pytest.raises(ValueError, match=message):
        _ = metrics_class(path)


def test_metrics_class_refuses_a_file_that_is_not_a_picard_metrics_file() -> None:
    """A file that is not a Picard metrics file is refused, naming the file."""
    path = DATA / "hs.per_target_coverage.txt"
    with pytest.raises(
        ValueError, match=rf"^{re.escape(str(path))} is not a Picard metrics file!$"
    ):
        _ = metrics_class(path)


@pytest.mark.parametrize("text", ["", "\n\n  \n"], ids=["empty", "blank"])
def test_metrics_class_refuses_an_empty_or_blank_file(tmp_path: Path, text: str) -> None:
    """An empty file, or one of only blank lines, is refused as not a Picard metrics file."""
    path = tmp_path / "empty.metrics"
    _ = path.write_text(text)
    with pytest.raises(
        ValueError, match=rf"^{re.escape(str(path))} is not a Picard metrics file!$"
    ):
        _ = metrics_class(path)


def test_metrics_class_refuses_a_file_whose_lines_end_with_a_lone_carriage_return(
    tmp_path: Path,
) -> None:
    """A file whose lines end with a lone carriage return is refused by both."""
    path = tmp_path / "mac.metrics"
    _ = path.write_text(
        (DATA / "cmm.quality_yield_metrics").read_text().replace("\n", "\r"), newline=""
    )
    message = (
        rf"^{re.escape(str(path))} breaks its lines with lone carriage returns, not line feeds!$"
    )
    with pytest.raises(ValueError, match=message):
        _ = metrics_class(path)
    with pytest.raises(ValueError, match=message):
        _ = PicardReader.from_path[QualityYieldMetrics](path)


def test_metrics_class_closes_the_file_when_it_refuses_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The file is closed when it is refused."""
    path = tmp_path / "empty.metrics"
    _ = path.write_text("")
    opened: list[TextIO] = []

    def spy(where: Path | str) -> TextIO:
        opened.append(open_for_reading(where))
        return opened[-1]

    monkeypatch.setattr(reader, "open_for_reading", spy)
    with pytest.raises(ValueError, match="is not a Picard metrics file!"):
        _ = metrics_class(path)
    assert [handle.closed for handle in opened] == [True]
