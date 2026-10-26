from dataclasses import dataclass
from enum import StrEnum

__all__ = [
    "AlignmentMetrics",
    "BaseDistributionByCycle",
    "Category",
    "ErrorIndel",
    "ErrorMismatch",
    "ErrorOverlap",
    "GcbiasDetail",
    "GcbiasSummary",
    "HybcapMetrics",
    "HybcapPerBase",
    "HybcapPerTarget",
    "IsizeHistogram",
    "IsizeHistogramColumns",
    "IsizeMetrics",
    "MeanQualityByCycle",
    "MeanQualityByCycleColumns",
    "PairOrientation",
    "QualityScoreDistribution",
    "QualityScoreDistributionColumns",
    "RnaBiotype",
    "RnaInsertSize",
    "RnaInsertSizeHistogram",
    "RnaInsertSizeHistogramColumns",
    "RnaMetrics",
    "StrandSpec",
    "WgsCoverage",
    "WgsCoverageColumns",
    "WgsMetrics",
]


class Category(StrEnum):
    """The `category` column of the alignment metrics: the reads that a row summarizes."""

    READ1 = "read1"
    READ2 = "read2"
    PAIR = "pair"


class PairOrientation(StrEnum):
    """The `pair_orientation` column of the insert size metrics."""

    FR = "FR"
    RF = "RF"
    TANDEM = "TANDEM"


class StrandSpec(StrEnum):
    """The `detected_strand` column of the RNA metrics: the strandedness that Riker resolved."""

    UNSTRANDED = "unstranded"
    FORWARD = "forward"
    REVERSE = "reverse"


@dataclass(frozen=True, kw_only=True)
class AlignmentMetrics:
    """The `.alignment-metrics.txt` table that `riker alignment` writes."""

    sample: str = ""
    """Sample name derived from the BAM read group SM tag or filename."""

    category: Category
    """Read category: read1, read2, or pair."""

    total_reads: int = 0
    """Total number of reads (including QC-failed reads)."""

    aligned_reads: int = 0
    """Number of PF reads that aligned to the reference."""

    frac_aligned: float = 0.0
    """Fraction of PF reads that aligned to the reference."""

    hq_aligned_reads: int = 0
    """Number of aligned reads with mapping quality >= min_mapq."""

    hq_aligned_bases: int = 0
    """Total aligned bases from high-quality reads."""

    hq_aligned_q20_bases: int = 0
    """Number of aligned bases with base quality >= 20 from high-quality reads."""

    hq_median_mismatches: float = 0.0
    """Median number of mismatches per high-quality aligned read."""

    mismatch_rate: float = 0.0
    """Rate of mismatches per aligned base across all PF aligned reads."""

    hq_mismatch_rate: float = 0.0
    """Rate of mismatches per aligned base for high-quality reads only."""

    indel_rate: float = 0.0
    """Rate of insertion and deletion events per aligned base."""

    mean_read_length: float = 0.0
    """Mean read length across all PF reads."""

    sd_read_length: float = 0.0
    """Standard deviation of read length across all PF reads."""

    median_read_length: float = 0.0
    """Median read length across all PF reads."""

    mad_read_length: float = 0.0
    """Median absolute deviation of read length across all PF reads."""

    min_read_length: int = 0
    """Minimum read length observed."""

    max_read_length: int = 0
    """Maximum read length observed."""

    mean_aligned_read_length: float = 0.0
    """Mean aligned read length (M, I, =, X bases) for reads that aligned."""

    aligned_reads_in_pairs: int = 0
    """Number of aligned reads that are part of a mapped pair."""

    frac_aligned_in_pairs: float = 0.0
    """Fraction of aligned reads that are part of a mapped pair."""

    reads_improperly_paired: int = 0
    """Number of reads that are aligned and paired but not properly paired."""

    frac_reads_improperly_paired: float = 0.0
    """Fraction of aligned reads that are improperly paired."""

    bad_cycles: int = 0
    """Number of sequencing cycles where >= 80% of reads had an N base call."""

    strand_balance: float = 0.0
    """Fraction of aligned reads on the positive strand."""

    frac_chimeras: float = 0.0
    """Fraction of read pairs that are chimeric (different contig, large insert, or unexpected
    orientation).
    """

    frac_softclipped_reads: float = 0.0
    """Fraction of total bases that are soft-clipped (mapped reads only)."""

    frac_hardclipped_reads: float = 0.0
    """Fraction of total bases that are hard-clipped (all PF reads)."""

    mean_3prime_softclipped_bases: float = 0.0
    """Mean number of soft-clipped bases at the 3-prime end of reads."""


