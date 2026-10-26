import re
from dataclasses import dataclass
from dataclasses import field
from io import StringIO
from pathlib import Path
from typing import Any

import pytest
from typeline import NamedExtraColumns

from shipslog.picard import ClippedBasesHistogram
from shipslog.picard import DuplicateSetSizeHistogram
from shipslog.picard import DuplicationMetrics
from shipslog.picard import InsertSizeHistogram
from shipslog.picard import InsertSizeMetrics
from shipslog.picard import PairOrientation
from shipslog.picard import PicardHistogramReader
from shipslog.picard import PicardHistogramWriter
from shipslog.picard import PicardReader
from shipslog.picard import PicardWriter
from shipslog.picard import QualityScoreDistribution
from shipslog.picard import QualityYieldMetrics
from shipslog.picard import SamComparisonHistogram
from shipslog.picard import SamComparisonMetric
from shipslog.picard import histogram_class
from shipslog.picard._header import header_lines
from shipslog.picard._histograms import HISTOGRAMS
from tests.compare import same
from tests.picard import FIXTURE_CLASSES
from tests.picard import HEADER
from tests.picard import PICARD_HISTOGRAM_FIXTURES
from tests.picard import PICARD_METRICS_FIXTURES
from tests.picard import DerivedHistogram
from tests.picard import NotHistogram
from tests.picard import class_named_in

QUALITY_YIELD = "picard.analysis.CollectQualityYieldMetrics$QualityYieldMetrics"

METRIC = InsertSizeMetrics(pair_orientation=PairOrientation.FR)

BIN = InsertSizeHistogram(insert_size=1, counts={"All_Reads.fr_count": 3})

BIN_LINES = ["## HISTOGRAM\tjava.lang.Integer", "insert_size\tAll_Reads.fr_count", "1\t3"]

QUALITY = QualityScoreDistribution(quality=30, count_of_q=5, counts={"COUNT_OF_OQ": 2})


@dataclass(frozen=True, kw_only=True)
class Unwritable(InsertSizeHistogram):
    """A subclass of a Picard histogram with a second field of extras, which typeline refuses."""

    more: NamedExtraColumns[int] = field(default_factory=dict)


def quality_bin(quality: int) -> QualityScoreDistribution:
    """A bin of the base quality distribution, at a base quality."""
    return QualityScoreDistribution(
        quality=quality, count_of_q=quality * 2, counts={"COUNT_OF_OQ": 1}
    )


def histogram_alone(*lines: str) -> str:
    """The text of a file of only a histogram, with the test header, or of no bins without lines."""
    return "\n".join([*header_lines(HEADER), "", "", *lines, "", ""])


def metrics_alone(path: Path) -> list[str]:
    """The lines of a file of `METRIC` alone, with the test header, once written to a path."""
    with PicardWriter.from_path[InsertSizeMetrics](path, header=HEADER) as writer:
        writer.write(METRIC)
    return path.read_text().split("\n")


def test_writer_writes_the_histogram_after_the_metrics_as_htsjdk_does(tmp_path: Path) -> None:
    """One blank line ends the metrics, then the histogram line, the labels, the bins, a blank."""
    path = tmp_path / "out.insert_size_metrics"
    with PicardWriter.from_path[InsertSizeMetrics](path, header=HEADER) as writer:
        writer.write(METRIC)
        writer.write_histogram([BIN])
    assert path.read_text().split("\n")[-6:] == [
        "",
        "## HISTOGRAM\tjava.lang.Integer",
        "insert_size\tAll_Reads.fr_count",
        "1\t3",
        "",
        "",
    ]
    alone = metrics_alone(tmp_path / "alone")
    assert path.read_text().split("\n") == [*alone[:-2], *BIN_LINES, "", ""]


