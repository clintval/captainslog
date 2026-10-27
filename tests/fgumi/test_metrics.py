import dataclasses
import json
from pathlib import Path
from typing import Any

from captainslog.fgumi import ReadType
from captainslog.fgumi import _metrics
from captainslog.fgumi._reader import HEADERS
from captainslog.fgumi._rust import MANIFEST_KEYS

MANIFEST: dict[str, Any] = json.loads(
    (Path(__file__).parents[2] / "scripts" / "fgumi" / "fgumi-0.8.0.json").read_text()
)

DATACLASSES = [
    getattr(_metrics, name)
    for name in _metrics.__all__
    if dataclasses.is_dataclass(getattr(_metrics, name))
]


def test_every_fgumi_dataclass_is_frozen_and_keyword_only() -> None:
    """Every fgumi dataclass is frozen and takes its fields by keyword only."""
    assert len(DATACLASSES) == 20
    for kind in DATACLASSES:
        assert kind.__dataclass_params__.frozen, kind
        assert all(field.kw_only for field in dataclasses.fields(kind)), kind


def test_every_file_of_the_contract_has_one_dataclass_with_its_columns() -> None:
    """Each file of fgumi's column contract is read by one dataclass with its columns."""
    assert MANIFEST["fgumi"] == "0.8.0"
    assert set(MANIFEST_KEYS) == set(DATACLASSES)
    keys = [key for found in MANIFEST_KEYS.values() for key in found]
    assert sorted(keys) == sorted(MANIFEST["files"])
    for kind, found in MANIFEST_KEYS.items():
        for key in found:
            assert [field.name for field in dataclasses.fields(kind)] == MANIFEST["files"][key], key


def test_no_two_dataclasses_share_a_header() -> None:
    """Each dataclass has a header of its own, so a header names one dataclass."""
    assert len(HEADERS) == len(DATACLASSES)


def test_read_types_are_fgumis() -> None:
    """The read types are the variants fgumi writes for its clipping metrics."""
    assert [kind.value for kind in ReadType] == ["Fragment", "ReadOne", "ReadTwo", "Pair", "All"]
