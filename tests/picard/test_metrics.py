from dataclasses import fields
from pathlib import Path
from typing import get_type_hints

import pytest

from captainslog.picard import AlignmentSummaryMetrics
from captainslog.picard import Category
from captainslog.picard import HsMetrics
from captainslog.picard import QualityYieldMetrics
from captainslog.picard import QualityYieldMetricsSnvq
from captainslog.picard._java import JAVA_NAMES
from tests.picard import METRICS_CLASS
from tests.picard import PICARD_METRICS_FIXTURES
from tests.picard import class_named_in


def test_every_picard_dataclass_is_frozen_keyword_only_and_named_in_java_names() -> None:
    """Every dataclass in JAVA_NAMES is frozen and takes its fields by keyword only."""
    for kind in JAVA_NAMES:
        assert kind.__dataclass_params__.frozen, kind
        assert all(field.kw_only is True for field in fields(kind)), kind


def test_java_names_are_unique() -> None:
    """No two dataclasses share a Java name."""
    assert len(set(JAVA_NAMES.values())) == len(JAVA_NAMES)


def test_multilevel_dataclasses_end_with_their_levels() -> None:
    """A multilevel dataclass ends with its level fields, which default to None."""
    assert [f.name for f in fields(HsMetrics)][-3:] == ["sample", "library", "read_group"]
    assert HsMetrics().sample is None


def test_alignment_summary_metrics_category_is_an_enum_of_its_java_constants() -> None:
    """The category of the alignment summary metrics is an enum of its Java constants."""
    assert {c.value for c in Category} == {"UNPAIRED", "FIRST_OF_PAIR", "SECOND_OF_PAIR", "PAIR"}
    assert get_type_hints(AlignmentSummaryMetrics)["category"] is Category


def test_quality_yield_metrics_from_both_tools_have_distinct_names() -> None:
    """The two Java classes named QualityYieldMetrics become two dataclasses."""
    assert (
        JAVA_NAMES[QualityYieldMetrics]
        == "picard.analysis.CollectQualityYieldMetrics$QualityYieldMetrics"
    )
    assert (
        JAVA_NAMES[QualityYieldMetricsSnvq]
        == "picard.analysis.CollectQualityYieldMetricsSNVQ$QualityYieldMetrics"
    )


@pytest.mark.parametrize("path", PICARD_METRICS_FIXTURES, ids=str)
def test_every_fixture_names_the_columns_of_its_dataclass_in_order(path: Path) -> None:
    """The header row of every fixture is the fields of its dataclass, in order."""
    lines = path.read_text().splitlines()
    index = next(i for i, line in enumerate(lines) if line.startswith(METRICS_CLASS))
    columns = [f.name.removesuffix("_").upper() for f in fields(class_named_in(path))]
    assert lines[index + 1] == "\t".join(columns)