def test_writer_refuses_a_histogram_before_any_metrics() -> None:
    """A histogram before any metric row is refused and writes nothing, but no bins are allowed."""
    handle = StringIO()
    writer = PicardWriter[InsertSizeMetrics](handle, header=HEADER)
    before = handle.getvalue()
    writer.write_histogram([])
    with pytest.raises(ValueError, match=r"^Write the metrics before their histogram!$"):
        writer.write_histogram([BIN])
    assert handle.getvalue() == before
    writer.write(METRIC)
    writer.write_histogram([BIN])
    assert handle.getvalue().split("\n")[-4:] == [*BIN_LINES, ""]


def test_histogram_only_writer_writes_the_layout_htsjdk_writes(tmp_path: Path) -> None:
    """The header, two blank lines, the histogram line, the labels, the bins, then a blank."""
    path = tmp_path / "out.quality_distribution_metrics"
    with PicardHistogramWriter.from_path[QualityScoreDistribution](path, header=HEADER) as writer:
        writer.write(QUALITY)
    n = len(header_lines(HEADER))
    assert path.read_text().split("\n")[n : n + 3] == ["", "", "## HISTOGRAM\tjava.lang.Byte"]
    assert path.read_text() == histogram_alone(
        "## HISTOGRAM\tjava.lang.Byte", "QUALITY\tCOUNT_OF_Q\tCOUNT_OF_OQ", "30\t5\t2"
    )


@pytest.mark.parametrize("use_write_all", [False, True], ids=["no-call", "write_all"])
def test_histogram_only_writer_writes_three_blank_lines_for_no_bins(
    tmp_path: Path, use_write_all: bool
) -> None:
    """With no bins, only the header and three blank lines are written, with no label row."""
    path = tmp_path / "out.quality_distribution_metrics"
    with PicardHistogramWriter.from_path[QualityScoreDistribution](path, header=HEADER) as writer:
        if use_write_all:
            writer.write_all([])
    assert path.read_text() == histogram_alone()
    with PicardHistogramReader.from_path[QualityScoreDistribution](path) as reader:
        assert list(reader) == []
    assert reader.header == HEADER


@pytest.mark.parametrize("path", PICARD_HISTOGRAM_FIXTURES, ids=lambda path: path.name)
def test_every_histogram_fixture_reads_back_the_same_after_writing(
    path: Path, tmp_path: Path
) -> None:
    """Every histogram fixture, and its metrics if it has them, reads back the same once written."""
    kind = FIXTURE_CLASSES[path.name]
    with PicardHistogramReader.from_path[kind](path) as reader:
        bins = list(reader)
    out = tmp_path / path.name
    if path in PICARD_METRICS_FIXTURES:
        metrics = class_named_in(path)
        with PicardReader.from_path[metrics](path) as metrics_reader:
            rows = list(metrics_reader)
        with PicardWriter.from_path[metrics](out, header=metrics_reader.header) as writer:
            writer.write_all(rows)
            writer.write_histogram(bins)
        with PicardReader.from_path[metrics](out) as metrics_again:
            assert same(list(metrics_again), rows)
        assert metrics_again.header == metrics_reader.header
    else:
        with PicardHistogramWriter.from_path[kind](out, header=reader.header) as writer:
            writer.write_all(bins)
    with PicardHistogramReader.from_path[kind](out) as again:
        assert same(list(again), bins)
    assert again.header == reader.header


def test_writer_writes_a_histogram_whose_class_has_no_extra_columns(tmp_path: Path) -> None:
    """A histogram without extra columns is labeled with the registered labels alone."""
    path = tmp_path / "out.sam_comparison_metric"
    bins = [
        SamComparisonHistogram(bin="60,0", value=2),
        SamComparisonHistogram(bin="60,60", value=7),
    ]
    with PicardWriter.from_path[SamComparisonMetric](path, header=HEADER) as writer:
        writer.write(SamComparisonMetric(are_equal=True))
        writer.write_histogram(bins)
    lines = path.read_text().split("\n")
    at = lines.index("## HISTOGRAM\tjava.lang.String")
    labels = "\t".join(HISTOGRAMS[SamComparisonHistogram].labels.values())
    assert lines[at + 1 :] == [labels, "60,0\t2", "60,60\t7", "", ""]
    assert labels == "BIN\tVALUE"
    with PicardHistogramReader.from_path[SamComparisonHistogram](path) as reader:
        assert same(list(reader), bins)


