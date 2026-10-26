import re
from dataclasses import fields
from pathlib import Path
from typing import Any

import pytest
from typing_extensions import assert_type

from shipslog.picard import InsertSizeHistogram
from shipslog.picard import InsertSizeHistogramColumns
from shipslog.picard import InsertSizeMetrics
from shipslog.picard import InsertSizeSeries
from shipslog.picard import LibraryComplexityHistogram
from shipslog.picard import LibraryComplexityHistogramColumns
from shipslog.picard import LibraryComplexitySeries
from shipslog.picard import PairOrientation
from shipslog.picard import PicardHistogramReader
from shipslog.picard import RnaCoverageHistogram
from shipslog.picard import RnaCoverageHistogramColumns
from shipslog.picard import RnaCoverageSeries
from shipslog.picard import RnaSeqMetrics
from shipslog.picard import columns
from shipslog.picard import insert_size_bins
from shipslog.picard import insert_size_series
from shipslog.picard import library_complexity_bins
from shipslog.picard import library_complexity_series
from shipslog.picard import rna_coverage_bins
from shipslog.picard import rna_coverage_series
from shipslog.picard._table import MARK
from tests.picard import REPEATED_INSERT_SIZES
from tests.picard import REPEATED_RNA_COVERAGE
from tests.picard import with_histogram

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
    assert all(s.insert_size is hist.insert_size for s in series)


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
    assert all(s.normalized_position is hist.normalized_position for s in series)


def test_library_complexity_series_of_the_fixture() -> None:
    """Each library column becomes a series named by the library."""
    path = "tests/data/picard/elc.duplication_metrics"
    with PicardHistogramReader.from_path[LibraryComplexityHistogram](path) as reader:
        hist = columns(list(reader))
    series = library_complexity_series(hist)
    _ = assert_type(series, list[LibraryComplexitySeries])
    assert [s.library for s in series] == ["Pond-492101", "NormPond-544932"]
    assert [s.counts for s in series] == [hist.counts[s.library] for s in series]
    assert all(s.duplication_group_count is hist.duplication_group_count for s in series)


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
        InsertSizeSeries(
            name=None, orientation=PairOrientation.TANDEM, insert_size=(1, 2), counts=(3, 4)
        ),
        InsertSizeSeries(
            name="S1", orientation=PairOrientation.RF, insert_size=(1, 2), counts=(5, 6)
        ),
        InsertSizeSeries(
            name="S1", orientation=PairOrientation.FR, insert_size=(1, 2), counts=(7, 8)
        ),
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
        normalized_position=(7,), normalized_coverage={"All_Reads.normalized_coverage": (0.5,)}
    )
    assert rna_coverage_series(hist) == [
        RnaCoverageSeries(name=None, normalized_position=(7,), normalized_coverage=(0.5,))
    ]


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
    hist = LibraryComplexityHistogramColumns(
        duplication_group_count=(2, 3), counts={"lib.fr_count": (1, 2)}
    )
    assert library_complexity_series(hist) == [
        LibraryComplexitySeries(
            library="lib.fr_count", duplication_group_count=(2, 3), counts=(1, 2)
        )
    ]


def test_series_are_frozen_and_keyword_only() -> None:
    """The series are built by keyword and cannot change."""
    kinds: list[Any] = [InsertSizeSeries, RnaCoverageSeries, LibraryComplexitySeries]
    for kind in kinds:
        assert kind.__dataclass_params__.frozen, kind
        assert all(f.kw_only is True for f in fields(kind)), kind


def _round_trip(kind: Any, path: str, series_of: Any, bins_of: Any) -> None:
    with PicardHistogramReader.from_path[kind](path) as reader:
        bins = list(reader)
    assert bins_of(series_of(columns(bins))) == bins


def test_insert_size_bins_round_trip_the_fixture() -> None:
    """The bins rebuilt from the series equal the bins read, keys in file order."""
    path = "tests/data/picard/cmm.insert_size_metrics"
    _round_trip(InsertSizeHistogram, path, insert_size_series, insert_size_bins)


def test_rna_coverage_bins_round_trip_the_fixture() -> None:
    """The bins rebuilt from the series equal the bins read, keys in file order."""
    path = "tests/data/picard/rna.rna_metrics"
    _round_trip(RnaCoverageHistogram, path, rna_coverage_series, rna_coverage_bins)


def test_library_complexity_bins_round_trip_the_fixture() -> None:
    """The bins rebuilt from the series equal the bins read, keys in file order."""
    path = "tests/data/picard/elc.duplication_metrics"
    _round_trip(
        LibraryComplexityHistogram, path, library_complexity_series, library_complexity_bins
    )