@dataclass(frozen=True, kw_only=True)
class BaseDistributionByCycle:
    """The `.base-distribution-by-cycle.txt` table that `riker basic` writes."""

    sample: str = ""
    """Sample name derived from the BAM read group SM tag or filename."""

    read_end: int = 0
    """Read end (1 or 2)."""

    cycle: int = 0
    """Sequencing cycle number (1-based)."""

    frac_a: float = 0.0
    """Fraction of A bases at this cycle."""

    frac_c: float = 0.0
    """Fraction of C bases at this cycle."""

    frac_g: float = 0.0
    """Fraction of G bases at this cycle."""

    frac_t: float = 0.0
    """Fraction of T bases at this cycle."""

    frac_n: float = 0.0
    """Fraction of N bases at this cycle."""


@dataclass(frozen=True, kw_only=True)
class MeanQualityByCycle:
    """The `.mean-quality-by-cycle.txt` table that `riker basic` writes."""

    sample: str = ""
    """Sample name derived from the BAM read group SM tag or filename."""

    cycle: int = 0
    """Sequencing cycle number (1-based)."""

    mean_quality: float = 0.0
    """Mean base quality score at this cycle."""


@dataclass(frozen=True, kw_only=True)
class MeanQualityByCycleColumns:
    """The columns of a `MeanQualityByCycle`, one tuple per field."""

    sample: tuple[str, ...] = ()
    cycle: tuple[int, ...] = ()
    mean_quality: tuple[float, ...] = ()


@dataclass(frozen=True, kw_only=True)
class QualityScoreDistribution:
    """The `.quality-score-distribution.txt` table that `riker basic` writes."""

    sample: str = ""
    """Sample name derived from the BAM read group SM tag or filename."""

    quality: int = 0
    """Base quality score."""

    count: int = 0
    """Number of bases with this quality score."""

    frac_bases: float = 0.0
    """Fraction of all bases with this quality score."""


@dataclass(frozen=True, kw_only=True)
class QualityScoreDistributionColumns:
    """The columns of a `QualityScoreDistribution`, one tuple per field."""

    sample: tuple[str, ...] = ()
    quality: tuple[int, ...] = ()
    count: tuple[int, ...] = ()
    frac_bases: tuple[float, ...] = ()


@dataclass(frozen=True, kw_only=True)
class IsizeMetrics:
    """The `.isize-metrics.txt` table that `riker isize` writes."""

    sample: str = ""
    """Sample name derived from the BAM read group SM tag or filename."""

    pair_orientation: PairOrientation
    """Pair orientation (FR, RF, or TANDEM)."""

    read_pairs: int = 0
    """Number of read pairs in this orientation."""

    mean_insert_size: float = 0.0
    """Mean insert size after trimming outliers."""

    standard_deviation: float = 0.0
    """Standard deviation of insert size after trimming outliers."""

    median_insert_size: float = 0.0
    """Median insert size across all pairs in this orientation."""

    median_absolute_deviation: float = 0.0
    """Median absolute deviation of insert size."""

    mode_insert_size: int = 0
    """Most frequent insert size."""

    min_insert_size: int = 0
    """Smallest insert size observed."""

    max_insert_size: int = 0
    """Largest insert size observed."""


@dataclass(frozen=True, kw_only=True)
class IsizeHistogram:
    """The `.isize-histogram.txt` table that `riker isize` writes."""

    sample: str = ""
    """Sample name derived from the BAM read group SM tag or filename."""

    insert_size: int = 0
    """Insert size in base pairs."""

    fr_count: int = 0
    """Number of FR (forward-reverse) pairs at this insert size."""

    rf_count: int = 0
    """Number of RF (reverse-forward) pairs at this insert size."""

    tandem_count: int = 0
    """Number of tandem (FF/RR) pairs at this insert size."""


@dataclass(frozen=True, kw_only=True)
class IsizeHistogramColumns:
    """The columns of an `IsizeHistogram`, one tuple per field."""

    sample: tuple[str, ...] = ()
    insert_size: tuple[int, ...] = ()
    fr_count: tuple[int, ...] = ()
    rf_count: tuple[int, ...] = ()
    tandem_count: tuple[int, ...] = ()


@dataclass(frozen=True, kw_only=True)
class GcbiasDetail:
    """The `.gcbias-detail.txt` table that `riker gcbias` writes."""

    sample: str = ""
    """Sample name derived from the BAM read group SM tag or filename."""

    gc: int = 0
    """GC content percentage (0-100)."""

    windows: int = 0
    """Number of reference windows at this GC percentage."""

    read_starts: int = 0
    """Number of reads starting at positions with this GC percentage."""

    reported_base_quality: float = 0.0
    """Mean of actual base quality scores from reads in this bin."""

    empirical_base_quality: float = 0.0
    """Phred-scaled error rate derived from the NM tag (mismatches + indels)."""

    normalized_coverage: float = 0.0
    """Normalized coverage: (reads/windows) / mean_reads_per_window."""

    error_bar_width: float = 0.0
    """Error bar width: sqrt(reads)/windows / mean_reads_per_window."""


