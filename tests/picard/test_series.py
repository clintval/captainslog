import re
from dataclasses import fields
from typing import Any

import pytest
from typing_extensions import assert_type

from shipslog.picard import InsertSizeHistogram
from shipslog.picard import InsertSizeHistogramColumns
from shipslog.picard import InsertSizeSeries
from shipslog.picard import LibraryComplexityHistogram
from shipslog.picard import LibraryComplexityHistogramColumns
from shipslog.picard import LibraryComplexitySeries
from shipslog.picard import PairOrientation
from shipslog.picard import PicardHistogramReader
from shipslog.picard import RnaCoverageHistogram
from shipslog.picard import RnaCoverageHistogramColumns
from shipslog.picard import RnaCoverageSeries
from shipslog.picard import columns
from shipslog.picard import insert_size_series
from shipslog.picard import library_complexity_series
from shipslog.picard import rna_coverage_series

NAMES = [None, "NA12891", "Pond-492101", "NormPond-544932", "NA12891.r1", "NA12891.r2"]
PREFIXES = ["All_Reads", *[name for name in NAMES if name]]


def test_insert_size_series_of_the_fixture() -> None:
    """Each column of the insert size histogram becomes a series in file order."""
    path = "tests/data/picard/cmm.insert_size_metrics"
    with PicardHistogramReader.from_path[InsertSizeHistogram](path) as reader:
        hist = columns(list(reader))
    series = insert_size_series(hist)
    _ = assert_type(series, list[InsertSizeSeries])
    assert [s.name for s in series] == NAMES
    assert all(s.orientation is PairOrientation.FR for s in series)
    assert [s.counts for s in series] == [hist.counts[f"{p}.fr_count"] for p in PREFIXES]


def test_rna_coverage_series_of_the_fixture() -> None:
    """Each column of the RNA coverage histogram becomes a series in file order."""
    path = "tests/data/picard/rna.rna_metrics"
    with PicardHistogramReader.from_path[RnaCoverageHistogram](path) as reader:
        hist = columns(list(reader))
    series = rna_coverage_series(hist)
    _ = assert_type(series, list[RnaCoverageSeries])
    assert [s.name for s in series] == NAMES
    expected = [hist.normalized_coverage[f"{p}.normalized_coverage"] for p in PREFIXES]
    assert [s.normalized_coverage for s in series] == expected


def test_library_complexity_series_of_the_fixture() -> None:
    """Each library column becomes a series named by the library."""
    path = "tests/data/picard/elc.duplication_metrics"
    with PicardHistogramReader.from_path[LibraryComplexityHistogram](path) as reader:
        hist = columns(list(reader))
    series = library_complexity_series(hist)
    _ = assert_type(series, list[LibraryComplexitySeries])
    assert [s.library for s in series] == ["Pond-492101", "NormPond-544932"]
    assert [s.counts for s in series] == [hist.counts[s.library] for s in series]


def test_insert_size_series_reads_every_orientation() -> None:
    """The suffix gives the orientation, including for all reads."""
    hist = InsertSizeHistogramColumns(
        insert_size=(1, 2),
        counts={
            "All_Reads.tandem_count": (3, 4),
            "S1.rf_count": (5, 6),
            "S1.fr_count": (7, 8),
        },
    )
    assert insert_size_series(hist) == [
        InsertSizeSeries(name=None, orientation=PairOrientation.TANDEM, counts=(3, 4)),
        InsertSizeSeries(name="S1", orientation=PairOrientation.RF, counts=(5, 6)),
        InsertSizeSeries(name="S1", orientation=PairOrientation.FR, counts=(7, 8)),
    ]


def test_series_names_keep_their_dots_and_suffix_like_words() -> None:
    """Only the final known suffix is stripped from a name."""
    hist = InsertSizeHistogramColumns(counts={"a.b.c.fr_count": (1,), "my.count.fr_count": (2,)})
    assert [s.name for s in insert_size_series(hist)] == ["a.b.c", "my.count"]
    rna = RnaCoverageHistogramColumns(
        normalized_coverage={
            "x.y.normalized_coverage": (1.0,),
            "my.count.normalized_coverage": (2.0,),
        }
    )
    assert [s.name for s in rna_coverage_series(rna)] == ["x.y", "my.count"]


def test_rna_coverage_series_of_all_reads_has_no_name() -> None:
    """The all-reads prefix gives a series with no name."""
    hist = RnaCoverageHistogramColumns(
        normalized_coverage={"All_Reads.normalized_coverage": (0.5,)}
    )
    assert rna_coverage_series(hist) == [RnaCoverageSeries(name=None, normalized_coverage=(0.5,))]


def test_insert_size_series_refuses_an_unknown_column() -> None:
    """A column that Picard does not write for the histogram is refused."""
    hist = InsertSizeHistogramColumns(counts={"S1.count": (1,)})
    message = "'S1.count' is not a column name Picard writes for an insert size histogram!"
    with pytest.raises(ValueError, match=f"^{re.escape(message)}$"):
        _ = insert_size_series(hist)


def test_rna_coverage_series_refuses_an_unknown_column() -> None:
    """A column that Picard does not write for the histogram is refused."""
    hist = RnaCoverageHistogramColumns(normalized_coverage={"S1.fr_count": (1.0,)})
    message = "'S1.fr_count' is not a column name Picard writes for an RNA coverage histogram!"
    with pytest.raises(ValueError, match=f"^{re.escape(message)}$"):
        _ = rna_coverage_series(hist)


def test_library_complexity_series_names_the_library_by_the_column() -> None:
    """A library column needs no parsing."""
    hist = LibraryComplexityHistogramColumns(counts={"lib.fr_count": (1, 2)})
    assert library_complexity_series(hist) == [
        LibraryComplexitySeries(library="lib.fr_count", counts=(1, 2))
    ]


def test_series_are_frozen_and_keyword_only() -> None:
    """The series are built by keyword and cannot change."""
    kinds: list[Any] = [InsertSizeSeries, RnaCoverageSeries, LibraryComplexitySeries]
    for kind in kinds:
        assert kind.__dataclass_params__.frozen, kind
        assert all(f.kw_only is True for f in fields(kind)), kind
