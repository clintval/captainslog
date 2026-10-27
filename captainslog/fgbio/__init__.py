"""Typed metrics for the files that fgbio writes."""

from captainslog.fgbio import _metrics
from captainslog.fgbio._histograms import RnaSeqInsertSizeHistogram
from captainslog.fgbio._histograms import SwitchbackGapHistogram
from captainslog.fgbio._histograms import SwitchbackLengthHistogram
from captainslog.fgbio._histograms import SwitchbackOffsetHistogram
from captainslog.fgbio._metrics import *  # noqa: F403
from captainslog.fgbio._reader import FgbioReader
from captainslog.fgbio._reader import metrics_class
from captainslog.fgbio._writer import FgbioWriter

__all__: list[str] = [
    "FgbioReader",
    "FgbioWriter",
    "RnaSeqInsertSizeHistogram",
    "SwitchbackGapHistogram",
    "SwitchbackLengthHistogram",
    "SwitchbackOffsetHistogram",
    "metrics_class",
]
__all__ += _metrics.__all__
