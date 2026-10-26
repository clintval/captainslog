from collections.abc import Sequence
from typing import Any
from typing import overload

from shipslog._columns import transpose
from shipslog.picard._histograms import ClippedBasesHistogram
from shipslog.picard._histograms import ClippedBasesHistogramColumns
from shipslog.picard._histograms import DuplicateSetSizeHistogram
from shipslog.picard._histograms import DuplicateSetSizeHistogramColumns
from shipslog.picard._histograms import DuplicationRoiHistogram
from shipslog.picard._histograms import DuplicationRoiHistogramColumns
from shipslog.picard._histograms import HsHistogram
from shipslog.picard._histograms import HsHistogramColumns
from shipslog.picard._histograms import IndependentReplicateHistogram
from shipslog.picard._histograms import IndependentReplicateHistogramColumns
from shipslog.picard._histograms import InsertSizeHistogram
from shipslog.picard._histograms import InsertSizeHistogramColumns
from shipslog.picard._histograms import LibraryComplexityHistogram
from shipslog.picard._histograms import LibraryComplexityHistogramColumns
from shipslog.picard._histograms import MeanQualityByCycle
from shipslog.picard._histograms import MeanQualityByCycleColumns
from shipslog.picard._histograms import QualityScoreDistribution
from shipslog.picard._histograms import QualityScoreDistributionColumns
from shipslog.picard._histograms import QualityYieldFlowHistogram
from shipslog.picard._histograms import QualityYieldFlowHistogramColumns
from shipslog.picard._histograms import QualityYieldSnvqHistogram
from shipslog.picard._histograms import QualityYieldSnvqHistogramColumns
from shipslog.picard._histograms import ReadLengthHistogram
from shipslog.picard._histograms import ReadLengthHistogramColumns
from shipslog.picard._histograms import RnaCoverageHistogram
from shipslog.picard._histograms import RnaCoverageHistogramColumns
from shipslog.picard._histograms import SamComparisonHistogram
from shipslog.picard._histograms import SamComparisonHistogramColumns
from shipslog.picard._histograms import UmiPrevalenceHistogram
from shipslog.picard._histograms import UmiPrevalenceHistogramColumns
from shipslog.picard._histograms import WgsHistogram
from shipslog.picard._histograms import WgsHistogramColumns
from shipslog.picard._histograms import WgsNonZeroCoverageHistogram
from shipslog.picard._histograms import WgsNonZeroCoverageHistogramColumns
from shipslog.picard._reader import histogram_of


@overload
def columns(rows: Sequence[ClippedBasesHistogram], /) -> ClippedBasesHistogramColumns: ...


@overload
def columns(rows: Sequence[DuplicateSetSizeHistogram], /) -> DuplicateSetSizeHistogramColumns: ...


@overload
def columns(rows: Sequence[DuplicationRoiHistogram], /) -> DuplicationRoiHistogramColumns: ...


@overload
def columns(rows: Sequence[HsHistogram], /) -> HsHistogramColumns: ...


@overload
def columns(
    rows: Sequence[IndependentReplicateHistogram], /
) -> IndependentReplicateHistogramColumns: ...


@overload
def columns(rows: Sequence[InsertSizeHistogram], /) -> InsertSizeHistogramColumns: ...


@overload
def columns(rows: Sequence[LibraryComplexityHistogram], /) -> LibraryComplexityHistogramColumns: ...


@overload
def columns(rows: Sequence[MeanQualityByCycle], /) -> MeanQualityByCycleColumns: ...


@overload
def columns(rows: Sequence[QualityScoreDistribution], /) -> QualityScoreDistributionColumns: ...


@overload
def columns(rows: Sequence[QualityYieldFlowHistogram], /) -> QualityYieldFlowHistogramColumns: ...


@overload
def columns(rows: Sequence[QualityYieldSnvqHistogram], /) -> QualityYieldSnvqHistogramColumns: ...


@overload
def columns(rows: Sequence[ReadLengthHistogram], /) -> ReadLengthHistogramColumns: ...


@overload
def columns(rows: Sequence[RnaCoverageHistogram], /) -> RnaCoverageHistogramColumns: ...


@overload
def columns(rows: Sequence[SamComparisonHistogram], /) -> SamComparisonHistogramColumns: ...


@overload
def columns(rows: Sequence[UmiPrevalenceHistogram], /) -> UmiPrevalenceHistogramColumns: ...


@overload
def columns(rows: Sequence[WgsHistogram], /) -> WgsHistogramColumns: ...


@overload
def columns(
    rows: Sequence[WgsNonZeroCoverageHistogram], /
) -> WgsNonZeroCoverageHistogramColumns: ...


def columns(rows: Sequence[object], /) -> Any:
    """Transpose the rows of a Picard histogram into one tuple per field.

    The extra columns of the rows, if the histogram has them, become a dict of one tuple per name.
    Rows of a subclass of a histogram dataclass give the columns of that histogram.

    Args:
        rows: the rows of one histogram, such as those a `PicardHistogramReader` reads.

    Raises:
        ValueError: if there are no rows, or the rows do not all name the same extra columns.
        TypeError: if the rows are not of a Picard histogram dataclass.
    """
    if not rows:
        raise ValueError("columns needs at least one row, to know their type!")
    return transpose(rows, histogram_of(type(rows[0])).columns)
