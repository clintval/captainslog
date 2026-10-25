from math import isnan

from captainslog.picard import IndependentReplicateMetric
from captainslog.picard import QualityYieldMetrics
from captainslog.picard._format import PICARD_CODECS
from captainslog.picard._format import picard_rename


def test_picard_codecs_read_and_write_booleans_and_floats_as_picard_does() -> None:
    """Picard writes booleans as `Y` and `N`, NaN and infinity as `?`, and minus infinity `-?`."""
    assert PICARD_CODECS[bool].from_text("Y") is True
    assert PICARD_CODECS[bool].into_text(False) == "N"
    assert isnan(PICARD_CODECS[float].from_text("?"))
    assert PICARD_CODECS[float].into_text(float("inf")) == "?"
    assert PICARD_CODECS[float].into_text(float("-inf")) == "-?"


def test_picard_rename_upper_cases_each_field() -> None:
    """A field's column is its name in upper case."""
    assert picard_rename(QualityYieldMetrics)["total_reads"] == "TOTAL_READS"


def test_picard_rename_keeps_the_java_label_of_a_camel_case_field() -> None:
    """A field whose Java label is not its name in upper case keeps that label."""
    assert picard_rename(IndependentReplicateMetric)["n_sites"] == "nSites"


def test_picard_rename_gives_a_subclass_the_columns_of_its_picard_dataclass() -> None:
    """A subclass of a Picard dataclass that adds only a property has its parent's columns."""

    class Yield(QualityYieldMetrics):
        @property
        def pf_fraction(self) -> float:
            return self.pf_reads / self.total_reads

    class Replicate(IndependentReplicateMetric):
        @property
        def sites(self) -> int | None:
            return self.n_sites

    assert picard_rename(Yield) == picard_rename(QualityYieldMetrics)
    assert picard_rename(Replicate) == picard_rename(IndependentReplicateMetric)
    assert picard_rename(Replicate)["n_sites"] == "nSites"
