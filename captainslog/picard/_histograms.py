from collections.abc import Mapping
from dataclasses import dataclass
from dataclasses import field
from typing import Any

from typeline import NamedExtraColumns

__all__ = [
    "ClippedBasesHistogram",
    "DuplicateSetSizeHistogram",
    "DuplicationRoiHistogram",
    "HsHistogram",
    "IndependentReplicateHistogram",
    "InsertSizeHistogram",
    "LibraryComplexityHistogram",
    "MeanQualityByCycle",
    "QualityScoreDistribution",
    "QualityYieldFlowHistogram",
    "QualityYieldSnvqHistogram",
    "ReadLengthHistogram",
    "RnaCoverageHistogram",
    "SamComparisonHistogram",
    "UmiPrevalenceHistogram",
    "WgsHistogram",
    "WgsNonZeroCoverageHistogram",
]


@dataclass(frozen=True, kw_only=True)
class ClippedBasesHistogram:
    """The histogram of adapter bases clipped from each read, as MarkIlluminaAdapters writes it."""

    clipped_bases: int = 0
    """The number of adapter bases clipped from a read."""

    read_count: int = 0
    """The number of reads with that many bases clipped."""


@dataclass(frozen=True, kw_only=True)
class DuplicateSetSizeHistogram:
    """The duplicate set sizes of MarkDuplicates, for several libraries or no library size."""

    set_size: float = 0.0
    """The number of reads in a duplicate set, counting a read without duplicates as a set of 1."""

    all_sets: int = 0
    """The number of duplicate sets of that size."""

    non_optical_sets: int = 0
    """The number of duplicate sets of that size once their optical duplicates are left out."""

    counts: NamedExtraColumns[int] = field(default_factory=dict)
    """`optical_sets`, the number of sets of that many optical duplicates plus one, if any."""


@dataclass(frozen=True, kw_only=True)
class DuplicationRoiHistogram:
    """The return on sequencing and duplicate set sizes MarkDuplicates writes for one library."""

    bin: float = 0.0
    """The multiple of sequencing for `coverage_mult`, and the duplicate set size for the sets."""

    coverage_mult: float = 0.0
    """The multiple of the unique read pairs seen that `bin` times the sequencing would see."""

    all_sets: int = 0
    """The number of duplicate sets of that size."""

    non_optical_sets: int = 0
    """The number of duplicate sets of that size once their optical duplicates are left out."""

    counts: NamedExtraColumns[int] = field(default_factory=dict)
    """`optical_sets`, the number of sets of that many optical duplicates plus one, if any."""


@dataclass(frozen=True, kw_only=True)
class HsHistogram:
    """The coverage and base quality histogram of CollectHsMetrics and CollectTargetedPcrMetrics."""

    coverage_or_base_quality: int = 0
    """The depth of coverage for the coverage count, and the base quality for the base counts."""

    high_quality_coverage_count: int = 0
    """The number of target bases at that depth, not counting bases below the minimum quality."""

    unfiltered_baseq_count: int = 0
    """The number of on-target bases of that base quality, counting only bases above quality 2."""


@dataclass(frozen=True, kw_only=True)
class IndependentReplicateHistogram:
    """The allele balance and UMI edit distances CollectIndependentReplicateMetrics writes."""

    allele_balance: int = 0
    """The percent of a site's reads that hold its alternate allele, or a UMI edit distance."""

    allele_balance_count: int = 0
    """The number of heterozygous sites with that allele balance."""

    counts: NamedExtraColumns[int] = field(default_factory=dict)
    """`diffAllelesCount` and `sameAllelesCount`, the duplicate pairs of different and of the same
    alleles whose UMIs are that edit distance apart, when reads hold UMIs.
    """


@dataclass(frozen=True, kw_only=True)
class InsertSizeHistogram:
    """The insert size histogram CollectInsertSizeMetrics writes."""

    insert_size: int = 0
    """The insert size of a read pair."""

    counts: NamedExtraColumns[int] = field(default_factory=dict)
    """The number of read pairs of that insert size, by accumulation level and pair orientation,
    e.g. `All_Reads.fr_count`.
    """


@dataclass(frozen=True, kw_only=True)
class LibraryComplexityHistogram:
    """The histogram of duplicate group sizes EstimateLibraryComplexity writes."""

    duplication_group_count: int = 0
    """The number of read pairs in a group of duplicates."""

    counts: NamedExtraColumns[int] = field(default_factory=dict)
    """The number of duplicate groups of that size, by library."""


@dataclass(frozen=True, kw_only=True)
class MeanQualityByCycle:
    """The mean base quality by cycle MeanQualityByCycle writes."""

    cycle: int = 0
    """The cycle, numbering the cycles of the second read after those of the first."""

    mean_quality: float = 0.0
    """The mean base quality of the bases of that cycle."""

    means: NamedExtraColumns[float] = field(default_factory=dict)
    """`MEAN_ORIGINAL_QUALITY`, the mean original base quality of that cycle, when reads hold OQ."""