def test_bins_of_no_series_are_empty() -> None:
    """Without series there are no bins."""
    _ = assert_type(insert_size_bins([]), list[InsertSizeHistogram])
    assert insert_size_bins([]) == []
    _ = assert_type(rna_coverage_bins([]), list[RnaCoverageHistogram])
    assert rna_coverage_bins([]) == []
    _ = assert_type(library_complexity_bins([]), list[LibraryComplexityHistogram])
    assert library_complexity_bins([]) == []


def test_insert_size_bins_name_the_columns() -> None:
    """The column names follow Picard for all reads, dotted names, and every orientation."""
    series = [
        InsertSizeSeries(
            name=None, orientation=PairOrientation.FR, insert_size=(1, 2), counts=(3, 4)
        ),
        InsertSizeSeries(
            name="NA12891.r1", orientation=PairOrientation.FR, insert_size=(1, 2), counts=(5, 6)
        ),
        InsertSizeSeries(
            name="S1", orientation=PairOrientation.RF, insert_size=(1, 2), counts=(7, 8)
        ),
        InsertSizeSeries(
            name=None, orientation=PairOrientation.TANDEM, insert_size=(1, 2), counts=(9, 0)
        ),
    ]
    bins = insert_size_bins(series)
    _ = assert_type(bins, list[InsertSizeHistogram])
    assert bins == [
        InsertSizeHistogram(
            insert_size=1,
            counts={
                "All_Reads.fr_count": 3,
                "NA12891.r1.fr_count": 5,
                "S1.rf_count": 7,
                "All_Reads.tandem_count": 9,
            },
        ),
        InsertSizeHistogram(
            insert_size=2,
            counts={
                "All_Reads.fr_count": 4,
                "NA12891.r1.fr_count": 6,
                "S1.rf_count": 8,
                "All_Reads.tandem_count": 0,
            },
        ),
    ]
    assert list(bins[0].counts) == list(bins[1].counts)


def test_rna_coverage_bins_name_the_columns() -> None:
    """The column names follow Picard, with All_Reads for no name."""
    series = [
        RnaCoverageSeries(name=None, normalized_position=(0, 1), normalized_coverage=(0.5, 0.25)),
        RnaCoverageSeries(name="a.b", normalized_position=(0, 1), normalized_coverage=(1.0, 2.0)),
    ]
    bins = rna_coverage_bins(series)
    _ = assert_type(bins, list[RnaCoverageHistogram])
    assert bins == [
        RnaCoverageHistogram(
            normalized_position=0,
            normalized_coverage={
                "All_Reads.normalized_coverage": 0.5,
                "a.b.normalized_coverage": 1.0,
            },
        ),
        RnaCoverageHistogram(
            normalized_position=1,
            normalized_coverage={
                "All_Reads.normalized_coverage": 0.25,
                "a.b.normalized_coverage": 2.0,
            },
        ),
    ]


def test_library_complexity_bins_name_the_columns_by_library() -> None:
    """The library is the column name."""
    series = [
        LibraryComplexitySeries(library="L1", duplication_group_count=(2, 3), counts=(1, 2)),
        LibraryComplexitySeries(library="L2", duplication_group_count=(2, 3), counts=(3, 4)),
    ]
    bins = library_complexity_bins(series)
    _ = assert_type(bins, list[LibraryComplexityHistogram])
    assert bins == [
        LibraryComplexityHistogram(duplication_group_count=2, counts={"L1": 1, "L2": 3}),
        LibraryComplexityHistogram(duplication_group_count=3, counts={"L1": 2, "L2": 4}),
    ]


def test_bins_refuse_series_with_different_axes() -> None:
    """Every series must share one axis."""
    fr = PairOrientation.FR
    insert = [
        InsertSizeSeries(name=None, orientation=fr, insert_size=(1,), counts=(1,)),
        InsertSizeSeries(name="S", orientation=fr, insert_size=(2,), counts=(1,)),
    ]
    with pytest.raises(ValueError, match="^Every series must hold the same insert sizes!$"):
        _ = insert_size_bins(insert)
    rna = [
        RnaCoverageSeries(name=None, normalized_position=(1,), normalized_coverage=(1.0,)),
        RnaCoverageSeries(name="S", normalized_position=(2,), normalized_coverage=(1.0,)),
    ]
    with pytest.raises(ValueError, match="^Every series must hold the same normalized positions!$"):
        _ = rna_coverage_bins(rna)
    lib = [
        LibraryComplexitySeries(library="A", duplication_group_count=(1,), counts=(1,)),
        LibraryComplexitySeries(library="B", duplication_group_count=(2,), counts=(1,)),
    ]
    message = "^Every series must hold the same duplication group counts!$"
    with pytest.raises(ValueError, match=message):
        _ = library_complexity_bins(lib)


