from pathlib import Path

import pytest

DATA = Path(__file__).parent / "data"

PICARD_COVERAGE = ["hs.per_base_coverage.txt", "hs.per_target_coverage.txt"]

PICARD_METRICS = [
    "cmm.alignment_summary_metrics",
    "cmm.bait_bias_detail_metrics",
    "cmm.bait_bias_summary_metrics",
    "cmm.base_distribution_by_cycle_metrics",
    "cmm.error_summary_metrics",
    "cmm.gc_bias.detail_metrics",
    "cmm.gc_bias.summary_metrics",
    "cmm.insert_size_metrics",
    "cmm.pre_adapter_detail_metrics",
    "cmm.pre_adapter_summary_metrics",
    "cmm.quality_by_cycle_metrics",
    "cmm.quality_distribution_metrics",
    "cmm.quality_yield_metrics",
    "concordance.genotype_concordance_contingency_metrics",
    "concordance.genotype_concordance_detail_metrics",
    "concordance.genotype_concordance_summary_metrics",
    "crosscheck.crosscheck_metrics",
    "dup.duplication_metrics",
    "elc.duplication_metrics",
    "fingerprint.fingerprinting_detail_metrics",
    "fingerprint.fingerprinting_summary_metrics",
    "hs.hs_metrics",
    "jump.jumping_metrics",
    "nonzero.wgs_metrics",
    "one_library.duplication_metrics",
    "oxog.oxog_metrics",
    "pcr.targeted_pcr_metrics",
    "raw.raw_wgs_metrics",
    "rna.rna_metrics",
    "rrbs.rrbs_detail_metrics",
    "rrbs.rrbs_summary_metrics",
    "vc.variant_calling_detail_metrics",
    "vc.variant_calling_summary_metrics",
    "wgs.wgs_metrics",
]

RIKER = [
    "s.alignment-metrics.txt",
    "s.base-distribution-by-cycle.txt",
    "s.error-indel.txt",
    "s.error-mismatch.txt",
    "s.error-overlap.txt",
    "s.gcbias-detail.txt",
    "s.gcbias-summary.txt",
    "s.hybcap-metrics.txt",
    "s.hybcap-per-base.txt",
    "s.hybcap-per-target.txt",
    "s.isize-histogram.txt",
    "s.isize-metrics.txt",
    "s.mean-quality-by-cycle.txt",
    "s.quality-score-distribution.txt",
    "s.rna-biotype.txt",
    "s.rna-insert-size-histogram.txt",
    "s.rna-insert-size.txt",
    "s.rna-metrics.txt",
    "s.wgs-coverage.txt",
    "s.wgs-metrics.txt",
]

FIXTURES = [Path("picard", name) for name in PICARD_METRICS + PICARD_COVERAGE] + [
    Path("riker", name) for name in RIKER
]


def picard_metrics_fixtures() -> list[str]:
    """Every Picard fixture written by htsjdk's metrics writer, listed or not."""
    written = {path.name for path in (DATA / "picard").glob("*")}
    return sorted((written | set(PICARD_METRICS)) - set(PICARD_COVERAGE))


@pytest.mark.parametrize("fixture", FIXTURES, ids=str)
def test_every_required_fixture_exists(fixture: Path) -> None:
    """Every fixture exists and holds data."""
    path = DATA / fixture
    assert path.is_file()
    assert path.stat().st_size > 0


@pytest.mark.parametrize("name", picard_metrics_fixtures())
def test_every_picard_fixture_starts_with_picards_two_headers(name: str) -> None:
    """Every Picard metrics fixture opens with the command line and start time headers."""
    lines = (DATA / "picard" / name).read_text().splitlines()
    assert lines[0] == "## htsjdk.samtools.metrics.StringHeader"
    assert lines[1].startswith("# ")
    assert lines[2] == "## htsjdk.samtools.metrics.StringHeader"
    assert lines[3].startswith("# Started on: ")
