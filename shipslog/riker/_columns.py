from collections.abc import Sequence
from typing import Any
from typing import overload

from shipslog._columns import transpose
from shipslog.riker._metrics import IsizeHistogram
from shipslog.riker._metrics import IsizeHistogramColumns
from shipslog.riker._metrics import MeanQualityByCycle
from shipslog.riker._metrics import MeanQualityByCycleColumns
from shipslog.riker._metrics import QualityScoreDistribution
from shipslog.riker._metrics import QualityScoreDistributionColumns
from shipslog.riker._metrics import RnaInsertSizeHistogram
from shipslog.riker._metrics import RnaInsertSizeHistogramColumns
from shipslog.riker._metrics import WgsCoverage
from shipslog.riker._metrics import WgsCoverageColumns

# fmt: off
HISTOGRAMS: dict[type[Any], type[Any]] = {
    IsizeHistogram: IsizeHistogramColumns,
    MeanQualityByCycle: MeanQualityByCycleColumns,
    QualityScoreDistribution: QualityScoreDistributionColumns,
    RnaInsertSizeHistogram: RnaInsertSizeHistogramColumns,
    WgsCoverage: WgsCoverageColumns,
}
# fmt: on


# fmt: off
@overload
def columns(rows: Sequence[IsizeHistogram], /) -> IsizeHistogramColumns: ...
@overload
def columns(rows: Sequence[MeanQualityByCycle], /) -> MeanQualityByCycleColumns: ...
@overload
def columns(rows: Sequence[QualityScoreDistribution], /) -> QualityScoreDistributionColumns: ...
@overload
def columns(rows: Sequence[RnaInsertSizeHistogram], /) -> RnaInsertSizeHistogramColumns: ...
@overload
def columns(rows: Sequence[WgsCoverage], /) -> WgsCoverageColumns: ...
# fmt: on


def columns(rows: Sequence[object], /) -> Any:
    """Transpose the rows of a Riker histogram into one tuple per field.

    Rows of a subclass of a histogram dataclass give the columns of that histogram.

    Args:
        rows: the rows of one histogram, such as those a `RikerReader` reads.

    Raises:
        ValueError: if there are no rows.
        TypeError: if the rows are not of a Riker histogram dataclass.
    """
    if not rows:
        raise ValueError("columns needs at least one row, to know their type!")
    kind = type(rows[0])
    for base in kind.__mro__:
        if base in HISTOGRAMS:
            return transpose(rows, HISTOGRAMS[base])
    raise TypeError(f"{kind.__name__} is not a Riker histogram dataclass!")
