from collections.abc import Sequence
from typing import Any
from typing import overload

from captainslog._columns import transpose
from captainslog.picard._histograms import ClippedBasesHistogram
from captainslog.picard._histograms import ClippedBasesHistogramColumns
from captainslog.picard._histograms import DuplicateSetSizeHistogram
from captainslog.picard._histograms import DuplicateSetSizeHistogramColumns
from captainslog.picard._histograms import DuplicationRoiHistogram
from captainslog.picard._histograms import DuplicationRoiHistogramColumns
from captainslog.picard._histograms import HsHistogram
from captainslog.picard._histograms import HsHistogramColumns
from captainslog.picard._histograms import IndependentReplicateHistogram
from captainslog.picard._histograms import IndependentReplicateHistogramColumns
from captainslog.picard._histograms import InsertSizeHistogram
from captainslog.picard._histograms import InsertSizeHistogramColumns
from captainslog.picard._histograms import LibraryComplexityHistogram
from captainslog.picard._histograms import LibraryComplexityHistogramColumns
from captainslog.picard._histograms import MeanQualityByCycle
from captainslog.picard._histograms import MeanQualityByCycleColumns
from captainslog.picard._histograms import QualityScoreDistribution
from captainslog.picard._histograms import QualityScoreDistributionColumns
from captainslog.picard._histograms import QualityYieldFlowHistogram
from captainslog.picard._histograms import QualityYieldFlowHistogramColumns
from captainslog.picard._histograms import QualityYieldSnvqHistogram
from captainslog.picard._histograms import QualityYieldSnvqHistogramColumns
from captainslog.picard._histograms import ReadLengthHistogram
from captainslog.picard._histograms import ReadLengthHistogramColumns
from captainslog.picard._histograms import RnaCoverageHistogram
from captainslog.picard._histograms import RnaCoverageHistogramColumns
from captainslog.picard._histograms import SamComparisonHistogram
from captainslog.picard._histograms import SamComparisonHistogramColumns
from captainslog.picard._histograms import UmiPrevalenceHistogram
from captainslog.picard._histograms import UmiPrevalenceHistogramColumns
from captainslog.picard._histograms import WgsHistogram
from captainslog.picard._histograms import WgsHistogramColumns
from captainslog.picard._histograms import WgsNonZeroCoverageHistogram
from captainslog.picard._histograms import WgsNonZeroCoverageHistogramColumns
from captainslog.picard._reader import histogram_of


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
