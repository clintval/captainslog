import dataclasses
import json
from pathlib import Path
from typing import Any

from captainslog.fgbio import CountKind
from captainslog.fgbio import PairOrientation
from captainslog.fgbio import ReadType
from captainslog.fgbio import _metrics
from captainslog.fgbio._histograms import HISTOGRAMS
from captainslog.fgbio._reader import HEADERS
from captainslog.fgbio._scala import SCALA_NAMES

SCHEMA: dict[str, Any] = json.loads(
    (Path(__file__).parents[2] / "scripts" / "fgbio" / "fgbio-4.1.1.json").read_text()
)

DATACLASSES = [
    getattr(_metrics, name)
    for name in _metrics.__all__
    if dataclasses.is_dataclass(getattr(_metrics, name))
]


def test_every_fgbio_dataclass_is_frozen_and_keyword_only() -> None:
    """Every fgbio dataclass is frozen and takes its fields by keyword only."""
    assert len(DATACLASSES) == 23
    for kind in DATACLASSES:
        assert kind.__dataclass_params__.frozen, kind
        assert all(field.kw_only for field in dataclasses.fields(kind)), kind


def test_every_dataclass_has_the_columns_fgbio_writes_for_its_class() -> None:
    """Each dataclass's fields are the constructor parameters of its Scala class, in order."""
    columns = {
        metric["class"]: [field["name"] for field in metric["fields"]]
        for metric in SCHEMA["classes"]
    }
    assert set(SCALA_NAMES) == set(DATACLASSES)
    for kind, scala in SCALA_NAMES.items():
        assert [field.name for field in dataclasses.fields(kind)] == columns[scala], kind


def test_no_two_dataclasses_share_a_header() -> None:
    """Each dataclass, and each histogram fgbio writes line by line, has a header of its own."""
    assert len(HEADERS) == len(DATACLASSES) + len(HISTOGRAMS) == 27


def test_every_enumeration_holds_the_texts_fgbio_writes() -> None:
    """Each enumeration's values are the texts fgbio writes, in fgbio's order."""
    enums = SCHEMA["enums"]
    assert [kind.value for kind in CountKind] == enums["com.fulcrumgenomics.bam.CountKind"]
    assert [kind.value for kind in ReadType] == enums["com.fulcrumgenomics.bam.ReadType"]
    assert [kind.value for kind in PairOrientation] == enums[
        "htsjdk.samtools.SamPairUtil$PairOrientation"
    ]


def test_an_option_of_fgbio_is_none_by_default() -> None:
    """A field fgbio declares as an `Option` defaults to None, which fgbio writes as empty."""
    for kind, scala in SCALA_NAMES.items():
        fields = next(metric["fields"] for metric in SCHEMA["classes"] if metric["class"] == scala)
        for field, found in zip(fields, dataclasses.fields(kind), strict=True):
            assert (found.default is None) == field["type"].startswith("Option["), (kind, found)
