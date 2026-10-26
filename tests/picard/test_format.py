import re
from collections.abc import Mapping
from math import isnan
from pathlib import Path
from typing import Any
from typing import get_origin
from typing import get_type_hints

import pytest

from shipslog.picard import HsMetrics
from shipslog.picard import IndependentReplicateMetric
from shipslog.picard import InsertSizeMetrics
from shipslog.picard import MeanQualityByCycle
from shipslog.picard import PerTargetCoverage
from shipslog.picard import PicardCoverageReader
from shipslog.picard import PicardCoverageWriter
from shipslog.picard import PicardHistogramReader
from shipslog.picard import PicardReader
from shipslog.picard import QualityYieldMetrics
from shipslog.picard import RnaCoverageHistogram
from shipslog.picard._coverage import coverage_rename
from shipslog.picard._format import PICARD_CODECS
from shipslog.picard._format import picard_rename
from shipslog.picard._histograms import HISTOGRAMS
from tests.compare import same
from tests.picard import DATA
from tests.picard import HISTOGRAM
from tests.picard import METRICS_CLASS

FLOATS: tuple[Any, ...] = (float, float | None, dict[str, float])


def label_row(path: Path, marker: str) -> int:
    """The index of the label row after the first line of a file that starts with a marker."""
    lines = path.read_text().split("\n")
    return next(index for index, line in enumerate(lines) if line.startswith(marker)) + 1


def with_decimal_commas(path: Path, at: int, kind: type[Any], rename: Mapping[str, str]) -> str:
    """The text of a file whose table, from its label row at `at`, writes floats with a comma.

    The table runs to its first blank line. A column no field is named for holds an extra column.
    """
    lines = path.read_text().split("\n")
    hints = get_type_hints(kind)
    types = {rename.get(name, name): hint for name, hint in hints.items()}
    extra = next((hint for hint in hints.values() if get_origin(hint) is dict), None)
    floats = [types.get(label, extra) in FLOATS for label in lines[at].split("\t")]
    stop = next((n for n in range(at + 1, len(lines)) if not lines[n].strip()), len(lines))
    for index in range(at + 1, stop):
        cells = lines[index].split("\t")
        lines[index] = "\t".join(
            cell.replace(".", ",") if is_float else cell
            for cell, is_float in zip(cells, floats, strict=True)
        )
    return "\n".join(lines)


def test_picard_codecs_read_and_write_booleans_and_floats_as_picard_does() -> None:
    """Picard writes booleans as `Y` and `N`, NaN and infinity as `?`, and minus infinity `-?`."""
    assert PICARD_CODECS[bool].from_text("Y") is True
    assert PICARD_CODECS[bool].into_text(False) == "N"
    assert isnan(PICARD_CODECS[float].from_text("?"))
    assert PICARD_CODECS[float].from_text("-?") == float("-inf")
    assert PICARD_CODECS[float].into_text(float("inf")) == "?"
    assert PICARD_CODECS[float].into_text(float("-inf")) == "-?"
    assert isnan(PICARD_CODECS[float].from_text(PICARD_CODECS[float].into_text(float("nan"))))


def test_picard_float_codec_reads_a_decimal_comma_and_writes_a_decimal_point() -> None:
    """A float Picard wrote under a German or French locale reads as it would with a point."""
    assert PICARD_CODECS[float].from_text("0,983183") == 0.983183
    assert PICARD_CODECS[float].from_text("-12,5") == -12.5
    assert PICARD_CODECS[float].from_text("70.54") == 70.54
    assert PICARD_CODECS[float].from_text("1") == 1.0
    assert PICARD_CODECS[float].into_text(0.983183) == "0.983183"
    assert PICARD_CODECS[float].into_text(1e-7) == "1e-7"


@pytest.mark.parametrize(
    "text",
    [
        "",
        "many",
        "1,2,3",
        "1.5,2",
        "1_000",
        "NaN",
        "nan",
        "Infinity",
        "inf",
        " 1.5 ",
        "1.",
        ".5",
        "+1",
    ],
    ids=repr,
)
def test_picard_float_codec_refuses_text_that_is_not_a_float(text: str) -> None:
    """Text that is not a float, with a decimal point or a comma, is refused as it is."""
    message = f"Expected a float but found '{text}'!"
    with pytest.raises(ValueError, match=f"^{re.escape(message)}$"):
        _ = PICARD_CODECS[float].from_text(text)


@pytest.mark.parametrize(
    ("text", "value"),
    [("1,5", 1.5), ("-2.5e-3", -0.0025), ("1e-7", 1e-7), ("1,5E+3", 1500.0), ("-0", 0.0)],
    ids=repr,
)
def test_picard_float_codec_reads_numbers_as_typeline_does(text: str, value: float) -> None:
    """A float of digits, a decimal point or comma, and an exponent is read."""
    assert PICARD_CODECS[float].from_text(text) == value


