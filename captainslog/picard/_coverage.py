from dataclasses import dataclass
from typing import Any
from typing import TextIO

from typeline import ReaderOptions
from typeline import RecordType
from typeline import TsvReader
from typeline import TsvWriter
from typeline import WriterOptions
from typing_extensions import Unpack

from captainslog._binding import FromPath
from captainslog.picard._format import PICARD_CODECS


@dataclass(frozen=True, kw_only=True)
class PerTargetCoverage:
    """The coverage of one target, a row of the file of per-target coverage that Picard writes."""

    chrom: str = ""
    """The contig of the target"""

    start: int = 0
    """The 1-based start of the target"""

    end: int = 0
    """The 1-based, inclusive end of the target"""

    length: int = 0
    """The number of bases of the target"""

    name: str = ""
    """The name of the target interval"""

    pct_gc: float = 0.0
    """The fraction of the bases of the target that are G or C"""

    mean_coverage: float = 0.0
    """The mean high quality depth over the bases of the target"""

    normalized_coverage: float = 0.0
    """The mean coverage of the target over the mean coverage of all targets"""

    min_normalized_coverage: float = 0.0
    """The least depth of a base of the target over the mean coverage of all targets"""

    max_normalized_coverage: float = 0.0
    """The greatest depth of a base of the target over the mean coverage of all targets"""

    min_coverage: int = 0
    """The least high quality depth of a base of the target"""

    max_coverage: int = 0
    """The greatest high quality depth of a base of the target"""

    pct_0x: float = 0.0
    """The fraction of the bases of the target with no coverage"""

    read_count: int = 0
    """The number of reads that overlap the target"""


@dataclass(frozen=True, kw_only=True)
class PerBaseCoverage:
    """The coverage of one base of a target, a row of the file of per-base coverage."""

    chrom: str = ""
    """The contig of the target"""

    pos: int = 0
    """The 1-based position of the base"""

    target: str = ""
    """The name of the target interval that holds the base"""

    coverage: int = 0
    """The high quality depth at the base"""


# fmt: off
COVERAGE_RENAMES: dict[type[Any], dict[str, str]] = {
    PerBaseCoverage: {},
    PerTargetCoverage: {"pct_gc": "%gc"},
}
# fmt: on


def coverage_rename(record_type: type[Any]) -> dict[str, str]:
    """Name the column of each field of a Picard coverage dataclass that differs from its name.

    Args:
        record_type: the dataclass, or a class that inherits from one.

    Raises:
        TypeError: if the class neither is nor inherits from a Picard coverage dataclass.
    """
    mro = record_type.__mro__
    found = next((COVERAGE_RENAMES[kind] for kind in mro if kind in COVERAGE_RENAMES), None)
    if found is None:
        raise TypeError(f"{record_type.__name__} is not a Picard coverage dataclass!")
    return found


class PicardCoverageReader(TsvReader[RecordType]):
    """A reader of a Picard file of per-target or per-base coverage, into its dataclass."""

    from_path: FromPath = FromPath()  # type: ignore[assignment]  # pyright: ignore[reportIncompatibleVariableOverride]  # ty: ignore[invalid-attribute-override]

    def __init__(self, handle: TextIO, /, **options: Unpack[ReaderOptions]) -> None:
        """Read the rows of a Picard file of per-target or per-base coverage.

        Args:
            handle: the text of the file.
            options: the options of the reader, left at Picard's defaults when not given.

        Raises:
            TypeError: if the record type is not a Picard coverage dataclass or a subclass of one.
        """
        rename = coverage_rename(self._bound_record_type())
        _ = options.setdefault("codecs", PICARD_CODECS)
        _ = options.setdefault("comment_prefixes", ())
        _ = options.setdefault("quoting", False)
        _ = options.setdefault("rename", rename)
        super().__init__(handle, **options)


class PicardCoverageWriter(TsvWriter[RecordType]):
    """A writer of a Picard file of per-target or per-base coverage, from its dataclass."""

    from_path: FromPath = FromPath()  # type: ignore[assignment]  # pyright: ignore[reportIncompatibleVariableOverride]  # ty: ignore[invalid-attribute-override]

    def __init__(self, handle: TextIO, /, **options: Unpack[WriterOptions]) -> None:
        """Write the rows of a Picard file of per-target or per-base coverage, under a header.

        Args:
            handle: a text stream to write the file to, opened with `newline=""`.
            options: the options of the writer, left at Picard's defaults when not given.

        Raises:
            TypeError: if the record type is not a Picard coverage dataclass or a subclass of one.
        """
        rename = coverage_rename(self._bound_record_type())
        _ = options.setdefault("codecs", PICARD_CODECS)
        _ = options.setdefault("comment_prefixes", ("\n",))
        _ = options.setdefault("header", True)
        _ = options.setdefault("quoting", False)
        _ = options.setdefault("rename", rename)
        super().__init__(handle, **options)
