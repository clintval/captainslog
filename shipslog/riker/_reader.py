from pathlib import Path
from typing import Any
from typing import TextIO

from typeline import ReaderOptions
from typeline import RecordType
from typeline import TsvReader
from typing_extensions import Unpack

from shipslog._binding import FromPath
from shipslog.riker._metrics import AlignmentMetrics
from shipslog.riker._metrics import BaseDistributionByCycle
from shipslog.riker._metrics import ErrorIndel
from shipslog.riker._metrics import ErrorMismatch
from shipslog.riker._metrics import ErrorOverlap
from shipslog.riker._metrics import GcbiasDetail
from shipslog.riker._metrics import GcbiasSummary
from shipslog.riker._metrics import HybcapMetrics
from shipslog.riker._metrics import HybcapPerBase
from shipslog.riker._metrics import HybcapPerTarget
from shipslog.riker._metrics import IsizeHistogram
from shipslog.riker._metrics import IsizeMetrics
from shipslog.riker._metrics import MeanQualityByCycle
from shipslog.riker._metrics import QualityScoreDistribution
from shipslog.riker._metrics import RnaBiotype
from shipslog.riker._metrics import RnaInsertSize
from shipslog.riker._metrics import RnaInsertSizeHistogram
from shipslog.riker._metrics import RnaMetrics
from shipslog.riker._metrics import WgsCoverage
from shipslog.riker._metrics import WgsMetrics

# fmt: off
SUFFIXES: dict[str, type[Any]] = {
    ".alignment-metrics.txt": AlignmentMetrics,
    ".base-distribution-by-cycle.txt": BaseDistributionByCycle,
    ".error-indel.txt": ErrorIndel,
    ".error-mismatch.txt": ErrorMismatch,
    ".error-overlap.txt": ErrorOverlap,
    ".gcbias-detail.txt": GcbiasDetail,
    ".gcbias-summary.txt": GcbiasSummary,
    ".hybcap-metrics.txt": HybcapMetrics,
    ".hybcap-per-base.txt": HybcapPerBase,
    ".hybcap-per-target.txt": HybcapPerTarget,
    ".isize-histogram.txt": IsizeHistogram,
    ".isize-metrics.txt": IsizeMetrics,
    ".mean-quality-by-cycle.txt": MeanQualityByCycle,
    ".quality-score-distribution.txt": QualityScoreDistribution,
    ".rna-biotype.txt": RnaBiotype,
    ".rna-insert-size.txt": RnaInsertSize,
    ".rna-insert-size-histogram.txt": RnaInsertSizeHistogram,
    ".rna-metrics.txt": RnaMetrics,
    ".wgs-coverage.txt": WgsCoverage,
    ".wgs-metrics.txt": WgsMetrics,
}
# fmt: on


def check_riker_class(record_type: type[Any]) -> None:
    """Refuse a class that neither is nor inherits from a Riker dataclass.

    Args:
        record_type: the class to check.

    Raises:
        TypeError: if the class is not a Riker dataclass or a subclass of one.
    """
    if not any(kind in SUFFIXES.values() for kind in record_type.__mro__):
        raise TypeError(f"{record_type.__name__} is not a Riker dataclass!")


def metrics_class(path: Path | str) -> type[Any]:
    """Name the Riker dataclass of a metrics file by the suffix of its path, reading no file.

    One `.gz` or `.bgz` is dropped from the end of the path, then the longest suffix is matched.

    Args:
        path: the path of a Riker metrics file.

    Raises:
        ValueError: if the path does not end with a suffix of a Riker 0.5.0 metrics file.
    """
    name = str(path)
    for compression in (".gz", ".bgz"):
        if name.endswith(compression):
            name = name.removesuffix(compression)
            break
    suffix = max((s for s in SUFFIXES if name.endswith(s)), key=len, default=None)
    if suffix is None:
        raise ValueError(f"{path} does not end with a Riker 0.5.0 suffix: {sorted(SUFFIXES)}!")
    return SUFFIXES[suffix]


class RikerReader(TsvReader[RecordType]):
    """A reader of a Riker metrics file, into its Riker dataclass."""

    from_path: FromPath = FromPath()  # type: ignore[assignment]  # pyright: ignore[reportIncompatibleVariableOverride]  # ty: ignore[invalid-attribute-override]

    def __init__(self, handle: TextIO, /, **options: Unpack[ReaderOptions]) -> None:
        """Read the rows of a Riker metrics file.

        Args:
            handle: the text of the file.
            options: the options of the reader, left at Riker's defaults when not given.

        Raises:
            TypeError: if the record type is not a Riker dataclass or a subclass of one.
            ValueError: if the columns of the file differ from the record type's fields, naming
                those missing from the file and those it does not expect.
        """
        check_riker_class(self._bound_record_type())
        _ = options.setdefault("comment_prefixes", ())
        super().__init__(handle, **options)