@dataclass(frozen=True, kw_only=True)
class GcbiasSummary:
    """The `.gcbias-summary.txt` table that `riker gcbias` writes."""

    sample: str = ""
    """Sample name derived from the BAM read group SM tag or filename."""

    window_size: int = 0
    """Sliding window size used for GC content calculation."""

    total_clusters: int = 0
    """Total clusters: first-of-pair or unpaired reads among `total_reads` (includes unmapped
    reads).
    """

    total_reads: int = 0
    """Total reads considered: every read except secondary and QC-fail (includes unmapped,
    duplicate, supplementary, and low-MAPQ reads).
    """

    aligned_reads: int = 0
    """Aligned reads: the mapped subset of `total_reads`."""

    filtered_reads: int = 0
    """Filtered reads: aligned reads not used in the GC bias computation (excluded as
    duplicate/supplementary, low MAPQ, in an excluded interval, or lacking a valid GC window).
    Equals `aligned_reads` minus the total binned read starts.
    """

    frac_filtered_reads: float = 0.0
    """Fraction of aligned reads that were filtered out of the GC bias computation (`filtered_reads
    / aligned_reads`).
    """

    at_dropout: float = 0.0
    """AT dropout: deficit at GC 0-50%."""

    gc_dropout: float = 0.0
    """GC dropout: deficit at GC 51-100%."""

    gc_0_19_normcov: float = 0.0
    """Aggregate normalized coverage for GC 0-19%."""

    gc_20_39_normcov: float = 0.0
    """Aggregate normalized coverage for GC 20-39%."""

    gc_40_59_normcov: float = 0.0
    """Aggregate normalized coverage for GC 40-59%."""

    gc_60_79_normcov: float = 0.0
    """Aggregate normalized coverage for GC 60-79%."""

    gc_80_100_normcov: float = 0.0
    """Aggregate normalized coverage for GC 80-100%."""


@dataclass(frozen=True, kw_only=True)
class WgsMetrics:
    """The `.wgs-metrics.txt` table that `riker wgs` writes."""

    sample: str = ""
    """Sample name derived from the BAM read group SM tag or filename."""

    genome_territory: int = 0
    """Number of non-N reference bases in the genome territory (or interval set)."""

    mean_coverage: float = 0.0
    """Mean coverage depth across all genome territory positions."""

    sd_coverage: float = 0.0
    """Standard deviation of coverage depth."""

    median_coverage: float = 0.0
    """Median coverage depth."""

    mad_coverage: float = 0.0
    """Median absolute deviation of coverage depth."""

    frac_excluded_mapq: float = 0.0
    """Fraction of bases excluded due to low mapping quality."""

    frac_excluded_dupe: float = 0.0
    """Fraction of bases excluded because the read was marked as a duplicate."""

    frac_excluded_unpaired: float = 0.0
    """Fraction of bases excluded because the read was unpaired or had an unmapped mate."""

    frac_excluded_baseq: float = 0.0
    """Fraction of bases excluded due to low base quality."""

    frac_excluded_overlap: float = 0.0
    """Fraction of bases excluded due to read-pair overlap (second occurrence of a read name)."""

    frac_excluded_capped: float = 0.0
    """Fraction of bases excluded because the coverage cap was exceeded."""

    frac_excluded_total: float = 0.0
    """Total fraction of bases excluded for any reason."""

    frac_bases_at_1x: float = 0.0
    """Fraction of genome territory positions with coverage ≥ 1×."""

    frac_bases_at_5x: float = 0.0
    """Fraction of genome territory positions with coverage ≥ 5×."""

    frac_bases_at_10x: float = 0.0
    """Fraction of genome territory positions with coverage ≥ 10×."""

    frac_bases_at_15x: float = 0.0
    """Fraction of genome territory positions with coverage ≥ 15×."""

    frac_bases_at_20x: float = 0.0
    """Fraction of genome territory positions with coverage ≥ 20×."""

    frac_bases_at_25x: float = 0.0
    """Fraction of genome territory positions with coverage ≥ 25×."""

    frac_bases_at_30x: float = 0.0
    """Fraction of genome territory positions with coverage ≥ 30×."""

    frac_bases_at_40x: float = 0.0
    """Fraction of genome territory positions with coverage ≥ 40×."""

    frac_bases_at_50x: float = 0.0
    """Fraction of genome territory positions with coverage ≥ 50×."""

    frac_bases_at_60x: float = 0.0
    """Fraction of genome territory positions with coverage ≥ 60×."""

    frac_bases_at_100x: float = 0.0
    """Fraction of genome territory positions with coverage ≥ 100×."""

    fold_80_base_penalty: float = 0.0
    """Mean coverage divided by the 20th-percentile coverage (80% of bases are at/above that level).
    """

    fold_90_base_penalty: float = 0.0
    """Mean coverage divided by the 10th-percentile coverage."""

    fold_95_base_penalty: float = 0.0
    """Mean coverage divided by the 5th-percentile coverage."""


