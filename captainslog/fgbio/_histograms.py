from dataclasses import dataclass
from typing import Any

__all__ = [
    "HISTOGRAMS",
    "RnaSeqInsertSizeHistogram",
    "SwitchbackGapHistogram",
    "SwitchbackLengthHistogram",
    "SwitchbackOffsetHistogram",
]


@dataclass(frozen=True, kw_only=True)
class RnaSeqInsertSizeHistogram:
    """A bin of the `.rnaseq_insert_size_histogram.txt` that `EstimateRnaSeqInsertSize` writes.

    fgbio writes this histogram line by line rather than as a metric, with one column for each pair
    orientation htsjdk knows, in lower case.
    """

    insert_size: int = 0
    """The insert size, in bases, that the bin counts read pairs at."""

    fr: int = 0
    """The number of read pairs in FR orientation with this insert size."""

    rf: int = 0
    """The number of read pairs in RF orientation with this insert size."""

    tandem: int = 0
    """The number of read pairs in tandem orientation with this insert size."""


@dataclass(frozen=True, kw_only=True)
class SwitchbackLengthHistogram:
    """A bin of the `.lengths.txt` that `FindSwitchbackReads --metrics` writes."""

    length: int = 0
    """The length of the switchback within a read-based switchback."""

    count: int = 0
    """The number of read-based switchbacks of this length."""


@dataclass(frozen=True, kw_only=True)
class SwitchbackOffsetHistogram:
    """A bin of the `.offsets.txt` that `FindSwitchbackReads --metrics` writes."""

    offset: int = 0
    """The offset of the switchback within a read-based switchback."""

    count: int = 0
    """The number of read-based switchbacks at this offset."""


@dataclass(frozen=True, kw_only=True)
class SwitchbackGapHistogram:
    """A bin of the `.gaps.txt` that `FindSwitchbackReads --metrics` writes."""

    gap_length: int = 0
    """The gap between the reads of a tandem-based switchback."""

    count: int = 0
    """The number of tandem-based switchbacks with this gap."""


HISTOGRAMS: tuple[type[Any], ...] = (
    RnaSeqInsertSizeHistogram,
    SwitchbackGapHistogram,
    SwitchbackLengthHistogram,
    SwitchbackOffsetHistogram,
)
"""The histograms fgbio writes line by line, which no fgbio metric class describes."""
