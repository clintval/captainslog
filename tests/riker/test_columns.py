import re
from dataclasses import fields
from pathlib import Path
from types import GenericAlias
from typing import Any
from typing import cast
from typing import get_type_hints

import pytest
from typing_extensions import assert_type

from captainslog.riker import AlignmentMetrics
from captainslog.riker import Category
from captainslog.riker import IsizeHistogram
from captainslog.riker import IsizeHistogramColumns
from captainslog.riker import RikerReader
from captainslog.riker import _metrics
from captainslog.riker import columns
from captainslog.riker._columns import HISTOGRAMS
from tests.riker import RIKER_FIXTURES
from tests.riker import riker_class_of

HISTOGRAM_FIXTURES = [path for path in RIKER_FIXTURES if riker_class_of(path) in HISTOGRAMS]


class DerivedIsize(IsizeHistogram):
    """A user's subclass of a Riker histogram that derives a count."""

    @property
    def pairs(self) -> int:
        """The number of pairs of the insert size, over all orientations."""
        return self.fr_count + self.rf_count + self.tandem_count


def test_columns_transposes_the_isize_histogram() -> None:
    """Each field of the rows becomes a tuple."""
    rows = [
        IsizeHistogram(sample="a", insert_size=1, fr_count=0),
        IsizeHistogram(sample="a", insert_size=2, fr_count=4),
    ]
    hist = columns(rows)
    _ = assert_type(hist, IsizeHistogramColumns)
    assert hist.sample == ("a", "a")
    assert hist.insert_size == (1, 2)
    assert hist.fr_count == (0, 4)


def test_columns_has_five_fixtures() -> None:
    """Every Riker histogram has a fixture to transpose."""
    assert {riker_class_of(path) for path in HISTOGRAM_FIXTURES} == set(HISTOGRAMS)


@pytest.mark.parametrize("path", HISTOGRAM_FIXTURES, ids=lambda path: path.name)
def test_columns_transposes_each_histogram_fixture(path: Path) -> None:
    """Each fixture's rows transpose into the columns class of its histogram."""
    kind = riker_class_of(path)
    with RikerReader.from_path[kind](path) as reader:
        rows = list(reader)
    hist: Any = columns(rows)
    assert type(hist) is HISTOGRAMS[kind]
    expected = {
        field.name: tuple(getattr(row, field.name) for row in rows) for field in fields(kind)
    }
    assert hist == HISTOGRAMS[kind](**expected)


def test_columns_transposes_rows_of_a_subclass() -> None:
    """Rows of a user's subclass give the columns of the histogram they extend."""
    hist = columns([DerivedIsize(sample="a", insert_size=1, fr_count=5)])
    _ = assert_type(hist, IsizeHistogramColumns)
    assert type(hist) is IsizeHistogramColumns
    assert hist.fr_count == (5,)


def test_columns_transposes_a_single_row() -> None:
    """A single row still becomes a tuple per field."""
    hist = columns([IsizeHistogram(sample="a", insert_size=7)])
    assert hist.insert_size == (7,)
    assert hist.sample == ("a",)


def test_columns_refuses_no_rows() -> None:
    """Without a row there is no type to choose the columns by."""
    message = "columns needs at least one row, to know their type!"
    with pytest.raises(ValueError, match=f"^{re.escape(message)}$"):
        _ = columns(cast(list[IsizeHistogram], []))


def test_columns_refuses_a_row_that_is_not_a_histogram() -> None:
    """Rows of a dataclass that is not a Riker histogram are refused, and by type checkers."""
    message = "AlignmentMetrics is not a Riker histogram dataclass!"
    with pytest.raises(TypeError, match=f"^{re.escape(message)}$"):
        _ = columns([AlignmentMetrics(category=Category.READ1)])  # type: ignore[list-item]  # pyright: ignore[reportArgumentType, reportCallIssue, reportUnknownVariableType]  # ty: ignore[no-matching-overload]


def test_registry_describes_each_riker_histogram() -> None:
    """Each registered row class maps to a frozen, keyword-only dataclass of tuples."""
    assert {kind.__name__ for kind in HISTOGRAMS} == {
        "IsizeHistogram",
        "MeanQualityByCycle",
        "QualityScoreDistribution",
        "RnaInsertSizeHistogram",
        "WgsCoverage",
    }
    exported = {getattr(_metrics, name) for name in _metrics.__all__ if name.endswith("Columns")}
    assert exported == set(HISTOGRAMS.values())
    for kind, histogram in HISTOGRAMS.items():
        assert histogram.__dataclass_params__.frozen, histogram
        assert all(f.kw_only is True for f in fields(histogram)), histogram
        names = [f.name for f in fields(kind)]
        assert [f.name for f in fields(histogram)] == names, histogram
        row_hints = get_type_hints(kind)
        hints = get_type_hints(histogram)
        for name in names:
            assert hints[name] == GenericAlias(tuple, (row_hints[name], ...)), (histogram, name)
