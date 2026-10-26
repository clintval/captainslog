from pathlib import Path
from typing import Any

from shipslog.riker import AlignmentMetrics
from shipslog.riker import BaseDistributionByCycle
from shipslog.riker import ErrorIndel
from shipslog.riker import ErrorMismatch
from shipslog.riker import ErrorOverlap
from shipslog.riker import GcbiasDetail
from shipslog.riker import GcbiasSummary
from shipslog.riker import HybcapMetrics
from shipslog.riker import HybcapPerBase
from shipslog.riker import HybcapPerTarget
from shipslog.riker import IsizeHistogram
from shipslog.riker import IsizeMetrics
from shipslog.riker import MeanQualityByCycle
from shipslog.riker import QualityScoreDistribution
from shipslog.riker import RnaBiotype
from shipslog.riker import RnaInsertSize
from shipslog.riker import RnaInsertSizeHistogram
from shipslog.riker import RnaMetrics
from shipslog.riker import WgsCoverage
from shipslog.riker import WgsMetrics

DATA = Path(__file__).parents[1] / "data" / "riker"

ALL_RIKER_FIXTURES = sorted(DATA.glob("*.txt"))

RIKER_FIXTURES = [path for path in ALL_RIKER_FIXTURES if path.read_text().strip()]

# fmt: off
CLASSES: dict[str, type[Any]] = {
    "alignment-metrics": AlignmentMetrics,
    "base-distribution-by-cycle": BaseDistributionByCycle,
    "error-indel": ErrorIndel,
    "error-mismatch": ErrorMismatch,
    "error-overlap": ErrorOverlap,
    "gcbias-detail": GcbiasDetail,
    "gcbias-summary": GcbiasSummary,
    "hybcap-metrics": HybcapMetrics,
    "hybcap-per-base": HybcapPerBase,
    "hybcap-per-target": HybcapPerTarget,
    "isize-histogram": IsizeHistogram,
    "isize-metrics": IsizeMetrics,
    "mean-quality-by-cycle": MeanQualityByCycle,
    "quality-score-distribution": QualityScoreDistribution,
    "rna-biotype": RnaBiotype,
    "rna-insert-size": RnaInsertSize,
    "rna-insert-size-histogram": RnaInsertSizeHistogram,
    "rna-metrics": RnaMetrics,
    "wgs-coverage": WgsCoverage,
    "wgs-metrics": WgsMetrics,
}
# fmt: on


def riker_class_of(path: Path) -> type[Any]:
    """The dataclass of a Riker fixture, by the suffix of its name."""
    suffix = next(s for s in sorted(CLASSES, key=len, reverse=True) if path.stem.endswith("." + s))
    return CLASSES[suffix]