@dataclass(frozen=True, kw_only=True)
class WgsCoverage:
    """The `.wgs-coverage.txt` table that `riker wgs` writes."""

    sample: str = ""
    """Sample name derived from the BAM read group SM tag or filename."""

    depth: int = 0
    """Coverage depth (number of reads covering a position)."""

    bases: int = 0
    """Number of reference positions with exactly this depth."""

    frac_bases: float = 0.0
    """Fraction of genome territory with exactly this depth."""

    bases_at_or_above: int = 0
    """Number of reference positions with depth ≥ this depth."""

    frac_bases_at_or_above: float = 0.0
    """Fraction of genome territory with depth ≥ this depth."""


@dataclass(frozen=True, kw_only=True)
class WgsCoverageColumns:
    """The columns of a `WgsCoverage`, one tuple per field."""

    sample: tuple[str, ...] = ()
    depth: tuple[int, ...] = ()
    bases: tuple[int, ...] = ()
    frac_bases: tuple[float, ...] = ()
    bases_at_or_above: tuple[int, ...] = ()
    frac_bases_at_or_above: tuple[float, ...] = ()


@dataclass(frozen=True, kw_only=True)
class HybcapMetrics:
    """The `.hybcap-metrics.txt` table that `riker hybcap` writes."""

    sample: str = ""
    """Sample name derived from the BAM read group SM tag or filename."""

    panel_name: str = ""
    """Name of the bait/target panel."""

    genome_size: int = 0
    """Total number of bases in the reference genome."""

    bait_territory: int = 0
    """Total number of unique bases covered by bait intervals."""

    target_territory: int = 0
    """Total number of unique bases covered by target intervals."""

    bait_design_efficiency: float = 0.0
    """Ratio of target territory to bait territory."""

    total_reads: int = 0
    """Total primary reads in the BAM file (excludes non-PF reads)."""

    deduped_reads: int = 0
    """Non-duplicate reads."""

    deduped_reads_aligned: int = 0
    """Non-duplicate aligned reads."""

    total_bases: int = 0
    """Total bases (read length × primary reads)."""

    bases_aligned: int = 0
    """Total aligned bases (from primary + supplementary)."""

    deduped_bases_aligned: int = 0
    """Non-duplicate aligned bases."""

    on_bait_bases: int = 0
    """Aligned bases falling on bait intervals (includes duplicates)."""

    near_bait_bases: int = 0
    """Aligned bases near but not on baits (includes duplicates)."""

    off_bait_bases: int = 0
    """Aligned bases not near any bait (includes duplicates)."""

    on_target_bases: int = 0
    """High-quality non-duplicate bases on target intervals."""

    on_target_bases_from_pairs: int = 0
    """High-quality non-duplicate bases on target from mapped pairs."""

    selected_pairs: int = 0
    """First-of-pair reads overlapping any bait (both ends mapped)."""

    selected_unique_pairs: int = 0
    """Same as selected_pairs but excluding duplicates."""

    frac_deduped_reads: float = 0.0
    """Fraction of total reads that are non-duplicate."""

    frac_deduped_reads_aligned: float = 0.0
    """Fraction of non-duplicate reads that are aligned."""

    frac_selected_bases: float = 0.0
    """Fraction of aligned bases that are on or near a bait."""

    frac_off_bait: float = 0.0
    """Fraction of aligned bases that are off-bait."""

    on_bait_vs_selected: float = 0.0
    """Fraction of selected bases that are strictly on (not near) bait."""

    mean_bait_coverage: float = 0.0
    """Mean coverage depth across bait bases (from aligned bases incl. duplicates)."""

    mean_target_coverage: float = 0.0
    """Mean coverage depth across target bases (from HQ non-dup bases)."""

    median_target_coverage: float = 0.0
    """Median per-base coverage depth across target bases."""

    max_target_coverage: int = 0
    """Maximum per-base coverage depth across target bases."""

    min_target_coverage: int = 0
    """Minimum per-base coverage depth across target bases."""

    frac_uncovered_targets: float = 0.0
    """Fraction of raw (pre-merge) targets with zero coverage."""

    fold_enrichment: float = 0.0
    """Fold enrichment of on-bait bases vs. random genomic distribution."""

    fold_80_base_penalty: float = 0.0
    """Mean / 20th-percentile coverage depth (uniformity penalty)."""

    frac_exc_dupe: float = 0.0
    """Fraction of aligned bases excluded because the read was a duplicate."""

    frac_exc_mapq: float = 0.0
    """Fraction of aligned bases excluded due to low mapping quality."""

    frac_exc_overlap: float = 0.0
    """Fraction of aligned bases excluded due to read-pair overlap clipping."""

    frac_exc_baseq: float = 0.0
    """Fraction of aligned bases excluded due to low base quality."""

    frac_exc_off_target: float = 0.0
    """Fraction of aligned bases excluded because they were off-target (but high quality)."""

    frac_target_bases_1x: float = 0.0
    """Fraction of target bases with coverage >= 1x."""

    frac_target_bases_10x: float = 0.0
    """Fraction of target bases with coverage >= 10x."""

    frac_target_bases_20x: float = 0.0
    """Fraction of target bases with coverage >= 20x."""

    frac_target_bases_30x: float = 0.0
    """Fraction of target bases with coverage >= 30x."""

    frac_target_bases_50x: float = 0.0
    """Fraction of target bases with coverage >= 50x."""

    frac_target_bases_100x: float = 0.0
    """Fraction of target bases with coverage >= 100x."""

    frac_target_bases_250x: float = 0.0
    """Fraction of target bases with coverage >= 250x."""

    frac_target_bases_500x: float = 0.0
    """Fraction of target bases with coverage >= 500x."""

    frac_target_bases_1000x: float = 0.0
    """Fraction of target bases with coverage >= 1000x."""

    at_dropout: float = 0.0
    """AT dropout: under-representation of AT-rich targets."""

    gc_dropout: float = 0.0
    """GC dropout: under-representation of GC-rich targets."""

    frac_usable_bases_on_bait: float = 0.0
    """Fraction of total bases that are on-bait (including duplicates in denominator)."""

    frac_usable_bases_on_target: float = 0.0
    """Fraction of total bases that are on-target (HQ, non-dup numerator, all bases denominator)."""

    hs_library_size: int | None = None
    """Estimated library size using Lander-Waterman model on selected pairs."""

    hs_penalty_10x: float = 0.0
    """Fold sequencing needed to reach 80% of targets at 10x."""

    hs_penalty_20x: float = 0.0
    """Fold sequencing needed to reach 80% of targets at 20x."""

    hs_penalty_30x: float = 0.0
    """Fold sequencing needed to reach 80% of targets at 30x."""

    hs_penalty_40x: float = 0.0
    """Fold sequencing needed to reach 80% of targets at 40x."""

    hs_penalty_50x: float = 0.0
    """Fold sequencing needed to reach 80% of targets at 50x."""

    hs_penalty_100x: float = 0.0
    """Fold sequencing needed to reach 80% of targets at 100x."""


