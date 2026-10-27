from pathlib import Path

import pytest

DATA = Path(__file__).parent / "data"

PICARD_COVERAGE = ["hs.per_base_coverage.txt", "hs.per_target_coverage.txt"]

PICARD_METRICS = [
    "cmm.alignment_summary_metrics.txt",
    "cmm.bait_bias_detail_metrics.txt",
    "cmm.bait_bias_summary_metrics.txt",
    "cmm.base_distribution_by_cycle_metrics.txt",
    "cmm.error_summary_metrics.txt",
    "cmm.gc_bias.detail_metrics.txt",
    "cmm.gc_bias.summary_metrics.txt",
    "cmm.insert_size_metrics.txt",
    "cmm.pre_adapter_detail_metrics.txt",
    "cmm.pre_adapter_summary_metrics.txt",
    "cmm.quality_by_cycle_metrics.txt",
    "cmm.quality_distribution_metrics.txt",
    "cmm.quality_yield_metrics.txt",
    "concordance.genotype_concordance_contingency_metrics.txt",
    "concordance.genotype_concordance_detail_metrics.txt",
    "concordance.genotype_concordance_summary_metrics.txt",
    "crosscheck.crosscheck_metrics.txt",
    "dup.duplication_metrics.txt",
    "elc.duplication_metrics.txt",
    "fingerprint.fingerprinting_detail_metrics.txt",
    "fingerprint.fingerprinting_summary_metrics.txt",
    "hs.hs_metrics.txt",
    "jump.jumping_metrics.txt",
    "nonzero.wgs_metrics.txt",
    "one_library.duplication_metrics.txt",
    "oxog.oxog_metrics.txt",
    "pcr.targeted_pcr_metrics.txt",
    "raw.raw_wgs_metrics.txt",
    "rna.rna_metrics.txt",
    "rrbs.rrbs_detail_metrics.txt",
    "rrbs.rrbs_summary_metrics.txt",
    "vc.variant_calling_detail_metrics.txt",
    "vc.variant_calling_summary_metrics.txt",
    "wgs.wgs_metrics.txt",
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


@pytest.mark.parametrize("name", RIKER)
def test_every_riker_fixture_holds_a_row_below_its_labels(name: str) -> None:
    """Every Riker fixture holds its label row and at least one row of data below it."""
    labels, *rows = (DATA / "riker" / name).read_text().splitlines()
    assert labels.startswith("sample\t")
    assert any(row.strip() for row in rows)


@pytest.mark.parametrize("name", picard_metrics_fixtures())
def test_every_picard_fixture_starts_with_picards_two_headers(name: str) -> None:
    """Every Picard metrics fixture opens with the command line and start time headers."""
    lines = (DATA / "picard" / name).read_text().splitlines()
    assert lines[0] == "## htsjdk.samtools.metrics.StringHeader"
    assert lines[1].startswith("# ")
    assert lines[2] == "## htsjdk.samtools.metrics.StringHeader"
    assert lines[3].startswith("# Started on: ")
