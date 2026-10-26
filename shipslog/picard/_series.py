from dataclasses import dataclass

from shipslog.picard._histograms import InsertSizeHistogramColumns
from shipslog.picard._histograms import LibraryComplexityHistogramColumns
from shipslog.picard._histograms import RnaCoverageHistogramColumns
from shipslog.picard._metrics import PairOrientation

ALL_READS = "All_Reads"


@dataclass(frozen=True, kw_only=True)
class InsertSizeSeries:
    """The counts of one insert size histogram column, with the level and orientation it names."""

    name: str | None
    """The sample, library or read group of the column, or `None` for all reads."""

    orientation: PairOrientation
    """The pair orientation of the reads counted."""

    counts: tuple[int, ...]
    """One count per bin of the histogram's `insert_size`."""


@dataclass(frozen=True, kw_only=True)
class RnaCoverageSeries:
    """The normalized coverage of one RNA coverage histogram column, with the level it names."""

    name: str | None
    """The sample, library or read group of the column, or `None` for all reads."""

    normalized_coverage: tuple[float, ...]
    """One normalized coverage per bin of the histogram's `normalized_position`."""


@dataclass(frozen=True, kw_only=True)
class LibraryComplexitySeries:
    """The counts of one library column of a library complexity histogram."""

    library: str
    """The library of the column."""

    counts: tuple[int, ...]
    """One count of duplicate groups per bin of the histogram's `duplication_group_count`."""


def _strip_suffix(column: str, suffixes: tuple[str, ...]) -> tuple[str | None, str] | None:
    """Return the name and the matched suffix of a column, or `None` if no suffix matches."""
    for suffix in suffixes:
        if column.endswith(suffix):
            prefix = column.removesuffix(suffix)
            return (None if prefix == ALL_READS else prefix), suffix
    return None


def insert_size_series(hist: InsertSizeHistogramColumns, /) -> list[InsertSizeSeries]:
    """Give one series for each column of an insert size histogram, in the order of the file.

    Args:
        hist: the columns of an insert size histogram, as `columns` returns them.

    Raises:
        ValueError: if a column is not named as Picard names an insert size column.
    """
    suffixes = tuple(f".{orientation.lower()}_count" for orientation in PairOrientation)
    series: list[InsertSizeSeries] = []
    for column, counts in hist.counts.items():
        parsed = _strip_suffix(column, suffixes)
        if parsed is None:
            raise ValueError(
                f"{column!r} is not a column name Picard writes for an insert size histogram!"
            )
        name, suffix = parsed
        orientation = PairOrientation(suffix[1:].removesuffix("_count").upper())
        series.append(InsertSizeSeries(name=name, orientation=orientation, counts=counts))
    return series


def rna_coverage_series(hist: RnaCoverageHistogramColumns, /) -> list[RnaCoverageSeries]:
    """Give one series for each column of an RNA coverage histogram, in the order of the file.

    Args:
        hist: the columns of an RNA coverage histogram, as `columns` returns them.

    Raises:
        ValueError: if a column is not named as Picard names an RNA coverage column.
    """
    series: list[RnaCoverageSeries] = []
    for column, coverage in hist.normalized_coverage.items():
        parsed = _strip_suffix(column, (".normalized_coverage",))
        if parsed is None:
            raise ValueError(
                f"{column!r} is not a column name Picard writes for an RNA coverage histogram!"
            )
        series.append(RnaCoverageSeries(name=parsed[0], normalized_coverage=coverage))
    return series


def library_complexity_series(
    hist: LibraryComplexityHistogramColumns, /
) -> list[LibraryComplexitySeries]:
    """Give one series for each library column of a library complexity histogram.

    Args:
        hist: the columns of a library complexity histogram, as `columns` returns them.
    """
    return [
        LibraryComplexitySeries(library=library, counts=counts)
        for library, counts in hist.counts.items()
    ]
