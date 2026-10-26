import gzip
import re
from dataclasses import fields
from dataclasses import replace
from io import StringIO
from itertools import takewhile
from pathlib import Path
from types import GenericAlias
from typing import Any
from typing import get_args
from typing import get_type_hints

import pytest
from typeline import Comment
from typeline import NamedExtraColumns

from shipslog.picard import DuplicateSetSizeHistogram
from shipslog.picard import DuplicationRoiHistogram
from shipslog.picard import HsHistogram
from shipslog.picard import InsertSizeHistogram
from shipslog.picard import InsertSizeMetrics
from shipslog.picard import MeanQualityByCycle
from shipslog.picard import PicardHeader
from shipslog.picard import PicardHistogramReader
from shipslog.picard import QualityScoreDistribution
from shipslog.picard import RnaCoverageHistogram
from shipslog.picard import ValidationErrorHistogram
from shipslog.picard import _histograms
from shipslog.picard import histogram_class
from shipslog.picard._histograms import HISTOGRAMS
from shipslog.picard._java import JAVA_NAMES
from shipslog.picard._reader import histogram_classes
from tests.compare import same
from tests.picard import DATA
from tests.picard import FIXTURE_CLASSES
from tests.picard import HEADER
from tests.picard import HISTOGRAM
from tests.picard import LINES
from tests.picard import METRICS_CLASS
from tests.picard import PICARD_HISTOGRAM_FIXTURES
from tests.picard import VALIDATE_SAM_FILE
from tests.picard import DerivedHistogram
from tests.picard import NotHistogram

KEY_TYPES: dict[str, type[Any]] = {
    "java.lang.Byte": int,
    "java.lang.Double": float,
    "java.lang.Integer": int,
    "java.lang.String": str,
}

EXTRA_TYPES: tuple[Any, ...] = (NamedExtraColumns[int], NamedExtraColumns[float])


def snake_case(label: str) -> str:
    """The snake_case of a column label, e.g. `coverage_mult` for `CoverageMult`."""
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", label).replace(" ", "_").lower()


def histogram_line(lines: list[str]) -> int:
    """The index of the `## HISTOGRAM` line of a file's lines."""
    return next(index for index, line in enumerate(lines) if line.startswith(HISTOGRAM))


def test_reader_reads_the_insert_size_histogram_by_column_name() -> None:
    """The bins of a histogram hold its key, and each column a header names, by its name."""
    path = DATA / "cmm.insert_size_metrics"
    bins = list(PicardHistogramReader.from_path[InsertSizeHistogram](path))
    assert bins and all(b.insert_size > 0 for b in bins)
    assert "All_Reads.fr_count" in bins[0].counts


@pytest.mark.parametrize("path", PICARD_HISTOGRAM_FIXTURES, ids=lambda path: path.name)
def test_histogram_class_names_a_class_that_reads_every_histogram_fixture(path: Path) -> None:
    """Every histogram Picard wrote reads as bins of the class `histogram_class` names."""
    kind = histogram_class(path)
    assert list(PicardHistogramReader.from_path[kind](path))


def test_histogram_class_names_the_class_of_each_histogram_fixture() -> None:
    """Each histogram fixture is named as the dataclass of its shape."""
    assert {path.name for path in PICARD_HISTOGRAM_FIXTURES} == set(FIXTURE_CLASSES)
    for name, kind in FIXTURE_CLASSES.items():
        assert histogram_class(DATA / name) is kind, name


@pytest.mark.parametrize("path", PICARD_HISTOGRAM_FIXTURES, ids=lambda path: path.name)
def test_every_histogram_fixture_matches_exactly_one_class(path: Path) -> None:
    """No two registered classes match the metrics class and label row of a fixture."""
    lines = path.read_text().splitlines()
    java = next(
        (line.removeprefix(METRICS_CLASS) for line in lines if line.startswith(METRICS_CLASS)), None
    )
    labels = lines[histogram_line(lines) + 1].split("\t")
    assert len(histogram_classes(java, labels)) == 1