@dataclass(frozen=True, kw_only=True)
class HybcapPerTarget:
    """The `.hybcap-per-target.txt` table that `riker hybcap` writes."""

    sample: str = ""
    """Sample name derived from the BAM read group SM tag or filename."""

    chrom: str = ""
    """Contig name."""

    start: int = 0
    """1-based start position."""

    end: int = 0
    """1-based inclusive end position."""

    length: int = 0
    """Interval length in bases."""

    name: str = ""
    """Interval name."""

    gc_frac: float = 0.0
    """GC fraction of the target region (0.0 if no reference provided)."""

    mean_coverage: float = 0.0
    """Mean high-quality coverage depth."""

    normalized_coverage: float = 0.0
    """Mean coverage normalized by overall mean target coverage."""

    min_coverage: int = 0
    """Minimum per-base coverage."""

    max_coverage: int = 0
    """Maximum per-base coverage."""

    frac_0x: float = 0.0
    """Fraction of bases with zero coverage."""

    read_count: int = 0
    """Number of reads overlapping this target."""


@dataclass(frozen=True, kw_only=True)
class HybcapPerBase:
    """The `.hybcap-per-base.txt` table that `riker hybcap` writes."""

    sample: str = ""
    """Sample name derived from the BAM read group SM tag or filename."""

    chrom: str = ""
    """Contig name."""

    pos: int = 0
    """1-based position."""

    target: str = ""
    """Name of the target interval containing this position."""

    coverage: int = 0
    """High-quality coverage depth at this position."""


@dataclass(frozen=True, kw_only=True)
class ErrorMismatch:
    """The `.error-mismatch.txt` table that `riker error` writes."""

    sample: str = ""
    """Sample name derived from the BAM read group SM tag or filename."""

    stratifier: str = ""
    """The stratification group (e.g. "read_num,cycle")."""

    covariate: str = ""
    """The covariate value(s) for this row."""

    total_bases: int = 0
    """Total bases passing quality and variant-site filters."""

    error_bases: int = 0
    """Number of bases mismatching the reference."""

    frac_error: float = 0.0
    """Fraction of bases that are errors (error_bases / total_bases)."""

    q_score: float = 0.0
    """Phred-scaled error rate: -10 * log10(error_rate)."""


