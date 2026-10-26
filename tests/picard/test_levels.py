import pytest

from shipslog.picard import AccumulationLevel
from shipslog.picard import GcBiasDetailMetrics
from shipslog.picard import GcBiasSummaryMetrics
from shipslog.picard import HsMetrics
from shipslog.picard import PicardReader
from shipslog.picard import accumulation_level
from tests.picard import DATA


def test_accumulation_level_reads_the_level_from_the_blank_level_columns() -> None:
    """Accumulation level reads the level from the blank level columns."""
    assert accumulation_level(HsMetrics()) is AccumulationLevel.ALL_READS
    assert accumulation_level(HsMetrics(sample="s")) is AccumulationLevel.SAMPLE
    assert accumulation_level(HsMetrics(sample="s", library="l")) is AccumulationLevel.LIBRARY
    row = HsMetrics(sample="s", library="l", read_group="r")
    assert accumulation_level(row) is AccumulationLevel.READ_GROUP


def test_accumulation_level_of_gc_bias_reads_its_own_column() -> None:
    """Accumulation level of gc bias reads its own column."""
    path = DATA / "cmm.gc_bias.summary_metrics"
    rows = list(PicardReader.from_path[GcBiasSummaryMetrics](path))
    assert {accumulation_level(row) for row in rows} == set(AccumulationLevel)


def test_accumulation_level_of_gc_bias_detail_reads_its_own_column() -> None:
    """Accumulation level of gc bias detail reads its own column."""
    path = DATA / "cmm.gc_bias.detail_metrics"
    rows = list(PicardReader.from_path[GcBiasDetailMetrics](path))
    assert {accumulation_level(row) for row in rows} == set(AccumulationLevel)


def test_accumulation_level_of_a_subclass_of_gc_bias_reads_its_own_column() -> None:
    """Accumulation level of a subclass of gc bias reads its own column."""

    class Mine(GcBiasSummaryMetrics):
        """A user's subclass."""

    assert accumulation_level(Mine(accumulation_level="Library")) is AccumulationLevel.LIBRARY


def test_accumulation_level_refuses_an_unknown_level() -> None:
    """Accumulation level refuses an unknown level."""
    row = GcBiasSummaryMetrics(accumulation_level="Lane")
    with pytest.raises(ValueError, match=r"^Unknown accumulation level: 'Lane'!$"):
        _ = accumulation_level(row)


def test_accumulation_level_values_are_their_names() -> None:
    """Accumulation level values are their names."""
    assert [level.value for level in AccumulationLevel] == [
        level.name for level in AccumulationLevel
    ]