def test_each_registered_label_row_matches_only_its_class() -> None:
    """The fixed labels of each class, in each of its owners' files, match that class alone."""
    for kind, histogram in HISTOGRAMS.items():
        for owner in histogram.owners or {None}:
            assert histogram_classes(owner, list(histogram.labels.values())) == [kind], kind


@pytest.mark.parametrize("path", PICARD_HISTOGRAM_FIXTURES, ids=lambda path: path.name)
def test_reader_reads_every_bin_of_every_histogram_fixture(path: Path) -> None:
    """Each line after the label row, up to a blank line, reads as a bin keyed by its first cell."""
    lines = path.read_text().splitlines()
    rows = list(takewhile(lambda line: line.strip() != "", lines[histogram_line(lines) + 2 :]))
    kind = FIXTURE_CLASSES[path.name]
    key = fields(kind)[0].name
    key_type = KEY_TYPES[HISTOGRAMS[kind].key]
    bins = list(PicardHistogramReader.from_path[kind](path))
    assert rows
    assert [getattr(b, key) for b in bins] == [key_type(row.split("\t")[0]) for row in rows]


@pytest.mark.parametrize("path", PICARD_HISTOGRAM_FIXTURES, ids=lambda path: path.name)
def test_every_histogram_fixture_names_the_key_of_its_class(path: Path) -> None:
    """The `## HISTOGRAM` line of each fixture names the Java key class its class registers."""
    lines = path.read_text().splitlines()
    key = HISTOGRAMS[FIXTURE_CLASSES[path.name]].key
    assert lines[histogram_line(lines)].endswith(f"\t{key}")


def test_registry_describes_each_histogram_dataclass() -> None:
    """Each histogram dataclass is registered with its owners, its key, and its fixed labels."""
    exported = {getattr(_histograms, name) for name in _histograms.__all__}
    assert exported == set(HISTOGRAMS) | {histogram.columns for histogram in HISTOGRAMS.values()}
    assert _histograms.__all__ == sorted(_histograms.__all__)
    for kind, histogram in HISTOGRAMS.items():
        assert kind.__dataclass_params__.frozen, kind
        assert all(f.kw_only is True for f in fields(kind)), kind
        names = [f.name for f in fields(kind)]
        hints = get_type_hints(kind, include_extras=True)
        extras = [name for name in names if hints[name] in EXTRA_TYPES]
        assert extras in ([], names[-1:]), kind
        assert list(histogram.labels) == [name for name in names if name not in extras], kind
        assert all(name == snake_case(label) for name, label in histogram.labels.items()), kind
        assert histogram.owners <= set(JAVA_NAMES.values()), kind
        assert hints[names[0]] is KEY_TYPES[histogram.key], kind
        columns = histogram.columns
        assert columns.__dataclass_params__.frozen, columns
        assert all(f.kw_only is True for f in fields(columns)), columns
        assert [f.name for f in fields(columns)] == names, columns
        column_hints = get_type_hints(columns)
        for name in names:
            row_type = get_args(get_args(hints[name])[0])[1] if name in extras else hints[name]
            column = GenericAlias(tuple, (row_type, ...))
            expected = GenericAlias(dict, (str, column)) if name in extras else column
            assert column_hints[name] == expected, (columns, name)


def test_reader_refuses_a_histogram_the_files_of_the_metrics_class_do_not_hold() -> None:
    """A metrics file whose class does not own the histogram is refused, naming both."""
    path = DATA / "cmm.quality_yield_metrics"
    assert path not in PICARD_HISTOGRAM_FIXTURES
    java = "picard.analysis.CollectQualityYieldMetrics$QualityYieldMetrics"
    message = f"{path} holds {java}, whose files hold no InsertSizeHistogram!"
    with pytest.raises(ValueError, match=f"^{re.escape(message)}$"):
        _ = PicardHistogramReader.from_path[InsertSizeHistogram](path)