@pytest.mark.parametrize(
    ("name", "kind"),
    [("hs.hs_metrics", HsMetrics), ("cmm.insert_size_metrics", InsertSizeMetrics)],
    ids=["hs", "insert-size"],
)
def test_reader_reads_metrics_whose_floats_hold_a_decimal_comma(
    tmp_path: Path, name: str, kind: type[Any]
) -> None:
    """Metrics written with a decimal comma read as the same metrics written with a point."""
    plain = DATA / name
    path = tmp_path / name
    at = label_row(plain, METRICS_CLASS)
    _ = path.write_text(with_decimal_commas(plain, at, kind, picard_rename(kind)))
    assert path.read_text().count(",") > plain.read_text().count(",")
    with (
        PicardReader.from_path[kind](path) as comma_reader,
        PicardReader.from_path[kind](plain) as point_reader,
    ):
        comma_rows, point_rows = list(comma_reader), list(point_reader)
    assert point_rows
    assert same(comma_rows, point_rows)


@pytest.mark.parametrize(
    ("name", "kind"),
    [
        ("rna.rna_metrics", RnaCoverageHistogram),
        ("cmm.quality_by_cycle_metrics", MeanQualityByCycle),
    ],
    ids=["rna", "mean-quality"],
)
def test_reader_reads_a_histogram_whose_floats_hold_a_decimal_comma(
    tmp_path: Path, name: str, kind: type[Any]
) -> None:
    """A histogram of floats written with a decimal comma reads as one written with a point."""
    plain = DATA / name
    path = tmp_path / name
    at = label_row(plain, HISTOGRAM)
    _ = path.write_text(with_decimal_commas(plain, at, kind, HISTOGRAMS[kind].labels))
    assert path.read_text().count(",") > plain.read_text().count(",")
    with (
        PicardHistogramReader.from_path[kind](path) as comma_reader,
        PicardHistogramReader.from_path[kind](plain) as point_reader,
    ):
        comma_bins, point_bins = list(comma_reader), list(point_reader)
    assert point_bins
    assert same(comma_bins, point_bins)


def test_coverage_reader_reads_floats_with_a_decimal_comma_and_writes_them_with_a_point(
    tmp_path: Path,
) -> None:
    """Per-target coverage written with a decimal comma reads alike, and writes with a point."""
    plain = DATA / "hs.per_target_coverage.txt"
    path = tmp_path / plain.name
    _ = path.write_text(
        with_decimal_commas(plain, 0, PerTargetCoverage, coverage_rename(PerTargetCoverage))
    )
    assert path.read_text().count(",") > plain.read_text().count(",")
    with (
        PicardCoverageReader.from_path[PerTargetCoverage](path) as comma_reader,
        PicardCoverageReader.from_path[PerTargetCoverage](plain) as point_reader,
    ):
        comma_rows, point_rows = list(comma_reader), list(point_reader)
    assert point_rows
    assert same(comma_rows, point_rows)
    comma_out, point_out = tmp_path / "comma.txt", tmp_path / "point.txt"
    for out, rows in ((comma_out, comma_rows), (point_out, point_rows)):
        with PicardCoverageWriter.from_path[PerTargetCoverage](out) as writer:
            writer.write_all(rows)
    assert "," not in comma_out.read_text()
    assert comma_out.read_text() == point_out.read_text()


def test_picard_rename_upper_cases_each_field() -> None:
    """A field's column is its name in upper case."""
    assert picard_rename(QualityYieldMetrics)["total_reads"] == "TOTAL_READS"


def test_picard_rename_keeps_the_java_label_of_a_camel_case_field() -> None:
    """A field whose Java label is not its name in upper case keeps that label."""
    assert picard_rename(IndependentReplicateMetric)["n_sites"] == "nSites"


def test_picard_rename_gives_a_subclass_the_columns_of_its_picard_dataclass() -> None:
    """A subclass of a Picard dataclass that adds only a property has its parent's columns."""

    class Yield(QualityYieldMetrics):
        @property
        def pf_fraction(self) -> float:
            return self.pf_reads / self.total_reads

    class Replicate(IndependentReplicateMetric):
        @property
        def sites(self) -> int | None:
            return self.n_sites

    assert picard_rename(Yield) == picard_rename(QualityYieldMetrics)
    assert picard_rename(Replicate) == picard_rename(IndependentReplicateMetric)
    assert picard_rename(Replicate)["n_sites"] == "nSites"
