import json
import re
from dataclasses import fields
from dataclasses import is_dataclass
from pathlib import Path
from typing import Any
from typing import get_type_hints

import pytest

from captainslog import picard
from captainslog.picard import AlignmentSummaryMetrics
from captainslog.picard import Category
from captainslog.picard import GcBiasDetailMetrics
from captainslog.picard import GcBiasSummaryMetrics
from captainslog.picard import GenotypeConcordanceSummaryMetrics
from captainslog.picard import HsMetrics
from captainslog.picard import IndependentReplicateMetric
from captainslog.picard import PicardReader
from captainslog.picard import PicardWriter
from captainslog.picard import QualityYieldMetrics
from captainslog.picard import QualityYieldMetricsSnvq
from captainslog.picard import ReadsUsed
from captainslog.picard import VariantType
from captainslog.picard import _metrics
from captainslog.picard._java import COLUMN_LABELS
from captainslog.picard._java import JAVA_NAMES
from tests.picard import DATA
from tests.picard import METRICS_CLASS
from tests.picard import PICARD_METRICS_FIXTURES
from tests.picard import class_named_in

SCRIPTS = Path(__file__).parents[2] / "scripts" / "picard"

SCHEMA = SCRIPTS / "picard-3.5.0.json"

UNITS: dict[str, dict[str, str]] = json.loads((SCRIPTS / "units.json").read_text())

PICARD_UNIT = re.compile(r"(?<![^_])(?:PCT|PERCENT)(?![^_])")


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


def test_no_dataclass_is_named_for_a_class_no_picard_file_holds() -> None:
    """Base and collector classes that no Picard file holds have no dataclass of their own."""
    held_by_no_file = {
        "picard.analysis.directed.PanelMetricsBase",
        "picard.analysis.directed.TargetMetrics",
        "picard.analysis.directed.TargetMetricsBase",
        "picard.metrics.MultilevelMetrics",
        "picard.sam.SamErrorMetric.ErrorMetric",
    }
    assert held_by_no_file.isdisjoint(JAVA_NAMES.values())
    assert "Multilevel" in picard.__all__


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


def test_reads_used_is_an_enum_of_the_constants_picard_writes() -> None:
    """The reads used by GC bias metrics are all reads, or only those that are not duplicates."""
    assert [member.value for member in ReadsUsed] == ["ALL", "UNIQUE"]


@pytest.mark.parametrize(
    ("kind", "name"),
    [
        (GcBiasDetailMetrics, "cmm.gc_bias.detail_metrics"),
        (GcBiasSummaryMetrics, "cmm.gc_bias.summary_metrics"),
    ],
)
def test_gc_bias_reads_used_is_read_as_a_reads_used(kind: type[Any], name: str) -> None:
    """The reads used of both GC bias dataclasses is a `ReadsUsed`, and is read as one."""
    assert get_type_hints(kind)["reads_used"] is ReadsUsed
    rows = list(PicardReader.from_path[kind](DATA / name))
    assert rows
    assert all(type(row.reads_used) is ReadsUsed for row in rows)
    assert {row.reads_used for row in rows} == {ReadsUsed.ALL}


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


def test_column_labels_hold_only_mixed_case_java_names_and_renamed_fractions() -> None:
    """A label is a mixed-case Java name, or the `PCT` or `PERCENT` label of a `frac` field."""
    for kind, labels in COLUMN_LABELS.items():
        for name, label in labels.items():
            assert label != name.removesuffix("_").upper(), (kind, name)
            assert label != label.upper() or PICARD_UNIT.sub("FRAC", label) == name.upper(), name


def test_no_picard_fraction_field_is_named_pct() -> None:
    """A fraction is named `frac` in place of `pct`, and a field still named `pct` is not one."""
    schema = json.loads(SCHEMA.read_text())
    columns = {c["class"]: c["fields"] for c in schema["classes"]}
    for kind, java in JAVA_NAMES.items():
        for field, column in zip(fields(kind), columns[java], strict=True):
            unit = UNITS.get(f"{column['declared_by']}.{column['name']}", {}).get("unit")
            tokens = set(field.name.split("_"))
            if unit == "fraction":
                assert field.name.upper() == PICARD_UNIT.sub("FRAC", column["name"]), field.name
            elif not tokens.isdisjoint({"pct", "percent"}):
                assert unit in {"none", "percent", "unknown"}, (java, field.name)


def test_a_renamed_fraction_is_written_under_picards_column_label(tmp_path: Path) -> None:
    """A `frac` field is written and read back under Picard's own `PCT` column label."""
    path = tmp_path / "out.alignment_summary_metrics"
    row = AlignmentSummaryMetrics(category=Category.PAIR, frac_pf_reads_aligned=0.996951)
    with PicardWriter.from_path[AlignmentSummaryMetrics](path) as writer:
        writer.write(row)
    labels = next(line for line in path.read_text().splitlines() if line.startswith("CATEGORY"))
    assert "PCT_PF_READS_ALIGNED" in labels.split("\t")
    assert not any(label.startswith("FRAC") for label in labels.split("\t"))
    assert list(PicardReader.from_path[AlignmentSummaryMetrics](path)) == [row]


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