def test_reader_refuses_a_histogram_only_class_from_a_metrics_file() -> None:
    """A histogram that Picard writes without metrics is refused from a file of metrics."""
    path = DATA / "cmm.insert_size_metrics"
    message = (
        f"{path} holds picard.analysis.InsertSizeMetrics, whose files hold no MeanQualityByCycle!"
    )
    with pytest.raises(ValueError, match=f"^{re.escape(message)}$"):
        _ = PicardHistogramReader.from_path[MeanQualityByCycle](path)


def test_reader_refuses_an_owned_histogram_from_a_histogram_only_file() -> None:
    """A histogram that Picard writes after metrics is refused from a file of only a histogram."""
    path = DATA / "cmm.quality_by_cycle_metrics"
    message = f"{path} holds only a histogram, which is not InsertSizeHistogram!"
    with pytest.raises(ValueError, match=f"^{re.escape(message)}$"):
        _ = PicardHistogramReader.from_path[InsertSizeHistogram](path)


def test_reader_reads_no_rows_from_an_owner_file_without_its_histogram(tmp_path: Path) -> None:
    """A file of the metrics that own a histogram, but without one, holds no bins."""
    lines = (DATA / "cmm.insert_size_metrics").read_text().split("\n")
    path = tmp_path / "cut.insert_size_metrics"
    _ = path.write_text("".join(f"{line}\n" for line in lines[: histogram_line(lines)]))
    with PicardHistogramReader.from_path[InsertSizeHistogram](path) as reader:
        assert list(reader) == []
        assert reader.header.command_line.startswith("CollectMultipleMetrics")


@pytest.mark.parametrize("blank_lines", [1, 3])
def test_reader_of_a_file_without_a_section_reads_no_records(blank_lines: int) -> None:
    """A file with a header and no section, as htsjdk writes for no data, holds no bins."""
    text = "\n".join([*LINES, *[""] * (blank_lines + 1)])
    with PicardHistogramReader[InsertSizeHistogram](StringIO(text)) as reader:
        assert list(reader) == []
        assert reader.header == HEADER


@pytest.mark.parametrize(
    "text",
    ["\n".join(LINES), "\n".join(LINES) + "\n", "\r\n".join(LINES) + "\r\n"],
    ids=["no-line-break", "lf", "crlf"],
)
def test_reader_and_histogram_class_refuse_a_file_that_ends_after_its_header(
    tmp_path: Path, text: str
) -> None:
    """A header without the blank line htsjdk writes after it may be cut short."""
    path = tmp_path / "cut.quality_distribution_metrics"
    _ = path.write_bytes(text.encode())
    message = f"{path} ends after its header, so it may be cut short!"
    with pytest.raises(ValueError, match=f"^{re.escape(message)}$"):
        _ = PicardHistogramReader.from_path[MeanQualityByCycle](path)
    with pytest.raises(ValueError, match=f"^{re.escape(message)}$"):
        _ = histogram_class(path)


def test_histogram_class_refuses_a_header_and_its_blank_lines_as_no_histogram(
    tmp_path: Path,
) -> None:
    """A header and the blank lines after it, as htsjdk writes for no data, hold no histogram."""
    path = tmp_path / "empty.quality_distribution_metrics"
    _ = path.write_text("\n".join([*LINES, "", ""]))
    with pytest.raises(ValueError, match=f"^{re.escape(str(path))} holds no histogram!$"):
        _ = histogram_class(path)


@pytest.mark.parametrize("end", ["", "\n"], ids=repr)
def test_reader_reads_a_histogram_the_file_ends_without_a_blank_line(end: str) -> None:
    """A histogram that ends the file, without a blank line after it, reads every bin."""
    path = DATA / "cmm.quality_by_cycle_metrics"
    text = path.read_text().rstrip("\n") + end
    with (
        PicardHistogramReader[MeanQualityByCycle](StringIO(text)) as cut_reader,
        PicardHistogramReader.from_path[MeanQualityByCycle](path) as reader,
    ):
        bins = list(reader)
        assert bins
        assert same(list(cut_reader), bins)


