import gzip
import re
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import assert_type

import pytest

from captainslog.riker import AlignmentMetrics
from captainslog.riker import HybcapPerBase
from captainslog.riker import RikerReader
from captainslog.riker import RnaBiotype
from captainslog.riker import metrics_class
from captainslog.riker._reader import SUFFIXES
from tests.riker import ALL_RIKER_FIXTURES
from tests.riker import DATA
from tests.riker import riker_class_of


@dataclass(frozen=True)
class NotRiker:
    """A dataclass that is not a Riker dataclass."""

    sample: str


class DerivedBiotype(RnaBiotype):
    """A user's subclass of a Riker dataclass that derives a name."""

    @property
    def label(self) -> str:
        """The sample and biotype."""
        return f"{self.sample}:{self.biotype}"


@pytest.mark.parametrize("path", ALL_RIKER_FIXTURES, ids=lambda path: path.name)
def test_metrics_class_names_the_dataclass_that_reads_every_fixture(path: Path) -> None:
    """The class that the suffix names reads the fixture."""
    kind = metrics_class(path)
    with RikerReader.from_path[kind](path) as reader:
        _ = list(reader)


@pytest.mark.parametrize("path", ALL_RIKER_FIXTURES, ids=lambda path: path.name)
def test_suffixes_agree_with_the_classes_of_the_fixtures(path: Path) -> None:
    """Every fixture's suffix is held by the registry, under its class."""
    assert metrics_class(path) is riker_class_of(path)


def test_suffixes_hold_twenty_suffixes_with_a_leading_dot() -> None:
    """The registry holds the twenty suffixes Riker writes."""
    assert len(SUFFIXES) == 20
    assert all(suffix.startswith(".") and suffix.endswith(".txt") for suffix in SUFFIXES)


@pytest.mark.parametrize("ending", [".txt", ".txt.gz", ".txt.bgz"])
def test_metrics_class_drops_one_compression_suffix(ending: str) -> None:
    """A `.gz` or `.bgz` is dropped before the suffix is matched."""
    assert metrics_class(f"out.hybcap-per-base{ending}") is HybcapPerBase


def test_no_riker_suffix_ends_with_another() -> None:
    """The longest-suffix match is unambiguous: a suffix is never the end of another."""
    assert not [(a, b) for a in SUFFIXES for b in SUFFIXES if a != b and a.endswith(b)]
    assert all(metrics_class(f"s{suffix}") is kind for suffix, kind in SUFFIXES.items())


def test_metrics_class_refuses_an_unknown_suffix() -> None:
    """A path with no Riker suffix is refused, named as given."""
    with pytest.raises(ValueError, match=r"^x\.txt does not end with a Riker 0\.5\.0 suffix: \["):
        _ = metrics_class("x.txt")


def test_metrics_class_drops_only_one_compression_suffix() -> None:
    """A second compression suffix is not dropped, so the path is refused."""
    with pytest.raises(ValueError, match=r"^s\.rna-biotype\.txt\.gz\.gz does not end with"):
        _ = metrics_class("s.rna-biotype.txt.gz.gz")


def test_reader_reads_a_gzipped_per_base_file(tmp_path: Path) -> None:
    """A gzipped file reads as the same records as the plain file."""
    plain = DATA / "s.hybcap-per-base.txt"
    gzipped = tmp_path / "s.hybcap-per-base.txt.gz"
    _ = gzipped.write_bytes(gzip.compress(plain.read_bytes()))
    with (
        RikerReader.from_path[HybcapPerBase](gzipped) as gzipped_reader,
        RikerReader.from_path[HybcapPerBase](plain) as plain_reader,
    ):
        rows = list(gzipped_reader)
        assert rows
        assert rows == list(plain_reader)


def test_reader_reads_a_sample_whose_name_starts_with_a_comment_prefix() -> None:
    """A sample named `#x` is a record, not a comment."""
    handle = StringIO("sample\tbiotype\treads\tfrac_reads\n#x\tlncRNA\t3\t0.5\n")
    with RikerReader[RnaBiotype](handle) as reader:
        assert list(reader) == [RnaBiotype(sample="#x", biotype="lncRNA", reads=3, frac_reads=0.5)]


def test_reader_reads_no_records_from_an_empty_file(tmp_path: Path) -> None:
    """A file with no header and no rows holds no records."""
    path = tmp_path / "s.alignment-metrics.txt"
    _ = path.write_text("")
    with RikerReader.from_path[AlignmentMetrics](path) as reader:
        assert list(reader) == []


def test_reader_refuses_a_class_that_is_not_a_riker_dataclass() -> None:
    """A record type that is no Riker dataclass is refused before any text is read."""
    handle = StringIO("sample\nx\n")
    message = "NotRiker is not a Riker dataclass!"
    with pytest.raises(TypeError, match=f"^{re.escape(message)}$"):
        _ = RikerReader[NotRiker](handle)
    assert handle.tell() == 0


def test_reader_reads_a_users_subclass_of_a_riker_dataclass() -> None:
    """A subclass of a Riker dataclass reads as its parent does."""
    handle = StringIO("sample\tbiotype\treads\tfrac_reads\ns\tmRNA\t1\t1.0\n")
    with RikerReader[DerivedBiotype](handle) as reader:
        (row,) = list(reader)
    assert row.label == "s:mRNA"


def test_reader_refuses_a_file_whose_columns_differ() -> None:
    """A file with another header is refused by typeline, naming the column."""
    handle = StringIO("sample\tbiotype\treads\tfrac\ns\tmRNA\t1\t1.0\n")
    with (
        pytest.raises(ValueError, match="frac_reads"),
        RikerReader[RnaBiotype](handle) as reader,
    ):
        _ = list(reader)


def test_from_path_types_the_riker_reader() -> None:
    """Type checkers see `from_path` build the reader over its record type."""
    with RikerReader.from_path[RnaBiotype](DATA / "s.rna-biotype.txt") as reader:
        _ = assert_type(reader, RikerReader[RnaBiotype])
        assert type(reader).__name__ == "RikerReader[RnaBiotype]"
