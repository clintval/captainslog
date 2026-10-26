import re
from dataclasses import fields
from math import isnan
from pathlib import Path
from typing import Any
from typing import cast

import pytest
from typing_extensions import assert_type

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


def same_column(left: object, right: object) -> bool:
    """Whether two columns are equal, where NaN equals NaN."""
    if isinstance(left, tuple) and isinstance(right, tuple):
        lefts, rights = cast(tuple[object, ...], left), cast(tuple[object, ...], right)
        return len(lefts) == len(rights) and all(map(same_column, lefts, rights))
    if isinstance(left, float) and isinstance(right, float) and isnan(left):
        return isnan(right)
    return left == right


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
    for field in fields(kind):
        column = getattr(hist, field.name)
        if isinstance(column, dict):
            extras = [cast(dict[str, Any], getattr(row, field.name)) for row in rows]
            names = {name for extra in extras for name in extra}
            mapping = cast(dict[str, tuple[object, ...]], column)
            assert set(mapping) == names
            for name, values in mapping.items():
                assert same_column(values, tuple(getattr(row, field.name)[name] for row in rows))
        else:
            assert same_column(column, tuple(getattr(row, field.name) for row in rows))


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


def test_columns_refuses_rows_that_name_different_extra_columns() -> None:
    """Rows that name different extra columns cannot share columns."""
    rows = [
        InsertSizeHistogram(insert_size=1, counts={"a": 1}),
        InsertSizeHistogram(insert_size=2, counts={"b": 2}),
    ]
    message = "Every row must name the same extra columns!"
    with pytest.raises(ValueError, match=f"^{re.escape(message)}$"):
        _ = columns(rows)


def test_columns_refuses_rows_that_are_not_a_histogram() -> None:
    """Rows of a dataclass that is not a Picard histogram are refused, and by type checkers."""
    message = "NotHistogram is not a Picard histogram dataclass!"
    with pytest.raises(TypeError, match=f"^{re.escape(message)}$"):
        _ = columns([NotHistogram(insert_size=1)])  # type: ignore[list-item]  # pyright: ignore[reportArgumentType, reportCallIssue, reportUnknownVariableType]  # ty: ignore[no-matching-overload]
