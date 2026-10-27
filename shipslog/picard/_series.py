from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from shipslog.picard._histograms import InsertSizeHistogram
from shipslog.picard._histograms import InsertSizeHistogramColumns
from shipslog.picard._histograms import LibraryComplexityHistogram
from shipslog.picard._histograms import LibraryComplexityHistogramColumns
from shipslog.picard._histograms import RnaCoverageHistogram
from shipslog.picard._histograms import RnaCoverageHistogramColumns
from shipslog.picard._metrics import PairOrientation
from shipslog.picard._table import mark_repeats
from shipslog.picard._table import unmark

ALL_READS = "All_Reads"


@dataclass(frozen=True, kw_only=True)
class InsertSizeSeries:
    """The counts of one insert size histogram column, with the level and orientation it names."""

    name: str | None
    """The sample, library or read group of the column, or `None` for all reads."""

    orientation: PairOrientation
    """The pair orientation of the reads counted."""

    insert_size: tuple[int, ...]
    """The insert size of each bin, shared with the histogram's `insert_size`."""

    counts: tuple[int, ...]
    """One count per bin of the histogram's `insert_size`."""


@dataclass(frozen=True, kw_only=True)
class RnaCoverageSeries:
    """The normalized coverage of one RNA coverage histogram column, with the level it names."""

    name: str | None
    """The sample, library or read group of the column, or `None` for all reads."""

    normalized_position: tuple[int, ...]
    """The 0-based percent of each bin, shared with the histogram's `normalized_position`."""

    normalized_coverage: tuple[float, ...]
    """One normalized coverage per bin of the histogram's `normalized_position`."""


@dataclass(frozen=True, kw_only=True)
class LibraryComplexitySeries:
    """The counts of one library column of a library complexity histogram."""

    library: str
    """The library of the column."""

    duplication_group_count: tuple[int, ...]
    """The group size of each bin, shared with the histogram's `duplication_group_count`."""

    counts: tuple[int, ...]
    """One count of duplicate groups per bin of the histogram's `duplication_group_count`."""


def _strip_suffix(column: str, suffixes: tuple[str, ...]) -> tuple[str | None, str] | None:
    """Return the name and the matched suffix of a column, or `None` if no suffix matches.

    A repeat of a column Picard wrote twice is read as the column, without its key.
    """
    label = unmark(column)
    for suffix in suffixes:
        if label.endswith(suffix):
            prefix = label.removesuffix(suffix)
            return (None if prefix == ALL_READS else prefix), suffix
    return None


def _columns(names: Sequence[tuple[str | None, str]]) -> list[str]:
    """Return the column Picard writes for each name and suffix, keying repeats as a reader does."""
    return mark_repeats([
        f"{ALL_READS if name is None else name}{suffix}" for name, suffix in names
    ])


def _rows(
    axes: list[tuple[int, ...]], named: list[tuple[str, tuple[Any, ...]]], axis_message: str
) -> list[tuple[int, dict[str, Any]]]:
    """Give each bin of the shared axis with one value per named column, in the order given."""
    if not axes:
        return []
    if any(axis != axes[0] for axis in axes):
        raise ValueError(axis_message)
    columns: dict[str, tuple[Any, ...]] = {}
    for column, values in named:
        if len(values) != len(axes[0]):
            count, bins = len(values), len(axes[0])
            raise ValueError(
                f"The {column} series holds {count} values, not one per bin of {bins}!"
            )
        if column in columns:
            raise ValueError(f"Two series make the column {column}!")
        columns[column] = values
    rows = zip(axes[0], *columns.values(), strict=True)
    return [(bin_, dict(zip(columns, row, strict=True))) for bin_, *row in rows]


def insert_size_series(hist: InsertSizeHistogramColumns, /) -> list[InsertSizeSeries]:
    """Give one series for each column of an insert size histogram, in the order of the file.

    A sample and a library of one name give two series of that name and orientation, in the order
    of the file. Picard writes all reads, then the samples, the libraries, and the read groups, so
    the earlier is the sample's.

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
        series.append(
            InsertSizeSeries(
                name=name, orientation=orientation, insert_size=hist.insert_size, counts=counts
            )
        )
    return series


def rna_coverage_series(hist: RnaCoverageHistogramColumns, /) -> list[RnaCoverageSeries]:
    """Give one series for each column of an RNA coverage histogram, in the order of the file.

    A sample and a library of one name give two series of that name, in the order of the file.
    Picard writes all reads, then the samples, the libraries, and the read groups, so the earlier
    is the sample's.

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
        series.append(
            RnaCoverageSeries(
                name=parsed[0],
                normalized_position=hist.normalized_position,
                normalized_coverage=coverage,
            )
        )
    return series


def library_complexity_series(
    hist: LibraryComplexityHistogramColumns, /
) -> list[LibraryComplexitySeries]:
    """Give one series for each library column of a library complexity histogram.

    Args:
        hist: the columns of a library complexity histogram, as `columns` returns them.
    """
    return [
        LibraryComplexitySeries(
            library=library, duplication_group_count=hist.duplication_group_count, counts=counts
        )
        for library, counts in hist.counts.items()
    ]


def insert_size_bins(series: Sequence[InsertSizeSeries], /) -> list[InsertSizeHistogram]:
    """Build the bins of an insert size histogram from its series, one bin per insert size.

    Two series of one name and orientation make one column twice, as Picard writes for a sample and
    a library of one name, and the second is keyed as a reader keys it: the column, the unit
    separator U+001F, and 2. A third is keyed with 3, and so on.

    Args:
        series: the series to write, one column each, named as Picard names the column.

    Raises:
        ValueError: if the series differ in insert sizes, or hold other than one value per bin.
    """
    columns = _columns([(s.name, f".{s.orientation.lower()}_count") for s in series])
    rows = _rows(
        [s.insert_size for s in series],
        list(zip(columns, [s.counts for s in series], strict=True)),
        "Every series must hold the same insert sizes!",
    )
    return [InsertSizeHistogram(insert_size=size, counts=counts) for size, counts in rows]


def rna_coverage_bins(series: Sequence[RnaCoverageSeries], /) -> list[RnaCoverageHistogram]:
    """Build the bins of an RNA coverage histogram from its series, one bin per position.

    Two series of one name make one column twice, as Picard writes for a sample and a library of
    one name, and the second is keyed as a reader keys it: the column, the unit separator U+001F,
    and 2. A third is keyed with 3, and so on.

    Args:
        series: the series to write, one column each, named as Picard names the column.

    Raises:
        ValueError: if the series differ in positions, or hold other than one value per bin.
    """
    columns = _columns([(s.name, ".normalized_coverage") for s in series])
    rows = _rows(
        [s.normalized_position for s in series],
        list(zip(columns, [s.normalized_coverage for s in series], strict=True)),
        "Every series must hold the same normalized positions!",
    )
    return [
        RnaCoverageHistogram(normalized_position=position, normalized_coverage=coverage)
        for position, coverage in rows
    ]


def library_complexity_bins(
    series: Sequence[LibraryComplexitySeries], /
) -> list[LibraryComplexityHistogram]:
    """Build the bins of a library complexity histogram from its series, one bin per group size.

    Args:
        series: the series to write, one library column each.

    Raises:
        ValueError: if the series differ in group sizes, hold a count other than one per bin,
            or make the same column.
    """
    rows = _rows(
        [s.duplication_group_count for s in series],
        [(s.library, s.counts) for s in series],
        "Every series must hold the same duplication group counts!",
    )
    return [
        LibraryComplexityHistogram(duplication_group_count=count, counts=counts)
        for count, counts in rows
    ]
