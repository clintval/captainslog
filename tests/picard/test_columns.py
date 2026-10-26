import re
from dataclasses import dataclass
from dataclasses import fields
from pathlib import Path
from typing import Any
from typing import ClassVar
from typing import cast

import pytest
from typing_extensions import assert_type

from captainslog._columns import transpose
from captainslog.picard import InsertSizeHistogram
from captainslog.picard import InsertSizeHistogramColumns
from captainslog.picard import PicardHistogramReader
from captainslog.picard import SamComparisonHistogram
from captainslog.picard import SamComparisonHistogramColumns
from captainslog.picard import columns
from captainslog.picard._histograms import HISTOGRAMS
from tests.picard import FIXTURE_CLASSES
from tests.picard import PICARD_HISTOGRAM_FIXTURES
from tests.picard import DerivedHistogram
from tests.picard import NotHistogram


def test_columns_transposes_the_insert_size_histogram() -> None:
    """The fixed field becomes a tuple, and the extra columns a dict of tuples by name."""
    rows = [
        InsertSizeHistogram(insert_size=1, counts={"All_Reads.fr_count": 0}),
        InsertSizeHistogram(insert_size=2, counts={"All_Reads.fr_count": 4}),
    ]
    hist = columns(rows)
    _ = assert_type(hist, InsertSizeHistogramColumns)
    assert hist.insert_size == (1, 2)
    assert hist.counts == {"All_Reads.fr_count": (0, 4)}


@pytest.mark.parametrize("path", PICARD_HISTOGRAM_FIXTURES, ids=lambda path: path.name)
def test_columns_transposes_every_histogram_fixture(path: Path) -> None:
    """Each fixture's rows transpose into the columns class of its histogram."""
    kind = FIXTURE_CLASSES[path.name]
    with PicardHistogramReader.from_path[kind](path) as reader:
        rows = list(reader)
    hist: Any = columns(rows)
    assert type(hist) is HISTOGRAMS[kind].columns
    expected: dict[str, object] = {}
    for field in fields(kind):
        values = [getattr(row, field.name) for row in rows]
        if isinstance(values[0], dict):
            extras = cast(list[dict[str, Any]], values)
            expected[field.name] = {
                name: tuple(extra[name] for extra in extras) for name in extras[0]
            }
        else:
            expected[field.name] = tuple(values)
    assert hist == HISTOGRAMS[kind].columns(**expected)


def test_columns_transposes_a_histogram_without_extra_columns() -> None:
    """A histogram with only fixed fields has a tuple per field."""
    rows = [SamComparisonHistogram(bin="a", value=1), SamComparisonHistogram(bin="b", value=2)]
    hist = columns(rows)
    _ = assert_type(hist, SamComparisonHistogramColumns)
    assert hist == SamComparisonHistogramColumns(bin=("a", "b"), value=(1, 2))


def test_columns_transposes_a_single_row() -> None:
    """A single fixed field, and a single extra column, still become tuples."""
    hist = columns([InsertSizeHistogram(insert_size=7, counts={"All_Reads.fr_count": 3})])
    assert hist.insert_size == (7,)
    assert hist.counts == {"All_Reads.fr_count": (3,)}


def test_columns_transposes_rows_of_a_subclass() -> None:
    """Rows of a user's subclass give the columns of the histogram they extend."""
    hist = columns([DerivedHistogram(insert_size=1, counts={"All_Reads.fr_count": 5})])
    _ = assert_type(hist, InsertSizeHistogramColumns)
    assert type(hist) is InsertSizeHistogramColumns
    assert hist.counts == {"All_Reads.fr_count": (5,)}


def test_columns_accepts_extra_columns_named_in_another_order() -> None:
    """Rows may name the same extra columns in different orders; the first row's order wins."""
    rows = [
        InsertSizeHistogram(insert_size=1, counts={"a": 1, "b": 2}),
        InsertSizeHistogram(insert_size=2, counts={"b": 4, "a": 3}),
    ]
    hist = columns(rows)
    assert list(hist.counts) == ["a", "b"]
    assert hist.counts == {"a": (1, 3), "b": (2, 4)}


def test_columns_refuses_no_rows() -> None:
    """Without a row there is no type to choose the columns by."""
    message = "columns needs at least one row, to know their type!"
    with pytest.raises(ValueError, match=f"^{re.escape(message)}$"):
        _ = columns(cast(list[InsertSizeHistogram], []))


@pytest.mark.parametrize(
    ("first", "second"),
    [({"a": 1}, {"b": 2}), ({"a": 1}, {"a": 1, "b": 2}), ({"a": 1, "b": 2}, {"a": 1})],
    ids=["disjoint", "superset", "subset"],
)
def test_columns_refuses_rows_that_name_different_extra_columns(
    first: dict[str, int], second: dict[str, int]
) -> None:
    """Rows that name different extra columns cannot share columns."""
    rows = [
        InsertSizeHistogram(insert_size=1, counts=first),
        InsertSizeHistogram(insert_size=2, counts=second),
    ]
    message = "Every row must name the same extra columns!"
    with pytest.raises(ValueError, match=f"^{re.escape(message)}$"):
        _ = columns(rows)


def test_transpose_leaves_out_annotations_that_are_not_fields() -> None:
    """A class variable of the columns dataclass is not a column."""

    @dataclass(frozen=True, kw_only=True)
    class Pairs:
        """Columns with a class variable."""

        unit: ClassVar[str] = "bp"
        left: tuple[int, ...] = ()

    @dataclass(frozen=True)
    class Row:
        """A row."""

        left: int

    assert transpose([Row(left=1), Row(left=2)], Pairs) == Pairs(left=(1, 2))


def test_columns_refuses_rows_that_are_not_a_histogram() -> None:
    """Rows of a dataclass that is not a Picard histogram are refused, and by type checkers."""
    message = "NotHistogram is not a Picard histogram dataclass!"
    with pytest.raises(TypeError, match=f"^{re.escape(message)}$"):
        _ = columns([NotHistogram(insert_size=1)])  # type: ignore[list-item]  # pyright: ignore[reportArgumentType, reportCallIssue, reportUnknownVariableType]  # ty: ignore[no-matching-overload]