@dataclass(frozen=True, kw_only=True)
class QualityScoreDistribution:
    """The distribution of base qualities QualityScoreDistribution writes."""

    quality: int = 0
    """The base quality."""

    count_of_q: int = 0
    """The number of bases of that base quality."""

    counts: NamedExtraColumns[int] = field(default_factory=dict)
    """`COUNT_OF_OQ`, the number of bases of that original base quality, when reads hold OQ."""


@dataclass(frozen=True, kw_only=True)
class QualityYieldFlowHistogram:
    """The flow quality histogram of CollectQualityYieldMetricsFlow, with INCLUDE_BQ_HISTOGRAM."""

    key: int = 0
    """The flow quality for `qual_count`, and the cycle of four flows for the cycle qualities."""

    qual_count: int = 0
    """The number of flows of that quality."""

    mean_cycle_qual: float = 0.0
    """The mean over reads of the mean flow quality of the cycle."""

    median_cycle_qual: float = 0.0
    """The median over reads of the mean flow quality of the cycle."""

    q25_cycle_qual: float = 0.0
    """The 25th percentile over reads of the mean flow quality of the cycle."""

    q75_cycle_qual: float = 0.0
    """The 75th percentile over reads of the mean flow quality of the cycle."""


@dataclass(frozen=True, kw_only=True)
class QualityYieldSnvqHistogram:
    """The quality histogram CollectQualityYieldMetricsSNVQ writes with INCLUDE_BQ_HISTOGRAM."""

    key: int = 0
    """The quality for the counts, and the read position for the means."""

    bq_count: int = 0
    """The number of bases of that base quality."""

    snvq_count: int = 0
    """The number of SNV qualities of that value, one per base for each base it is not."""

    read_index_mean_bq: float = 0.0
    """The mean base quality at that read position."""

    read_index_mean_snvq: float = 0.0
    """The mean SNV quality at that read position."""


@dataclass(frozen=True, kw_only=True)
class ReadLengthHistogram:
    """The read length histogram CollectAlignmentSummaryMetrics writes over all reads."""

    read_length: int = 0
    """The length of a read, or of its aligned part for the aligned counts."""

    counts: NamedExtraColumns[int] = field(default_factory=dict)
    """The number of reads of that length, e.g. `PAIRED_TOTAL_LENGTH_COUNT`, for the paired and the
    unpaired reads Picard saw, over their whole length and their aligned length.
    """


@dataclass(frozen=True, kw_only=True)
class RnaCoverageHistogram:
    """The normalized coverage by transcript position CollectRnaSeqMetrics writes."""

    normalized_position: int = 0
    """The percent of the way along a transcript, from its 5' end."""

    normalized_coverage: NamedExtraColumns[float] = field(default_factory=dict)
    """The mean normalized coverage at that position of the most highly expressed transcripts, by
    accumulation level, e.g. `All_Reads.normalized_coverage`.
    """


@dataclass(frozen=True, kw_only=True)
class SamComparisonHistogram:
    """The mapping quality histogram CompareSAMs writes with COMPARE_MQ."""

    bin: str = ""
    """The mapping qualities of a read in the left and in the right file, e.g. `60,0`."""

    value: int = 0
    """The number of reads with that pair of mapping qualities."""


@dataclass(frozen=True, kw_only=True)
class UmiPrevalenceHistogram:
    """The histogram of UMIs per duplicate set CollectUmiPrevalenceMetrics writes."""

    num_umis: int = 0
    """The number of distinct UMIs in a duplicate set."""

    duplicate_sets: int = 0
    """The number of duplicate sets with that many distinct UMIs."""


@dataclass(frozen=True, kw_only=True)
class WgsHistogram:
    """The coverage histogram CollectWgsMetrics and CollectRawWgsMetrics write."""

    coverage: int = 0
    """The depth of coverage, and the base quality for `unfiltered_baseq_count`."""

    high_quality_coverage_count: int = 0
    """The number of sites at that depth, not counting bases below the minimum base quality."""

    counts: NamedExtraColumns[int] = field(default_factory=dict)
    """`unfiltered_baseq_count`, the number of bases of that quality, with INCLUDE_BQ_HISTOGRAM."""


@dataclass(frozen=True, kw_only=True)
class WgsNonZeroCoverageHistogram:
    """The coverage histogram CollectWgsMetricsWithNonZeroCoverage writes."""

    coverage: int = 0
    """The depth of coverage, and the base quality for `unfiltered_baseq_count`."""

    count_whole_genome: int = 0
    """The number of sites at that depth over the whole genome, not counting low quality bases."""

    count_non_zero_regions: int = 0
    """The number of sites at that depth over the sites with coverage, so none at depth 0."""

    counts: NamedExtraColumns[int] = field(default_factory=dict)
    """`unfiltered_baseq_count`, the number of bases of that quality, with INCLUDE_BQ_HISTOGRAM."""


@dataclass(frozen=True)
class Histogram:
    """How Picard writes a histogram into a metrics file."""

    owners: frozenset[str]
    """The Java names of the metrics classes whose files hold it, or none for a histogram alone."""

    key: str
    """The Java class of its bins, as the `## HISTOGRAM` line names it, e.g. `java.lang.Integer`."""

    labels: Mapping[str, str]
    """The label of the column of each field always written, by field name, in field order."""