def test_writer_writes_optical_sets_after_the_fixed_columns(tmp_path: Path) -> None:
    """An `optical_sets` extra is written last, though Picard writes it mid-row: both read back."""
    path = tmp_path / "out.duplication_metrics"
    bins = [
        DuplicateSetSizeHistogram(
            set_size=1.0, all_sets=4, non_optical_sets=3, counts={"optical_sets": 1}
        )
    ]
    with PicardWriter.from_path[DuplicationMetrics](path, header=HEADER) as writer:
        writer.write(DuplicationMetrics(library="lib"))
        writer.write_histogram(bins)
    lines = path.read_text().split("\n")
    at = lines.index("## HISTOGRAM\tjava.lang.Double")
    assert lines[at + 1] == "set_size\tall_sets\tnon_optical_sets\toptical_sets"
    assert histogram_class(path) is DuplicateSetSizeHistogram
    with PicardHistogramReader.from_path[DuplicateSetSizeHistogram](path) as reader:
        assert same(list(reader), bins)


def test_writer_writes_no_histogram_for_no_bins(tmp_path: Path) -> None:
    """No bins leave the text as if no histogram were given, and a later call still writes one."""
    plain, called, later, once = (tmp_path / name for name in ("plain", "called", "later", "once"))
    with PicardWriter.from_path[InsertSizeMetrics](plain, header=HEADER) as writer:
        writer.write(METRIC)
    with PicardWriter.from_path[InsertSizeMetrics](called, header=HEADER) as writer:
        writer.write(METRIC)
        writer.write_histogram([])
    assert called.read_text() == plain.read_text()
    with PicardWriter.from_path[InsertSizeMetrics](later, header=HEADER) as writer:
        writer.write(METRIC)
        writer.write_histogram(iter([]))
        writer.write_histogram([BIN])
    with PicardWriter.from_path[InsertSizeMetrics](once, header=HEADER) as writer:
        writer.write(METRIC)
        writer.write_histogram([BIN])
    assert later.read_text() == once.read_text()


def test_writer_refuses_a_histogram_of_another_metrics_class() -> None:
    """A histogram the files of the metrics class do not hold is refused, and nothing is written."""
    handle = StringIO()
    writer = PicardWriter[QualityYieldMetrics](handle, header=HEADER)
    writer.write(QualityYieldMetrics(total_reads=1))
    before = handle.getvalue()
    message = f"InsertSizeHistogram is not a histogram of {QUALITY_YIELD} files!"
    with pytest.raises(TypeError, match=f"^{re.escape(message)}$"):
        writer.write_histogram([BIN])
    assert handle.getvalue() == before


def test_writer_refuses_a_row_that_is_not_a_histogram() -> None:
    """A row that is not of a Picard histogram dataclass is refused, and nothing is written."""
    handle = StringIO()
    writer = PicardWriter[InsertSizeMetrics](handle, header=HEADER)
    writer.write(METRIC)
    before = handle.getvalue()
    with pytest.raises(TypeError, match=r"^NotHistogram is not a Picard histogram dataclass!$"):
        writer.write_histogram([NotHistogram(insert_size=1)])
    assert handle.getvalue() == before


def test_writer_refuses_a_histogram_typeline_cannot_write_and_changes_nothing() -> None:
    """A histogram typeline refuses to write leaves the text and the writer as they were."""
    handle, plain = StringIO(), StringIO()
    writer = PicardWriter[InsertSizeMetrics](handle, header=HEADER)
    writer.write(METRIC)
    before = handle.getvalue()
    message = (
        "Unwritable holds the columns no other field takes in more than one field:"
        + " ['counts', 'more']!"
    )
    with pytest.raises(TypeError, match=f"^{re.escape(message)}$"):
        writer.write_histogram([Unwritable(insert_size=1)])
    assert handle.getvalue() == before
    writer.write(METRIC)
    writer.write_histogram([BIN])
    other = PicardWriter[InsertSizeMetrics](plain, header=HEADER)
    other.write_all([METRIC, METRIC])
    other.write_histogram([BIN])
    assert handle.getvalue() == plain.getvalue()