def test_bins_refuse_values_that_do_not_match_the_axis() -> None:
    """A series needs one value per bin."""
    insert = [
        InsertSizeSeries(name="S", orientation=PairOrientation.RF, insert_size=(1, 2), counts=(1,))
    ]
    with pytest.raises(
        ValueError, match=r"^The S\.rf_count series holds 1 values, not one per bin of 2!$"
    ):
        _ = insert_size_bins(insert)
    rna = [RnaCoverageSeries(name=None, normalized_position=(1,), normalized_coverage=(1.0, 2.0))]
    message = r"^The All_Reads\.normalized_coverage series holds 2 values, not one per bin of 1!$"
    with pytest.raises(ValueError, match=message):
        _ = rna_coverage_bins(rna)
    lib = [LibraryComplexitySeries(library="L", duplication_group_count=(1, 2, 3), counts=())]
    with pytest.raises(ValueError, match="^The L series holds 0 values, not one per bin of 3!$"):
        _ = library_complexity_bins(lib)


def test_bins_key_each_repeat_of_a_column_as_a_reader_does() -> None:
    """Series that make one column make it again, the n-th repeat keyed by `MARK` and n."""
    fr = PairOrientation.FR
    insert = [
        InsertSizeSeries(name=None, orientation=fr, insert_size=(1,), counts=(count,))
        for count in (1, 2, 3)
    ]
    column = "All_Reads.fr_count"
    counts = {column: 1, f"{column}{MARK}2": 2, f"{column}{MARK}3": 3}
    assert insert_size_bins(insert) == [InsertSizeHistogram(insert_size=1, counts=counts)]
    rna = [RnaCoverageSeries(name="S", normalized_position=(1,), normalized_coverage=(1.0,))] * 2
    coverage = {"S.normalized_coverage": 1.0, f"S.normalized_coverage{MARK}2": 1.0}
    assert rna_coverage_bins(rna) == [
        RnaCoverageHistogram(normalized_position=1, normalized_coverage=coverage)
    ]


def test_library_complexity_bins_refuse_two_series_of_one_library() -> None:
    """Two series of one library cannot make the same column."""
    lib = [LibraryComplexitySeries(library="L", duplication_group_count=(1,), counts=(1,))] * 2
    with pytest.raises(ValueError, match="^Two series make the column L!$"):
        _ = library_complexity_bins(lib)


def test_insert_size_series_of_a_sample_and_a_library_of_one_name(tmp_path: Path) -> None:
    """A column Picard repeats gives a series of its name for each, in order, which round-trip."""
    metric = InsertSizeMetrics(pair_orientation=PairOrientation.FR)
    path = with_histogram(tmp_path / "s.insert_size_metrics", metric, REPEATED_INSERT_SIZES)
    with PicardHistogramReader.from_path[InsertSizeHistogram](path) as reader:
        bins = list(reader)
    hist = columns(bins)
    assert list(hist.counts) == [
        "All_Reads.fr_count",
        "NA12891.fr_count",
        f"NA12891.fr_count{MARK}2",
        "Pond-2.fr_count",
    ]
    series = insert_size_series(hist)
    assert [s.name for s in series] == [None, "NA12891", "NA12891", "Pond-2"]
    assert all(s.orientation is PairOrientation.FR for s in series)
    assert [s.counts for s in series] == [(5, 7), (5, 7), (3, 4), (2, 3)]
    assert insert_size_bins(series) == bins


def test_rna_coverage_series_of_a_sample_and_a_library_of_one_name(tmp_path: Path) -> None:
    """A column Picard repeats gives a series of its name for each, in order, which round-trip."""
    path = with_histogram(tmp_path / "s.rna_metrics", RnaSeqMetrics(), REPEATED_RNA_COVERAGE)
    with PicardHistogramReader.from_path[RnaCoverageHistogram](path) as reader:
        bins = list(reader)
    hist = columns(bins)
    assert list(hist.normalized_coverage) == [
        "All_Reads.normalized_coverage",
        "NA12891.normalized_coverage",
        f"NA12891.normalized_coverage{MARK}2",
    ]
    series = rna_coverage_series(hist)
    assert [s.name for s in series] == [None, "NA12891", "NA12891"]
    assert [s.normalized_coverage for s in series] == [(0.5, 1.25), (0.5, 1.25), (0.25, 1.5)]
    assert rna_coverage_bins(series) == bins
