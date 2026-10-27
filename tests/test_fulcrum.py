import dataclasses
import math
from enum import StrEnum
from io import StringIO
from typing import Any
from typing import get_type_hints

import pytest

from captainslog import fgbio
from captainslog import fgumi
from captainslog._fulcrum import FULCRUM_FLOAT
from captainslog._fulcrum import by_header
from captainslog.fgbio._reader import HEADERS as FGBIO_HEADERS
from captainslog.fgumi._reader import HEADERS as FGUMI_HEADERS

# The files both tools write with one header, by the dataclass of each tool that reads them.
# fmt: off
SHARED: dict[type[Any], type[Any]] = {
    fgbio.ClippingMetrics: fgumi.ClippingMetrics,
    fgbio.ConsensusKvMetric: fgumi.ConsensusKvMetric,
    fgbio.ConsensusVariantReviewInfo: fgumi.ConsensusVariantReviewInfo,
    fgbio.DuplexFamilySizeMetric: fgumi.DuplexFamilySizeMetric,
    fgbio.DuplexUmiMetric: fgumi.DuplexUmiMetric,
    fgbio.DuplexYieldMetric: fgumi.DuplexYieldMetric,
    fgbio.FamilySizeMetric: fgumi.FamilySizeMetric,
    fgbio.TagFamilySizeMetric: fgumi.FamilySizeMetrics,
    fgbio.UmiCorrectionMetrics: fgumi.UmiCorrectionMetrics,
    fgbio.UmiGroupingMetric: fgumi.UmiGroupingMetrics,
    fgbio.UmiMetric: fgumi.UmiMetric,
}
# fmt: on


def kinds(record_type: type[Any]) -> dict[str, object]:
    """The type of each field of a dataclass, with an enumeration as the texts it holds."""
    hints = get_type_hints(record_type)
    return {
        name: [member.value for member in hint]
        if isinstance(hint, type) and issubclass(hint, StrEnum)
        else hint
        for name, hint in hints.items()
    }


def test_the_files_both_tools_write_have_one_header() -> None:
    """These are the files that fgbio and fgumi both write with one header, and no others."""
    shared = {
        FGBIO_HEADERS[header]: FGUMI_HEADERS[header]
        for header in set(FGBIO_HEADERS) & set(FGUMI_HEADERS)
    }
    assert shared == SHARED


@pytest.mark.parametrize("pair", SHARED.items(), ids=lambda pair: pair[0].__name__)
def test_the_files_both_tools_write_have_the_same_types(pair: tuple[type[Any], type[Any]]) -> None:
    """A file both tools write holds the same type in each column, whichever tool wrote it."""
    assert kinds(pair[0]) == kinds(pair[1])


@pytest.mark.parametrize(
    "value, text",
    [
        (math.nan, "NaN"),
        (math.inf, "Infinity"),
        (-math.inf, "-Infinity"),
        (0.0, "0"),
        (42.0, "42"),
        (-7.0, "-7"),
        (0.5, "0.5"),
        (0.136546, "0.136546"),
        (1.5e-6, "1.5e-6"),
    ],
)
def test_floats_are_written_as_fgbio_and_fgumi_read_them(value: float, text: str) -> None:
    """Non-finite floats are spelled as fgbio spells them, and whole numbers have no point."""
    assert FULCRUM_FLOAT.into_text(value) == text
    found = FULCRUM_FLOAT.from_text(text)
    assert math.isnan(found) if math.isnan(value) else found == value


@pytest.mark.parametrize("text", ["1.5E-6", "Infinity", "-Infinity", "NaN"])
def test_floats_are_read_as_fgbio_writes_them(text: str) -> None:
    """A small float in scientific notation, and the non-finite floats, are read."""
    assert isinstance(FULCRUM_FLOAT.from_text(text), float)


def test_a_file_of_either_tool_is_read_by_the_dataclass_of_the_other() -> None:
    """A row of a file both tools write reads the same through either tool's dataclass."""
    text = "family_size\tcount\tfraction\tfraction_gt_or_eq_family_size\n1\t5\t0.5\t1\n"
    [left] = fgbio.FgbioReader[fgbio.TagFamilySizeMetric](StringIO(text))
    [right] = fgumi.FgumiReader[fgumi.FamilySizeMetrics](StringIO(text))
    assert dataclasses.asdict(left) == dataclasses.asdict(right)


def test_two_dataclasses_with_one_header_are_refused() -> None:
    """A header that would name two dataclasses names neither."""

    @dataclasses.dataclass(frozen=True)
    class Left:
        count: int

    @dataclasses.dataclass(frozen=True)
    class Right:
        count: int

    with pytest.raises(ValueError, match="Left and Right share a header"):
        _ = by_header([Left, Right], "test")