@pytest.mark.parametrize("rows", [[BIN], []], ids=["bins", "no-bins"])
def test_writer_refuses_a_second_histogram(rows: list[InsertSizeHistogram]) -> None:
    """A second histogram is refused, even with no bins, and nothing is written."""
    handle = StringIO()
    writer = PicardWriter[InsertSizeMetrics](handle, header=HEADER)
    writer.write(METRIC)
    writer.write_histogram([BIN])
    before = handle.getvalue()
    with pytest.raises(ValueError, match=r"^The histogram is already written!$"):
        writer.write_histogram(rows)
    assert handle.getvalue() == before


def test_writer_refuses_metrics_after_the_histogram() -> None:
    """Metrics after the histogram are refused and write nothing, while no metrics write nothing."""
    handle = StringIO()
    writer = PicardWriter[InsertSizeMetrics](handle, header=HEADER)
    writer.write_all([METRIC])
    writer.write_histogram([BIN])
    before = handle.getvalue()
    message = r"^Cannot write metrics after the histogram!$"
    with pytest.raises(ValueError, match=message):
        writer.write(METRIC)
    assert handle.getvalue() == before
    with pytest.raises(ValueError, match=message):
        writer.write_all([METRIC])
    assert handle.getvalue() == before
    writer.write_all([])
    assert handle.getvalue() == before


def test_writer_writes_a_users_subclass_of_a_histogram(tmp_path: Path) -> None:
    """A subclass of a Picard histogram is written under its base's key and labels."""
    path = tmp_path / "out.insert_size_metrics"
    bins = [DerivedHistogram(insert_size=1, counts={"All_Reads.fr_count": 3})]
    with PicardWriter.from_path[InsertSizeMetrics](path, header=HEADER) as writer:
        writer.write(METRIC)
        writer.write_histogram(bins)
    alone = metrics_alone(tmp_path / "alone")
    assert path.read_text().split("\n") == [*alone[:-2], *BIN_LINES, "", ""]
    with PicardHistogramReader.from_path[DerivedHistogram](path) as reader:
        again = list(reader)
    assert same(again, bins)
    assert again[0].all_reads == 3


def test_writer_closes_twice_after_a_histogram(tmp_path: Path) -> None:
    """Closing again after a histogram leaves the file as a single close does."""
    once, twice = tmp_path / "once", tmp_path / "twice"
    for path in (once, twice):
        writer = PicardWriter.from_path[InsertSizeMetrics](path, header=HEADER)
        writer.write(METRIC)
        writer.write_histogram([BIN])
        writer.close()
        if path is twice:
            writer.close()
    assert twice.read_text() == once.read_text()
    with PicardHistogramReader.from_path[InsertSizeHistogram](twice) as reader:
        assert same(list(reader), [BIN])


def test_histogram_only_writer_closes_twice(tmp_path: Path) -> None:
    """Closing again leaves the file as a single close does."""
    once, twice = tmp_path / "once", tmp_path / "twice"
    for path in (once, twice):
        writer = PicardHistogramWriter.from_path[QualityScoreDistribution](path, header=HEADER)
        writer.write(QUALITY)
        writer.close()
        if path is twice:
            writer.close()
    assert twice.read_text() == once.read_text()
    with PicardHistogramReader.from_path[QualityScoreDistribution](twice) as reader:
        assert same(list(reader), [QUALITY])


def test_histogram_only_writer_writes_rows_through_write_and_write_all_alike(
    tmp_path: Path,
) -> None:
    """Bins written one at a time and all at once give the same text."""
    bins = [quality_bin(quality) for quality in (10, 20, 30)]
    one, many = tmp_path / "one", tmp_path / "many"
    with PicardHistogramWriter.from_path[QualityScoreDistribution](one, header=HEADER) as writer:
        for row in bins:
            writer.write(row)
    with PicardHistogramWriter.from_path[QualityScoreDistribution](many, header=HEADER) as writer:
        writer.write_all(bins)
    assert one.read_text() == many.read_text()
    with PicardHistogramReader.from_path[QualityScoreDistribution](one) as reader:
        assert same(list(reader), bins)