def test_reader_reads_the_header_of_a_histogram_only_file() -> None:
    """A file of only a histogram has the header htsjdk wrote at its top."""
    path = DATA / "cmm.quality_by_cycle_metrics"
    with PicardHistogramReader.from_path[MeanQualityByCycle](path) as reader:
        assert reader.header.command_line.startswith("CollectMultipleMetrics INPUT=in/sample.bam")
        assert reader.header.started_on == "Sat Oct 24 21:42:13 HST 2026"
        assert reader.header.others == ()
        assert list(reader)


def test_reader_passes_header_comments_to_the_callers_on_comment() -> None:
    """The caller's `on_comment` receives each header line, with its line number, on opening."""
    path = DATA / "cmm.insert_size_metrics"
    lines = takewhile(lambda line: line.startswith("#"), path.read_text().split("\n"))
    expected = [Comment(number, line) for number, line in enumerate(lines, start=1)]
    assert len(expected) == 4
    received: list[Comment] = []
    with PicardHistogramReader.from_path[InsertSizeHistogram](
        path, on_comment=received.append
    ) as reader:
        assert received == expected
        assert list(reader)
    assert received == expected


def test_reader_refuses_a_file_that_is_not_picard() -> None:
    """A file whose first line after the comments starts no section is refused."""
    path = DATA / "hs.per_target_coverage.txt"
    with pytest.raises(ValueError, match=f"^{re.escape(str(path))} is not a Picard metrics file!$"):
        _ = PicardHistogramReader.from_path[HsHistogram](path)


def test_histogram_class_refuses_a_file_that_is_not_picard() -> None:
    """A file whose first line after the comments starts no section names no histogram."""
    path = DATA / "hs.per_target_coverage.txt"
    with pytest.raises(ValueError, match=f"^{re.escape(str(path))} is not a Picard metrics file!$"):
        _ = histogram_class(path)


def test_reader_refuses_lone_carriage_returns() -> None:
    """A file whose lines end with a carriage return alone is refused, not read as empty."""
    text = (DATA / "cmm.quality_by_cycle_metrics").read_text().replace("\n", "\r")
    message = r"^The text breaks its lines with lone carriage returns, not line feeds!$"
    with pytest.raises(ValueError, match=message):
        _ = PicardHistogramReader[MeanQualityByCycle](StringIO(text))


def test_histogram_class_refuses_a_file_without_a_histogram() -> None:
    """A metrics file without a histogram names no histogram dataclass."""
    path = DATA / "cmm.quality_yield_metrics"
    assert path not in PICARD_HISTOGRAM_FIXTURES
    with pytest.raises(ValueError, match=r"cmm\.quality_yield_metrics holds no histogram!$"):
        _ = histogram_class(path)


def test_histogram_class_refuses_an_unknown_label_row(tmp_path: Path) -> None:
    """A label row no registered class matches is refused, naming its labels."""
    text = (DATA / "cmm.quality_by_cycle_metrics").read_text()
    assert "CYCLE\tMEAN_QUALITY\t" in text
    path = tmp_path / "unknown.quality_by_cycle_metrics"
    _ = path.write_text(text.replace("CYCLE\tMEAN_QUALITY\t", "CYCLE\tMEDIAN_QUALITY\t"))
    labels = "CYCLE, MEDIAN_QUALITY, MEAN_ORIGINAL_QUALITY"
    message = f"{path} holds a histogram shipslog does not know: {labels}!"
    with pytest.raises(ValueError, match=f"^{re.escape(message)}$"):
        _ = histogram_class(path)


def test_histogram_class_refuses_the_repeated_labels_of_several_levels(tmp_path: Path) -> None:
    """A targeted histogram of several accumulation levels repeats its labels, so is unknown."""
    text = (DATA / "hs.hs_metrics").read_text()
    labels = "coverage_or_base_quality\thigh_quality_coverage_count\tunfiltered_baseq_count"
    assert f"\n{labels}\n" in text
    path = tmp_path / "levels.hs_metrics"
    repeated = f"{labels}\thigh_quality_coverage_count\tunfiltered_baseq_count"
    _ = path.write_text(text.replace(f"\n{labels}\n", f"\n{repeated}\n"))
    known = repeated.replace("\t", ", ")
    message = f"{path} holds a histogram shipslog does not know: {known}!"
    with pytest.raises(ValueError, match=f"^{re.escape(message)}$"):
        _ = histogram_class(path)