@dataclass(frozen=True, kw_only=True)
class ErrorOverlap:
    """The `.error-overlap.txt` table that `riker error` writes."""

    sample: str = ""
    """Sample name derived from the BAM read group SM tag or filename."""

    stratifier: str = ""
    """The stratification group."""

    covariate: str = ""
    """The covariate value(s) for this row."""

    overlapping_read_bases: int = 0
    """Number of bases from reads overlapping their mate at this position."""

    bases_mismatching_ref_and_mate: int = 0
    """Bases where read disagrees with both reference and mate (mate agrees with ref). Likely
    sequencing errors.
    """

    bases_matching_mate_but_not_ref: int = 0
    """Bases where read and mate agree with each other but both disagree with reference. Likely
    pre-sequencing errors.
    """

    bases_in_three_way_disagreement: int = 0
    """Bases where read, mate, and reference all differ from each other."""

    q_mismatching_ref_and_mate: float = 0.0
    """Q-score for bases mismatching ref and mate (likely sequencing errors)."""

    q_matching_mate_but_not_ref: float = 0.0
    """Q-score for bases matching mate but not ref (likely pre-sequencing errors)."""

    q_three_way_disagreement: float = 0.0
    """Q-score for three-way disagreements."""


@dataclass(frozen=True, kw_only=True)
class ErrorIndel:
    """The `.error-indel.txt` table that `riker error` writes."""

    sample: str = ""
    """Sample name derived from the BAM read group SM tag or filename."""

    stratifier: str = ""
    """The stratification group."""

    covariate: str = ""
    """The covariate value(s) for this row."""

    total_bases: int = 0
    """Total bases considered (alignment-consuming bases)."""

    num_insertions: int = 0
    """Number of insertion events."""

    num_inserted_bases: int = 0
    """Total bases inserted across all insertion events."""

    num_deletions: int = 0
    """Number of deletion events."""

    num_deleted_bases: int = 0
    """Total bases deleted across all deletion events."""

    frac_indel_error: float = 0.0
    """Fraction of indel events relative to total bases."""

    q_score: float = 0.0
    """Phred-scaled indel error rate."""


