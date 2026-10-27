from dataclasses import dataclass
from typing import Any
from typing import TextIO

from typeline import Comment
from typeline import ReaderOptions
from typeline import RecordType
from typeline import TsvReader
from typeline import TsvWriter
from typeline import WriterOptions
from typing_extensions import Unpack
from typing_extensions import override

from captainslog._binding import FromPath
from captainslog.picard._reader import with_table_defaults
from captainslog.picard._writer import table_options


@dataclass(frozen=True, kw_only=True)
class PerTargetCoverage:
    """The coverage of one target, a row of the file of per-target coverage that Picard writes."""

    chrom: str = ""
    """The contig of the target."""

    start: int = 0
    """The 1-based start of the target."""

    end: int = 0
    """The 1-based, inclusive end of the target."""

    length: int = 0
    """The number of bases of the target."""

    name: str = ""
    """The name of the target interval."""

    frac_gc: float = 0.0
    """The fraction of the reference bases of the target that are G or C.

    A fraction from 0 to 1, in Picard's `%gc` column.
    """

    mean_coverage: float = 0.0
    """The mean high quality depth over the bases of the target."""

    normalized_coverage: float = 0.0
    """The mean coverage of the target over the mean target coverage, the total high quality
    depth over the target territory.
    """

    min_normalized_coverage: float = 0.0
    """The least depth of a base of the target over the mean target coverage, the total high
    quality depth over the target territory.
    """

    max_normalized_coverage: float = 0.0
    """The greatest depth of a base of the target over the mean target coverage, the total
    high quality depth over the target territory.
    """

    min_coverage: int = 0
    """The least high quality depth of a base of the target."""

    max_coverage: int = 0
    """The greatest high quality depth of a base of the target."""

    frac_0x: float = 0.0
    """The fraction of the bases of the target with no coverage.

    A fraction from 0 to 1, in Picard's `pct_0x` column.
    """

    read_count: int = 0
    """The number of reads that are not duplicates, meet the minimum mapping quality and are not
    adapter, with at least one high quality aligned base on the target.
    """


@dataclass(frozen=True, kw_only=True)
class PerBaseCoverage:
    """The coverage of one base of a target, a row of the file of per-base coverage."""

    chrom: str = ""
    """The contig of the target."""

    pos: int = 0
    """The 1-based position of the base."""

    target: str = ""
    """The name of the target interval that holds the base."""

    coverage: int = 0
    """The high quality depth at the base."""


# fmt: off
COVERAGE_RENAMES: dict[type[Any], dict[str, str]] = {
    PerBaseCoverage: {},
    PerTargetCoverage: {"frac_0x": "pct_0x", "frac_gc": "%gc"},
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
            ValueError: if the columns of the file differ from the record type's fields, naming
                those missing from the file and those it does not expect.
        """
        with_table_defaults(options, coverage_rename(self.record_type))
        super().__init__(handle, **options)


class PicardCoverageWriter(TsvWriter[RecordType]):
    """A writer of a Picard file of per-target or per-base coverage, from its dataclass.

    Each float is written as the shortest text that reads back as the same number, such as
    `0.30000000000000004` or `1e-7`, not rounded to Picard's six places.
    """

    from_path: FromPath = FromPath()  # type: ignore[assignment]  # pyright: ignore[reportIncompatibleVariableOverride]  # ty: ignore[invalid-attribute-override]

    def __init__(self, handle: TextIO, /, **options: Unpack[WriterOptions]) -> None:
        """Write the rows of a Picard file of per-target or per-base coverage, under a header.

        Args:
            handle: a text stream to write the file to, opened with `newline=""`.
            options: the options of the writer, left at Picard's defaults when not given.

        Raises:
            TypeError: if the record type is not a Picard coverage dataclass or a subclass of one.
        """
        defaults = table_options(coverage_rename(self.record_type))
        defaults.update(options)
        super().__init__(handle, **defaults)

    @override
    def write_comment(self, comment: str | Comment) -> None:
        """Refuse a comment, since a Picard coverage file holds none.

        Raises:
            TypeError: always.
        """
        raise TypeError("A Picard coverage file holds no comments!")