# fmt: off
HISTOGRAMS: dict[type[Any], Histogram] = {
    ClippedBasesHistogram: Histogram(owners=frozenset(), key="java.lang.Integer", labels={"clipped_bases": "clipped_bases", "read_count": "read_count"}),
    DuplicateSetSizeHistogram: Histogram(owners=frozenset({"picard.sam.DuplicationMetrics", "picard.sam.FlowBasedDuplicationMetrics"}), key="java.lang.Double", labels={"set_size": "set_size", "all_sets": "all_sets", "non_optical_sets": "non_optical_sets"}),
    DuplicationRoiHistogram: Histogram(owners=frozenset({"picard.sam.DuplicationMetrics", "picard.sam.FlowBasedDuplicationMetrics"}), key="java.lang.Double", labels={"bin": "BIN", "coverage_mult": "CoverageMult", "all_sets": "all_sets", "non_optical_sets": "non_optical_sets"}),
    HsHistogram: Histogram(owners=frozenset({"picard.analysis.directed.HsMetrics", "picard.analysis.directed.TargetedPcrMetrics"}), key="java.lang.Integer", labels={"coverage_or_base_quality": "coverage_or_base_quality", "high_quality_coverage_count": "high_quality_coverage_count", "unfiltered_baseq_count": "unfiltered_baseq_count"}),
    IndependentReplicateHistogram: Histogram(owners=frozenset({"picard.analysis.replicates.IndependentReplicateMetric"}), key="java.lang.Byte", labels={"allele_balance": "alleleBalance", "allele_balance_count": "alleleBalanceCount"}),
    InsertSizeHistogram: Histogram(owners=frozenset({"picard.analysis.InsertSizeMetrics"}), key="java.lang.Integer", labels={"insert_size": "insert_size"}),
    LibraryComplexityHistogram: Histogram(owners=frozenset({"picard.sam.DuplicationMetrics"}), key="java.lang.Integer", labels={"duplication_group_count": "duplication_group_count"}),
    MeanQualityByCycle: Histogram(owners=frozenset(), key="java.lang.Integer", labels={"cycle": "CYCLE", "mean_quality": "MEAN_QUALITY"}),
    QualityScoreDistribution: Histogram(owners=frozenset(), key="java.lang.Byte", labels={"quality": "QUALITY", "count_of_q": "COUNT_OF_Q"}),
    QualityYieldFlowHistogram: Histogram(owners=frozenset({"picard.analysis.CollectQualityYieldMetricsFlow$QualityYieldMetricsFlow"}), key="java.lang.Integer", labels={"key": "KEY", "qual_count": "QUAL_COUNT", "mean_cycle_qual": "MEAN_CYCLE_QUAL", "median_cycle_qual": "MEDIAN_CYCLE_QUAL", "q25_cycle_qual": "Q25_CYCLE_QUAL", "q75_cycle_qual": "Q75_CYCLE_QUAL"}),
    QualityYieldSnvqHistogram: Histogram(owners=frozenset({"picard.analysis.CollectQualityYieldMetricsSNVQ$QualityYieldMetrics"}), key="java.lang.Integer", labels={"key": "KEY", "bq_count": "BQ_COUNT", "snvq_count": "SNVQ_COUNT", "read_index_mean_bq": "READ_INDEX_MEAN_BQ", "read_index_mean_snvq": "READ_INDEX_MEAN_SNVQ"}),
    ReadLengthHistogram: Histogram(owners=frozenset({"picard.analysis.AlignmentSummaryMetrics"}), key="java.lang.Integer", labels={"read_length": "READ_LENGTH"}),
    RnaCoverageHistogram: Histogram(owners=frozenset({"picard.analysis.RnaSeqMetrics"}), key="java.lang.Integer", labels={"normalized_position": "normalized_position"}),
    SamComparisonHistogram: Histogram(owners=frozenset({"picard.sam.SamComparisonMetric"}), key="java.lang.String", labels={"bin": "BIN", "value": "VALUE"}),
    UmiPrevalenceHistogram: Histogram(owners=frozenset(), key="java.lang.Integer", labels={"num_umis": "numUmis", "duplicate_sets": "duplicateSets"}),
    WgsHistogram: Histogram(owners=frozenset({"picard.analysis.WgsMetrics", "picard.analysis.CollectRawWgsMetrics$RawWgsMetrics"}), key="java.lang.Integer", labels={"coverage": "coverage", "high_quality_coverage_count": "high_quality_coverage_count"}),
    WgsNonZeroCoverageHistogram: Histogram(owners=frozenset({"picard.analysis.CollectWgsMetricsWithNonZeroCoverage$WgsMetricsWithNonZeroCoverage"}), key="java.lang.Integer", labels={"coverage": "coverage", "count_whole_genome": "count_WHOLE_GENOME", "count_non_zero_regions": "count_NON_ZERO_REGIONS"}),
}
# fmt: on