@dataclass(frozen=True, kw_only=True)
class RnaMetrics:
    """The `.rna-metrics.txt` table that `riker rna` writes."""

    sample: str = ""
    """Sample name from the BAM read group SM tag, or the filename."""

    total_reads: int = 0
    """Every QC-passing read except secondary alignments, i.e. mapped, unmapped, and supplementary
    reads. The denominator for `bases`. Because supplementary alignments are counted here but not in
    `mapped_reads`, expect `total_reads` ≥ `mapped_reads` + `unmapped_reads`.
    """

    mapped_reads: int = 0
    """Mapped, non-secondary, non-supplementary reads, the "one record per read" count that is the
    denominator for `duplicate_rate` and all `frac_*_reads` genomic-origin fractions.
    """

    unmapped_reads: int = 0
    """Unmapped, non-secondary reads."""

    ignored_reads: int = 0
    """Reads on an --ignore-chrom contig. Counted in `bases`/`total_reads` but excluded from every
    other metric (Picard's IGNORE_SEQUENCE behavior).
    """

    duplicate_rate: float = 0.0
    """`duplicate-flagged mapped_reads / mapped_reads`. Always reported as an observed rate;
    duplicates are still *included* in every other metric unless `--exclude-duplicates` is set.
    """

    ribosomal_reads: int | None = None
    """Reads whose fragment overlaps a ribosomal interval by at least --rrna-fragment-fraction;
    these are tallied here and removed before the exonic/intronic/intergenic classification. Blank
    if no ribosomal source (gene-model biotype or --ribosomal-intervals) is available.
    """

    exonic_reads: int = 0
    """Reads with at least one aligned base in an exon of any gene. Equals `assigned_reads` (exonic
    to exactly one gene) + `ambiguous_reads` (exonic to more than one gene).
    """

    intronic_reads: int = 0
    """Reads contained within a gene's span but touching no exon (i.e. wholly intronic)."""

    intergenic_reads: int = 0
    """Reads overlapping no gene at all."""

    ambiguous_reads: int = 0
    """Reads with exon overlap in more than one gene. A subset of `exonic_reads`; these are *not*
    counted in `assigned_reads` and do not contribute to `genes_detected` or the biotype file.
    """

    assigned_reads: int = 0
    """Reads with exon overlap in exactly one gene, the "usable for quantification" set that feeds
    `genes_detected` and the per-biotype counts.
    """

    frac_ribosomal_reads: float | None = None
    """`ribosomal_reads / mapped_reads`. Blank if no ribosomal source."""

    frac_exonic_reads: float = 0.0
    """`exonic_reads / mapped_reads`. Under default filters, ribosomal + exonic + intronic +
    intergenic = mapped_reads.
    """

    frac_intronic_reads: float = 0.0
    """`intronic_reads / mapped_reads`."""

    frac_intergenic_reads: float = 0.0
    """`intergenic_reads / mapped_reads`."""

    frac_ambiguous_reads: float = 0.0
    """`ambiguous_reads / mapped_reads` (the ambiguous subset of `frac_exonic_reads`)."""

    genes_detected: int = 0
    """Number of distinct genes (by name, so a gene at disjoint loci counts once) with at least
    --genes-detected-min-reads uniquely-assigned reads. Scales with sequencing depth, so compare
    only across similarly-sequenced samples.
    """

    spliced_reads: int = 0
    """Reads with at least one splice, a CIGAR N (skip) gap of at least --junction-min-intron bp."""

    frac_spliced_reads: float = 0.0
    """`spliced_reads / mapped_reads`."""

    known_splice_obs: int = 0
    """Splice-junction *observations* (counted with read multiplicity: a junction seen in N reads
    adds N) whose intron matches an annotated junction (both splice sites annotated).
    """

    partial_splice_obs: int = 0
    """Splice-junction observations (with read multiplicity) where exactly one splice site is
    annotated (partially novel).
    """

    novel_splice_obs: int = 0
    """Splice-junction observations (with read multiplicity) where neither splice site is annotated.
    """

    known_juncs: int = 0
    """Distinct annotated junctions observed (each unique intron counted once, regardless of how
    many reads spanned it): contrast the `*_splice_obs` counts, which include multiplicity.
    """

    partial_juncs: int = 0
    """Distinct observed junctions with exactly one annotated splice site."""

    novel_juncs: int = 0
    """Distinct observed junctions with neither splice site annotated."""

    frac_known_juncs: float = 0.0
    """`known_juncs / (known + partial + novel distinct junctions)`: the annotated fraction of the
    junctions seen.
    """

    bases: int = 0
    """Total bases in QC-passing, non-secondary reads, including unmapped reads and soft-clips
    (Picard PF_BASES). A base-level total: distinct from the read-level `total_reads`.
    """

    aligned_bases: int = 0
    """Reference-aligned bases (CIGAR M/=/X) of mapped reads: excludes soft-clips and insertions
    (Picard PF_ALIGNED_BASES). The denominator for the `frac_*_bases` composition fractions.
    """

    ribosomal_bases: int | None = None
    """Aligned bases in fragments classified ribosomal. Blank if no ribosomal source. Note the
    base-level composition is independent of the read-level origin counts above: it tallies *bases*,
    and a single read can contribute bases to several categories.
    """

    coding_bases: int = 0
    """Aligned bases falling in coding (CDS) exon sequence."""

    utr_bases: int = 0
    """Aligned bases falling in UTR (non-coding exon) sequence."""

    intronic_bases: int = 0
    """Aligned bases falling within a gene span but outside any exon (intronic)."""

    intergenic_bases: int = 0
    """Aligned bases overlapping no gene."""

    frac_ribosomal_bases: float | None = None
    """`ribosomal_bases / aligned_bases`. Blank if no ribosomal source."""

    frac_coding_bases: float = 0.0
    """`coding_bases / aligned_bases`."""

    frac_utr_bases: float = 0.0
    """`utr_bases / aligned_bases`."""

    frac_intronic_bases: float = 0.0
    """`intronic_bases / aligned_bases`."""

    frac_intergenic_bases: float = 0.0
    """`intergenic_bases / aligned_bases`."""

    frac_mrna_bases: float = 0.0
    """`frac_coding_bases + frac_utr_bases`: the mRNA (exonic) fraction of aligned bases."""

    frac_usable_bases: float = 0.0
    """`(coding_bases + utr_bases) / bases`. Note the denominator is **all sequenced bases**
    (`bases`), not `aligned_bases` like the other `frac_*_bases`: this is intentional, matching
    Picard's PCT_USABLE_BASES (the usable-mRNA fraction of the whole sequencing run).
    """

    detected_strand: StrandSpec
    """Strandedness used for the strand metrics: `unstranded`, `forward`, or `reverse`. With
    --strand auto (the default) this is inferred from the observed R1/R2 transcript-strand counts.
    """

    correct_strand_reads: int = 0
    """Reads aligning on the strand expected under `detected_strand`. Always 0 when unstranded."""

    frac_correct_strand_reads: float = 0.0
    """`correct_strand_reads / (correct + incorrect)`. (The incorrect count is not emitted; it is
    `mapped exon-overlapping single-gene reads` minus `correct_strand_reads`.)
    """

    r1_tx_strand_reads: int = 0
    """Templates (counted from read 1 / unpaired reads, FR-enclosed within a single gene) whose
    geometry implies read 1 lies on the transcription strand. Used for strand auto-detection.
    """

    r2_tx_strand_reads: int = 0
    """Templates whose geometry implies read 2 lies on the transcription strand."""

    unexplained_reads: int = 0
    """Templates that overlapped a single gene's exons but whose transcription strand could not be
    inferred (not properly paired / not FR-enclosed in one gene).
    """

    frac_r1_tx_strand_reads: float = 0.0
    """`r1_tx_strand_reads / (r1_tx_strand_reads + r2_tx_strand_reads)`: the basis for strand
    auto-detection (≈0.5 unstranded, ≈1 forward, ≈0 reverse).
    """

    frac_r2_tx_strand_reads: float = 0.0
    """`r2_tx_strand_reads / (r1_tx_strand_reads + r2_tx_strand_reads)`."""

    median_cv_coverage: float = 0.0
    """Median across the top ~1000 expressed transcripts (one per gene, length ≥
    max(--minimum-length, 2×--end-bias-bases), mean coverage ≥ 1) of each transcript's coverage
    coefficient of variation (stddev/mean of per-base coverage). Lower = more even coverage.
    """

    median_5prime_bias: float = 0.0
    """Median, over the same transcripts, of mean coverage in the 5' end window (--end-bias-bases
    wide) divided by whole-transcript mean coverage. ~1 is unbiased; <1 indicates 5' loss.
    """

    median_3prime_bias: float = 0.0
    """As `median_5prime_bias` but for the 3' end window. >1 indicates 3' enrichment (e.g. from
    poly-A selection of degraded RNA).
    """

    median_5prime_to_3prime_bias: float = 0.0
    """Median ratio of 5'-window to 3'-window coverage. ~1 is balanced; far from 1 signals a 5'/3'
    coverage skew.
    """

    median_tin: float = 0.0
    """Median Transcript Integrity Number (0–100): `100·exp(−KL(coverage‖uniform))`, an
    entropy-based coverage-uniformity score (100 = perfectly even). Computed over one representative
    transcript per gene (length ≥ --minimum-length, mean coverage > --tin-min-coverage). TIN is
    **scale-invariant**: it reflects relative coverage *shape*, not depth, so a deeply-sequenced
    transcript with a localized low-coverage stretch still scores low. See ERRATA.md (rna) for the
    full formula and interpretation.
    """

    mean_tin: float = 0.0
    """Mean TIN over the same transcripts."""

    stddev_tin: float = 0.0
    """Standard deviation of TIN over the same transcripts."""

    tin_transcripts: int = 0
    """Number of transcripts (genes) contributing to the TIN statistics, after the length and
    mean-coverage gates.
    """


