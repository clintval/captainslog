"""What Riker, Picard, and fgbio share from htsjdk: the orientation of a read pair."""

from enum import StrEnum


class PairOrientation(StrEnum):
    """htsjdk's `SamPairUtil$PairOrientation`."""

    FR = "FR"
    RF = "RF"
    TANDEM = "TANDEM"
