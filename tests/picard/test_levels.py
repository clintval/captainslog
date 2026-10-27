import pytest

from captainslog.picard import AccumulationLevel
from captainslog.picard import GcBiasDetailMetrics
from captainslog.picard import GcBiasSummaryMetrics
from captainslog.picard import HsMetrics
from captainslog.picard import PicardReader
from captainslog.picard import ReadsUsed
from captainslog.picard import accumulation_level
from tests.picard import DATA


def test_accumulation_level_reads_the_level_from_the_blank_level_columns() -> None:
    """The level is read from which of the sample, library, and read group columns are blank."""
    assert accumulation_level(HsMetrics()) is AccumulationLevel.ALL_READS
    assert accumulation_level(HsMetrics(sample="s")) is AccumulationLevel.SAMPLE
    assert accumulation_level(HsMetrics(sample="s", library="l")) is AccumulationLevel.LIBRARY
    row = HsMetrics(sample="s", library="l", read_group="r")
    assert accumulation_level(row) is AccumulationLevel.READ_GROUP


def test_accumulation_level_of_gc_bias_reads_its_own_column() -> None:
    """A GC bias summary row gives the level from its own `accumulation_level` column."""
    path = DATA / "cmm.gc_bias.summary_metrics"
    rows = list(PicardReader.from_path[GcBiasSummaryMetrics](path))
    assert {accumulation_level(row) for row in rows} == set(AccumulationLevel)


def test_accumulation_level_of_gc_bias_detail_reads_its_own_column() -> None:
    """A GC bias detail row gives the level from its own `accumulation_level` column."""
    path = DATA / "cmm.gc_bias.detail_metrics"
    rows = list(PicardReader.from_path[GcBiasDetailMetrics](path))
    assert {accumulation_level(row) for row in rows} == set(AccumulationLevel)


def test_accumulation_level_of_a_subclass_of_gc_bias_reads_its_own_column() -> None:
    """A subclass of a GC bias dataclass gives the level from its `accumulation_level` column."""

    class Mine(GcBiasSummaryMetrics):
        """A user's subclass."""

    row = Mine(accumulation_level="Library", reads_used=ReadsUsed.ALL)
    assert accumulation_level(row) is AccumulationLevel.LIBRARY


def test_accumulation_level_refuses_an_unknown_level() -> None:
    """An `accumulation_level` column holding an unknown level is refused, naming the level."""
    row = GcBiasSummaryMetrics(accumulation_level="Lane", reads_used=ReadsUsed.ALL)
    with pytest.raises(ValueError, match=r"^Unknown accumulation level: 'Lane'!$"):
        _ = accumulation_level(row)


def test_accumulation_level_values_are_their_names() -> None:
    """Each level has its own name as its value."""
    assert [level.value for level in AccumulationLevel] == [
        level.name for level in AccumulationLevel
    ]