@dataclass(frozen=True, kw_only=True)
class RnaBiotype:
    """The `.rna-biotype.txt` table that `riker rna` writes."""

    sample: str = ""
    """Sample name."""

    biotype: str = ""
    """Gene biotype (e.g. protein_coding, rRNA, lincRNA). For refFlat (no biotype column) this is
    the inferred `protein_coding`/`noncoding` split from CDS presence; `unknown` only when no
    biotype could be determined.
    """

    reads: int = 0
    """Reads uniquely assigned to genes of this biotype."""

    frac_reads: float = 0.0
    """`reads / assigned_reads`."""


@dataclass(frozen=True, kw_only=True)
class RnaInsertSize:
    """The `.rna-insert-size.txt` table that `riker rna` writes."""

    sample: str = ""
    """Sample name."""

    pair_orientation: PairOrientation
    """Pair orientation (FR, RF, or TANDEM)."""

    read_pairs: int = 0
    """Number of read pairs contributing to this orientation."""

    mean_insert_size: float = 0.0
    """Mean transcript-space insert size after trimming outliers."""

    standard_deviation: float = 0.0
    """Standard deviation after trimming outliers."""

    median_insert_size: float = 0.0
    """Median transcript-space insert size."""

    median_absolute_deviation: float = 0.0
    """Median absolute deviation of insert size."""

    min_insert_size: int = 0
    """Smallest insert size observed."""

    max_insert_size: int = 0
    """Largest insert size observed."""


@dataclass(frozen=True, kw_only=True)
class RnaInsertSizeHistogram:
    """The `.rna-insert-size-histogram.txt` table that `riker rna` writes."""

    sample: str = ""
    """Sample name."""

    insert_size: int = 0
    """Insert size in transcript space (bp)."""

    fr_count: int = 0
    """FR pairs at this insert size."""

    rf_count: int = 0
    """RF pairs at this insert size."""

    tandem_count: int = 0
    """Tandem pairs at this insert size."""


@dataclass(frozen=True, kw_only=True)
class RnaInsertSizeHistogramColumns:
    """The columns of an `RnaInsertSizeHistogram`, one tuple per field."""

    sample: tuple[str, ...] = ()
    insert_size: tuple[int, ...] = ()
    fr_count: tuple[int, ...] = ()
    rf_count: tuple[int, ...] = ()
    tandem_count: tuple[int, ...] = ()
