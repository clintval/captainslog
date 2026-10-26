import dataclasses
from pathlib import Path
from types import UnionType
from typing import get_type_hints

import pytest

from captainslog.riker import Category
from captainslog.riker import HybcapMetrics
from captainslog.riker import PairOrientation
from captainslog.riker import RnaMetrics
from captainslog.riker import StrandSpec
from captainslog.riker import _metrics
from tests.riker import ALL_RIKER_FIXTURES
from tests.riker import CLASSES
from tests.riker import RIKER_FIXTURES
from tests.riker import riker_class_of

DATACLASSES = [
    getattr(_metrics, name)
    for name in _metrics.__all__
    if dataclasses.is_dataclass(getattr(_metrics, name))
]

ENUMS = (Category, PairOrientation, StrandSpec)


def test_every_riker_dataclass_is_frozen_and_keyword_only() -> None:
    """Every Riker dataclass is frozen and takes its fields by keyword only."""
    assert len(DATACLASSES) == 20
    for kind in DATACLASSES:
        params = kind.__dataclass_params__
        assert params.frozen, kind
        assert all(field.kw_only for field in dataclasses.fields(kind)), kind


@pytest.mark.parametrize("path", RIKER_FIXTURES, ids=lambda path: path.name)
def test_every_fixture_names_the_columns_of_its_dataclass_in_order(path: Path) -> None:
    """A fixture's header is the field names of its dataclass, in order."""
    names = [field.name for field in dataclasses.fields(riker_class_of(path))]
    assert path.read_text().splitlines()[0] == "\t".join(names)


def test_every_fixture_suffix_has_exactly_one_dataclass() -> None:
    """Each fixture suffix maps to one distinct dataclass, and each dataclass is mapped."""
    assert len(CLASSES) == 20
    assert len(set(CLASSES.values())) == 20
    assert set(CLASSES.values()) == set(DATACLASSES)
    suffixes = {path.stem.split(".", 1)[1] for path in ALL_RIKER_FIXTURES}
    assert suffixes == set(CLASSES)


def test_alignment_categories_are_rikers() -> None:
    """The alignment categories are the ones Riker writes."""
    assert [c.value for c in Category] == ["read1", "read2", "pair"]


def test_pair_orientations_are_rikers() -> None:
    """The pair orientations are the ones Riker writes."""
    assert [o.value for o in PairOrientation] == ["FR", "RF", "TANDEM"]


def test_strands_are_rikers() -> None:
    """The strands are the ones Riker writes once it resolves auto."""
    assert [s.value for s in StrandSpec] == ["unstranded", "forward", "reverse"]


def test_optional_fields_default_to_none() -> None:
    """The columns Riker leaves blank are optional and default to None."""
    optional = {
        HybcapMetrics: ["hs_library_size"],
        RnaMetrics: [
            "ribosomal_reads",
            "frac_ribosomal_reads",
            "ribosomal_bases",
            "frac_ribosomal_bases",
        ],
    }
    for kind, names in optional.items():
        fields = {field.name: field for field in dataclasses.fields(kind)}
        hints = get_type_hints(kind)
        for name in names:
            assert fields[name].default is None
            assert isinstance(hints[name], UnionType)
            assert type(None) in hints[name].__args__


def test_every_field_type_is_one_riker_writes() -> None:
    """Every field is an int, a float, a str, an optional number, or a Riker enum."""
    allowed = {int, float, str, int | None, float | None, *ENUMS}
    for kind in DATACLASSES:
        for name, hint in get_type_hints(kind).items():
            assert hint in allowed, (kind, name, hint)
