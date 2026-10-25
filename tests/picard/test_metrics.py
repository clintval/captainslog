import json
from dataclasses import fields
from dataclasses import is_dataclass
from pathlib import Path
from typing import Any
from typing import get_type_hints

import pytest

from captainslog.picard import AlignmentSummaryMetrics
from captainslog.picard import Category
from captainslog.picard import GenotypeConcordanceSummaryMetrics
from captainslog.picard import HsMetrics
from captainslog.picard import IndependentReplicateMetric
from captainslog.picard import QualityYieldMetrics
from captainslog.picard import QualityYieldMetricsSnvq
from captainslog.picard import VariantType
from captainslog.picard import _metrics
from captainslog.picard._java import COLUMN_LABELS
from captainslog.picard._java import JAVA_NAMES
from tests.picard import METRICS_CLASS
from tests.picard import PICARD_METRICS_FIXTURES
from tests.picard import class_named_in

SCHEMA = Path(__file__).parents[2] / "scripts" / "picard" / "picard-3.5.0.json"


def column_labels(kind: type[Any]) -> list[str]:
    """The column label of each field of a dataclass, in order."""
    labels = COLUMN_LABELS.get(kind, {})
    return [labels.get(f.name, f.name.removesuffix("_").upper()) for f in fields(kind)]


def test_every_picard_dataclass_is_frozen_keyword_only_and_named_in_java_names() -> None:
    """Every exported dataclass has a Java name, is frozen, and takes its fields by keyword only."""
    exported = {getattr(_metrics, name) for name in _metrics.__all__}
    assert {kind for kind in exported if is_dataclass(kind)} == set(JAVA_NAMES)
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


def test_htsjdks_variant_context_type_is_the_enum_variant_type() -> None:
    """The variant type columns hold htsjdk's VariantContext$Type, named VariantType."""
    assert get_type_hints(GenotypeConcordanceSummaryMetrics)["variant_type"] is VariantType
    assert [t.value for t in VariantType] == [
        "NO_VARIATION",
        "SNP",
        "MNP",
        "INDEL",
        "SYMBOLIC",
        "MIXED",
    ]


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


def test_camel_case_java_fields_are_snake_case_and_keep_their_column_labels() -> None:
    """A camelCase Java field becomes a snake_case field whose column label is the Java name."""
    first = fields(IndependentReplicateMetric)[0]
    assert first.name == "n_sites"
    assert COLUMN_LABELS[IndependentReplicateMetric][first.name] == "nSites"


def test_column_labels_hold_only_mixed_case_java_names() -> None:
    """An UPPER_SNAKE Java field keeps its name, so only mixed-case names need a column label."""
    for kind, labels in COLUMN_LABELS.items():
        for name, label in labels.items():
            assert label != name.removesuffix("_").upper(), (kind, name)
            assert label != label.upper(), (kind, name)


def test_every_dataclass_labels_its_columns_as_htsjdk_writes_them() -> None:
    """The column labels of every dataclass are its Java class's field names, in order."""
    schema = json.loads(SCHEMA.read_text())
    columns = {c["class"]: [f["name"] for f in c["fields"]] for c in schema["classes"]}
    for kind, java in JAVA_NAMES.items():
        assert column_labels(kind) == columns[java], java


@pytest.mark.parametrize("path", PICARD_METRICS_FIXTURES, ids=lambda path: path.name)
def test_every_fixture_names_the_columns_of_its_dataclass_in_order(path: Path) -> None:
    """The header row of every fixture is the column labels of its dataclass, in order."""
    lines = path.read_text().splitlines()
    index = next(i for i, line in enumerate(lines) if line.startswith(METRICS_CLASS))
    assert lines[index + 1] == "\t".join(column_labels(class_named_in(path)))
