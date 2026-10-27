from dataclasses import dataclass
from pathlib import Path
from typing import Any

from captainslog.picard import DuplicateSetSizeHistogram
from captainslog.picard import DuplicationRoiHistogram
from captainslog.picard import HsHistogram
from captainslog.picard import InsertSizeHistogram
from captainslog.picard import LibraryComplexityHistogram
from captainslog.picard import MeanQualityByCycle
from captainslog.picard import PicardWriter
from captainslog.picard import QualityScoreDistribution
from captainslog.picard import ReadLengthHistogram
from captainslog.picard import RnaCoverageHistogram
from captainslog.picard import WgsHistogram
from captainslog.picard import WgsNonZeroCoverageHistogram
from captainslog.picard._header import PicardHeader
from captainslog.picard._java import JAVA_NAMES

DATA = Path(__file__).parents[1] / "data" / "picard"

METRICS_CLASS = "## METRICS CLASS\t"

HISTOGRAM = "## HISTOGRAM"

LINES = [
    "## htsjdk.samtools.metrics.StringHeader",
    "# CollectQualityYieldMetrics I=in.bam O=out.txt",
    "## htsjdk.samtools.metrics.StringHeader",
    "# Started on: Sat Oct 24 10:00:00 HST 2026",
    "## htsjdk.samtools.metrics.VersionHeader",
    "# picard\t3.5.0",
]
HEADER = PicardHeader(
    command_line="CollectQualityYieldMetrics I=in.bam O=out.txt",
    started_on="Sat Oct 24 10:00:00 HST 2026",
    others=(("htsjdk.samtools.metrics.VersionHeader", "picard\t3.5.0"),),
)


@dataclass(frozen=True)
class NotHistogram:
    """A dataclass that is not a Picard histogram dataclass."""

    insert_size: int


class DerivedHistogram(InsertSizeHistogram):
    """A user's subclass of a Picard histogram that derives a count."""

    @property
    def all_reads(self) -> int:
        """The number of read pairs of the insert size, over all reads in FR orientation."""
        return self.counts["All_Reads.fr_count"]


def _metrics_class_line(path: Path) -> str | None:
    lines = path.read_text().splitlines()
    return next((line for line in lines if line.startswith(METRICS_CLASS)), None)


PICARD_METRICS_FIXTURES = sorted(path for path in DATA.glob("*") if _metrics_class_line(path))


def _holds_a_histogram(path: Path) -> bool:
    return any(line.startswith(HISTOGRAM) for line in path.read_text().splitlines())


PICARD_HISTOGRAM_FIXTURES = sorted(path for path in DATA.glob("*") if _holds_a_histogram(path))

FIXTURE_CLASSES: dict[str, type[Any]] = {
    "cmm.alignment_summary_metrics.txt": ReadLengthHistogram,
    "cmm.insert_size_metrics.txt": InsertSizeHistogram,
    "cmm.quality_by_cycle_metrics.txt": MeanQualityByCycle,
    "cmm.quality_distribution_metrics.txt": QualityScoreDistribution,
    "dup.duplication_metrics.txt": DuplicateSetSizeHistogram,
    "elc.duplication_metrics.txt": LibraryComplexityHistogram,
    "hs.hs_metrics.txt": HsHistogram,
    "nonzero.wgs_metrics.txt": WgsNonZeroCoverageHistogram,
    "one_library.duplication_metrics.txt": DuplicationRoiHistogram,
    "pcr.targeted_pcr_metrics.txt": HsHistogram,
    "raw.raw_wgs_metrics.txt": WgsHistogram,
    "rna.rna_metrics.txt": RnaCoverageHistogram,
    "wgs.wgs_metrics.txt": WgsHistogram,
}


def class_named_in(path: Path) -> type[Any]:
    """The dataclass of the Java class that a file's `## METRICS CLASS` line names."""
    line = _metrics_class_line(path)
    assert line is not None, f"{path} has no {METRICS_CLASS!r} line"
    name = line.removeprefix(METRICS_CLASS)
    return next(kind for kind, java in JAVA_NAMES.items() if java == name)


REPEATED_INSERT_SIZES = [
    "## HISTOGRAM\tjava.lang.Integer",
    "insert_size\tAll_Reads.fr_count\tNA12891.fr_count\tNA12891.fr_count\tPond-2.fr_count",
    "100\t5\t5\t3\t2",
    "101\t7\t7\t4\t3",
]
"""An insert size histogram of a sample `NA12891` of two libraries, one of which shares its name."""

REPEATED_RNA_COVERAGE = [
    "## HISTOGRAM\tjava.lang.Integer",
    "normalized_position\tAll_Reads.normalized_coverage\tNA12891.normalized_coverage"
    + "\tNA12891.normalized_coverage",
    "0\t0.5\t0.5\t0.25",
    "1\t1.25\t1.25\t1.5",
]
"""An RNA coverage histogram of a sample `NA12891` and a library of that name."""


def with_histogram(path: Path, metric: object, lines: list[str]) -> Path:
    """Write a file of one metric under the test header, then a histogram of these lines."""
    kind: type[Any] = type(metric)
    with PicardWriter.from_path[kind](path, header=HEADER) as writer:
        writer.write(metric)
    _ = path.write_text(path.read_text().removesuffix("\n") + "\n".join([*lines, "", ""]))
    return path


VALIDATE_SAM_FILE = [
    "",
    "",
    "## HISTOGRAM\tjava.lang.String",
    "Error Type\tCount",
    "ERROR:MATE_NOT_FOUND\t1",
    "WARNING:MISSING_TAG_NM\t3",
]
"""The lines of the summary ValidateSamFile writes, of no header and a histogram alone."""