@pytest.mark.parametrize(
    ("kind", "owners"),
    [
        (InsertSizeHistogram, "picard.analysis.InsertSizeMetrics"),
        (
            DuplicateSetSizeHistogram,
            "picard.sam.DuplicationMetrics or picard.sam.FlowBasedDuplicationMetrics",
        ),
    ],
    ids=["one-owner", "two-owners"],
)
def test_histogram_only_writer_refuses_a_histogram_with_owners(
    tmp_path: Path, kind: type[Any], owners: str
) -> None:
    """A histogram Picard writes after metrics is refused before any file is created."""
    path = tmp_path / "out.txt"
    message = (
        f"{kind.__name__} belongs in {owners} files! Write it with PicardWriter.write_histogram."
    )
    with pytest.raises(TypeError, match=f"^{re.escape(message)}$"):
        _ = PicardHistogramWriter.from_path[kind](path)
    assert not path.exists()


def test_histogram_only_writer_refuses_a_class_that_is_not_a_histogram(tmp_path: Path) -> None:
    """A class that is not a Picard histogram dataclass is refused before any file is created."""
    path = tmp_path / "out.txt"
    with pytest.raises(TypeError, match=r"^NotHistogram is not a Picard histogram dataclass!$"):
        _ = PicardHistogramWriter.from_path[NotHistogram](path)
    assert not path.exists()


def test_histogram_only_writer_write_header_writes_nothing(tmp_path: Path) -> None:
    """The label row is written with the first bin, so `write_header` changes nothing."""
    row = ClippedBasesHistogram(clipped_bases=2, read_count=9)
    plain, called, alone = tmp_path / "plain", tmp_path / "called", tmp_path / "alone"
    with PicardHistogramWriter.from_path[ClippedBasesHistogram](plain, header=HEADER) as writer:
        writer.write(row)
    with PicardHistogramWriter.from_path[ClippedBasesHistogram](called, header=HEADER) as writer:
        writer.write_header()
        writer.write(row)
        writer.write_header()
    assert called.read_text() == plain.read_text()
    with PicardHistogramWriter.from_path[ClippedBasesHistogram](alone, header=HEADER) as writer:
        writer.write_header()
    assert alone.read_text() == histogram_alone()


def test_histogram_only_writer_refuses_write_header_before_the_first_bin_of_named_extras() -> None:
    """The labels of named extra columns come from the first bin, so none are written before it."""
    handle = StringIO()
    writer = PicardHistogramWriter[QualityScoreDistribution](handle, header=HEADER)
    before = handle.getvalue()
    message = (
        "Cannot write the header of QualityScoreDistribution before its first record, which"
        + " names the columns of its NamedExtraColumns field 'counts'!"
    )
    with pytest.raises(ValueError, match=f"^{re.escape(message)}$"):
        writer.write_header()
    assert handle.getvalue() == before


def test_histogram_only_writer_refuses_a_comment() -> None:
    """A comment is refused, and nothing is written."""
    handle = StringIO()
    writer = PicardHistogramWriter[QualityScoreDistribution](handle, header=HEADER)
    before = handle.getvalue()
    message = (
        "A Picard metrics file holds no comments: give its header lines as the writer's header!"
    )
    with pytest.raises(TypeError, match=f"^{re.escape(message)}$"):
        writer.write_comment("x")
    assert handle.getvalue() == before


def test_histogram_only_writer_writes_the_default_header_when_given_none(tmp_path: Path) -> None:
    """Without a header, the command line is `shipslog`, then the start time follows."""
    path = tmp_path / "out.quality_distribution_metrics"
    with PicardHistogramWriter.from_path[QualityScoreDistribution](path):
        pass
    lines = path.read_text().split("\n")
    assert lines[:2] == ["## htsjdk.samtools.metrics.StringHeader", "# shipslog"]
    assert lines[3].startswith("# Started on: ")