@pytest.mark.parametrize(
    ("name", "kind"),
    [
        ("one_library.duplication_metrics", DuplicationRoiHistogram),
        ("dup.duplication_metrics", DuplicateSetSizeHistogram),
    ],
    ids=["roi", "set_size"],
)
def test_optical_sets_between_fixed_columns_read_as_an_extra_column(
    tmp_path: Path, name: str, kind: type[Any]
) -> None:
    """An `optical_sets` column between two fixed columns is named and read into the extras."""
    plain = DATA / name
    lines = plain.read_text().split("\n")
    at = histogram_line(lines) + 1
    column = lines[at].split("\t").index("all_sets") + 1
    stop = next(index for index in range(at, len(lines)) if lines[index].strip() == "")
    for index in range(at, stop):
        cells = lines[index].split("\t")
        cells.insert(column, "optical_sets" if index == at else "1")
        lines[index] = "\t".join(cells)
    assert lines[at].endswith("\tall_sets\toptical_sets\tnon_optical_sets")
    path = tmp_path / name
    _ = path.write_text("\n".join(lines))
    assert histogram_class(path) is kind
    with (
        PicardHistogramReader.from_path[kind](path) as optical_reader,
        PicardHistogramReader.from_path[kind](plain) as plain_reader,
    ):
        optical_bins, plain_bins = list(optical_reader), list(plain_reader)
    assert plain_bins
    assert all(b.counts == {"optical_sets": 1} for b in optical_bins)
    assert same([replace(b, counts={}) for b in optical_bins], plain_bins)


def test_histogram_class_reads_a_gzipped_file(tmp_path: Path) -> None:
    """A gzipped file names the class of the plain file, and reads as the same bins."""
    plain = DATA / "cmm.insert_size_metrics"
    gzipped = tmp_path / "cmm.insert_size_metrics.gz"
    _ = gzipped.write_bytes(gzip.compress(plain.read_bytes()))
    assert histogram_class(gzipped) is InsertSizeHistogram
    with (
        PicardHistogramReader.from_path[InsertSizeHistogram](gzipped) as gzipped_reader,
        PicardHistogramReader.from_path[InsertSizeHistogram](plain) as plain_reader,
    ):
        gzipped_bins, plain_bins = list(gzipped_reader), list(plain_reader)
        assert gzipped_bins
        assert same(gzipped_bins, plain_bins)


def test_reader_reads_a_crlf_histogram_as_the_lf_histogram(tmp_path: Path) -> None:
    """A file whose lines end with CRLF names the same class and reads as the same bins."""
    lf = DATA / "rna.rna_metrics"
    crlf = tmp_path / "rna.rna_metrics"
    _ = crlf.write_text(lf.read_text(), newline="\r\n")
    assert crlf.read_bytes().count(b"\r\n") == lf.read_bytes().count(b"\n")
    assert histogram_class(crlf) is RnaCoverageHistogram
    with (
        PicardHistogramReader.from_path[RnaCoverageHistogram](crlf) as crlf_reader,
        PicardHistogramReader.from_path[RnaCoverageHistogram](lf) as lf_reader,
    ):
        crlf_bins, lf_bins = list(crlf_reader), list(lf_reader)
        assert lf_bins
        assert same(crlf_bins, lf_bins)
        assert crlf_reader.header == lf_reader.header


def test_reader_refuses_a_record_type_that_is_not_a_picard_histogram() -> None:
    """A dataclass that is not a Picard histogram dataclass is refused before the file is read."""
    handle = StringIO((DATA / "cmm.insert_size_metrics").read_text())
    with pytest.raises(TypeError, match=r"^NotHistogram is not a Picard histogram dataclass!$"):
        _ = PicardHistogramReader[NotHistogram](handle)
    message = r"^InsertSizeMetrics is not a Picard histogram dataclass!$"
    with pytest.raises(TypeError, match=message):
        _ = PicardHistogramReader[InsertSizeMetrics](handle)
    assert handle.tell() == 0


