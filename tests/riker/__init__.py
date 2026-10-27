from pathlib import Path
from typing import Any

from captainslog.riker import AlignmentMetrics
from captainslog.riker import BaseDistributionByCycle
from captainslog.riker import ErrorIndel
from captainslog.riker import ErrorMismatch
from captainslog.riker import ErrorOverlap
from captainslog.riker import GcbiasDetail
from captainslog.riker import GcbiasSummary
from captainslog.riker import HybcapMetrics
from captainslog.riker import HybcapPerBase
from captainslog.riker import HybcapPerTarget
from captainslog.riker import IsizeHistogram
from captainslog.riker import IsizeMetrics
from captainslog.riker import MeanQualityByCycle
from captainslog.riker import QualityScoreDistribution
from captainslog.riker import RnaBiotype
from captainslog.riker import RnaInsertSize
from captainslog.riker import RnaInsertSizeHistogram
from captainslog.riker import RnaMetrics
from captainslog.riker import WgsCoverage
from captainslog.riker import WgsMetrics

DATA = Path(__file__).parents[1] / "data" / "riker"

RIKER_FIXTURES = sorted(DATA.glob("*.txt"))

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
