from enum import StrEnum
from typing import Protocol
from typing import cast
from typing import overload


class AccumulationLevel(StrEnum):
    """The level at which Picard accumulates the reads of a row of metrics."""

    ALL_READS = "ALL_READS"
    SAMPLE = "SAMPLE"
    LIBRARY = "LIBRARY"
    READ_GROUP = "READ_GROUP"


class Multilevel(Protocol):
    """A row of metrics whose blank sample, library, and read group columns mark its level."""

    @property
    def sample(self) -> str | None:
        """The sample of the row, or None when it accumulates more than one."""
        ...

    @property
    def library(self) -> str | None:
        """The library of the row, or None when it accumulates more than one."""
        ...

    @property
    def read_group(self) -> str | None:
        """The read group of the row, or None when it accumulates more than one."""
        ...


class Leveled(Protocol):
    """A row of metrics that names its level in a column, as the GC bias metrics do."""

    @property
    def accumulation_level(self) -> str:
        """The level of the row as Picard writes it: `All Reads`, `Sample`, `Library`, ..."""
        ...


TEXT_LEVELS: dict[str, AccumulationLevel] = {
    "All Reads": AccumulationLevel.ALL_READS,
    "Library": AccumulationLevel.LIBRARY,
    "Read Group": AccumulationLevel.READ_GROUP,
    "Sample": AccumulationLevel.SAMPLE,
}
"""The accumulation levels by the text of the column that names them."""


@overload
def accumulation_level(row: Leveled) -> AccumulationLevel: ...


@overload
def accumulation_level(row: Multilevel) -> AccumulationLevel: ...


def accumulation_level(row: object) -> AccumulationLevel:
    """Find the level at which Picard accumulated the reads of a row of metrics.

    A row with an `accumulation_level` column is read from it. Any other row is at the finest
    level whose column is not blank: read group, library, sample, else all reads.

    At the read group level, Picard 3.5.0 counts the reads of a read group without a platform unit
    (`PU`) in a row whose sample, library, and read group are each `unknown`, and tools such as
    CollectAlignmentSummaryMetrics also write an empty row for that read group. That row holds its
    sample and library but no read group, so it reads as `LIBRARY`.

    Args:
        row: a row of metrics.

    Raises:
        ValueError: if the `accumulation_level` column holds an unknown level.
    """
    if hasattr(row, "accumulation_level"):
        text = cast(Leveled, row).accumulation_level
        if text not in TEXT_LEVELS:
            raise ValueError(f"Unknown accumulation level: {text!r}!")
        return TEXT_LEVELS[text]
    levels = cast(Multilevel, row)
    if levels.read_group is not None:
        return AccumulationLevel.READ_GROUP
    if levels.library is not None:
        return AccumulationLevel.LIBRARY
    if levels.sample is not None:
        return AccumulationLevel.SAMPLE
    return AccumulationLevel.ALL_READS