def test_reader_reads_a_users_subclass_of_a_histogram() -> None:
    """A subclass of the histogram a file holds reads the file into the subclass."""
    bins = list(PicardHistogramReader.from_path[DerivedHistogram](DATA / "cmm.insert_size_metrics"))
    assert bins
    assert all(isinstance(b, DerivedHistogram) for b in bins)
    assert bins[0].all_reads == bins[0].counts["All_Reads.fr_count"]


@pytest.mark.parametrize("end", ["\n\n", "\n", ""], ids=["blank-line", "line-break", "none"])
def test_reader_reads_the_summary_validate_sam_file_writes(tmp_path: Path, end: str) -> None:
    """ValidateSamFile's summary, two blank lines then a histogram alone, reads however it ends."""
    path = tmp_path / "s.ValidateSamFile.SUMMARY"
    _ = path.write_text("\n".join(VALIDATE_SAM_FILE) + end)
    assert histogram_class(path) is ValidationErrorHistogram
    assert histogram_classes(None, VALIDATE_SAM_FILE[3].split("\t")) == [ValidationErrorHistogram]
    with PicardHistogramReader.from_path[ValidationErrorHistogram](path) as reader:
        assert list(reader) == [
            ValidationErrorHistogram(error_type="ERROR:MATE_NOT_FOUND", count=1),
            ValidationErrorHistogram(error_type="WARNING:MISSING_TAG_NM", count=3),
        ]
    assert reader.header == PicardHeader()


CONCATENATED = "holds another Picard file after its first, as a concatenation does!"


@pytest.mark.parametrize("path", PICARD_HISTOGRAM_FIXTURES, ids=lambda path: path.name)
def test_reader_refuses_a_histogram_fixture_written_twice_into_one_file(
    tmp_path: Path, path: Path
) -> None:
    """Two Picard files written into one, as `cat` writes them, are refused once read."""
    kind = FIXTURE_CLASSES[path.name]
    doubled = tmp_path / path.name
    _ = doubled.write_text(path.read_text() * 2)
    message = f"{doubled} {CONCATENATED}"
    with (
        PicardHistogramReader.from_path[kind](doubled) as reader,
        pytest.raises(ValueError, match=f"^{re.escape(message)}$"),
    ):
        _ = list(reader)


@pytest.mark.parametrize("line", ["## HISTOGRAM\tjava.lang.Byte"], ids=repr)
def test_reader_refuses_a_second_histogram_after_the_histogram(line: str) -> None:
    """A second histogram follows no histogram, which htsjdk writes last."""
    text = (DATA / "cmm.quality_distribution_metrics").read_text()
    with (
        PicardHistogramReader[QualityScoreDistribution](StringIO(f"{text}\n \n{line}")) as reader,
        pytest.raises(ValueError, match=f"^The text {re.escape(CONCATENATED)}$"),
    ):
        _ = list(reader)


def test_reader_reads_a_histogram_followed_by_blank_lines() -> None:
    """The blank lines after a histogram are no second file."""
    path = DATA / "cmm.quality_distribution_metrics"
    text = path.read_text() + " \n\n\x0c\n"
    bins = list(PicardHistogramReader.from_path[QualityScoreDistribution](path))
    assert bins
    assert list(PicardHistogramReader[QualityScoreDistribution](StringIO(text))) == bins


TRAILING = "holds text after its last table, which htsjdk does not write!"


@pytest.mark.parametrize("line", ["# done", "\t", "0\t1", " x"], ids=repr)
def test_reader_refuses_text_after_the_last_table(line: str) -> None:
    """Other than blank lines, nothing follows the histogram, which htsjdk writes last."""
    text = (DATA / "cmm.quality_distribution_metrics").read_text()
    with (
        PicardHistogramReader[QualityScoreDistribution](StringIO(f"{text}\n \n{line}")) as reader,
        pytest.raises(ValueError, match=f"^The text {re.escape(TRAILING)}$"),
    ):
        _ = list(reader)


@pytest.mark.parametrize("line", ["## htsjdk.samtools.metrics.StringHeader", "## METRICS CLASS\tx"])
def test_reader_refuses_a_header_or_metrics_after_the_histogram(line: str) -> None:
    """A header line or a metrics section after any table is a concatenation."""
    text = (DATA / "cmm.quality_distribution_metrics").read_text()
    with (
        PicardHistogramReader[QualityScoreDistribution](StringIO(f"{text}\n{line}\n")) as reader,
        pytest.raises(ValueError, match=f"^The text {re.escape(CONCATENATED)}$"),
    ):
        _ = list(reader)


def with_labels(row: str) -> str:
    """The text of the insert size fixture, with its histogram's label row replaced."""
    lines = (DATA / "cmm.insert_size_metrics").read_text().split("\n")
    at = next(i for i, line in enumerate(lines) if line.startswith("## HISTOGRAM")) + 1
    lines[at] = row
    return "\n".join(lines)


@pytest.mark.parametrize(
    "row",
    [
        "insert_size\tinsert_size\tAll_Reads.fr_count",
        "insert_size\tAll_Reads.fr_count\tinsert_size",
    ],
    ids=repr,
)
def test_reader_refuses_a_fixed_label_repeated(row: str) -> None:
    """A fixed column, which Picard writes once, is refused when the label row repeats it."""
    message = "^The text repeats the column insert_size, which Picard does not!$"
    with pytest.raises(ValueError, match=message):
        _ = list(PicardHistogramReader[InsertSizeHistogram](StringIO(with_labels(row))))


def test_reader_refuses_a_repeated_label_of_a_histogram_without_extra_columns() -> None:
    """A histogram with no extra columns refuses a repeated label as it does any."""
    text = (DATA / "cmm.quality_distribution_metrics").read_text()
    text = text.replace("QUALITY\tCOUNT_OF_Q", "QUALITY\tCOUNT_OF_Q\tCOUNT_OF_Q")
    message = "^The text repeats the column COUNT_OF_Q, which Picard does not!$"
    with pytest.raises(ValueError, match=message):
        _ = list(PicardHistogramReader[QualityScoreDistribution](StringIO(text)))


def test_histogram_class_names_no_class_for_a_repeated_fixed_label(tmp_path: Path) -> None:
    """A row that repeats a fixed label names no class, whether or not it keeps extra columns."""
    path = tmp_path / "a.insert_size_metrics"
    _ = path.write_text(with_labels("insert_size\tinsert_size\tAll_Reads.fr_count"))
    with pytest.raises(ValueError, match=f"^{re.escape(str(path))} repeats the column insert_size"):
        _ = histogram_class(path)
    other = tmp_path / "b.quality_distribution_metrics"
    text = (DATA / "cmm.quality_distribution_metrics").read_text()
    _ = other.write_text(text.replace("QUALITY\tCOUNT_OF_Q", "QUALITY\tCOUNT_OF_Q\tCOUNT_OF_Q"))
    with pytest.raises(ValueError):
        _ = histogram_class(other)


def test_reader_keeps_a_repeated_extra_column() -> None:
    """The column of a sample and a library of one name repeats in a Picard file, and is kept."""
    text = with_labels("insert_size\tAll_Reads.fr_count\tNA12891.fr_count\tNA12891.fr_count")
    lines = text.split("\n")
    at = next(i for i, line in enumerate(lines) if line.startswith("## HISTOGRAM")) + 2
    for i in range(at, len(lines)):
        if lines[i].strip():
            lines[i] = "\t".join(lines[i].split("\t")[:2] + ["1", "2"])
    bins = list(PicardHistogramReader[InsertSizeHistogram](StringIO("\n".join(lines))))
    assert bins
    assert "NA12891.fr_count" in bins[0].counts
