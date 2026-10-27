from typing import TextIO

from typeline import Comment
from typeline import RecordType
from typeline import TsvWriter
from typeline import WriterOptions
from typing_extensions import Unpack
from typing_extensions import override

from captainslog._binding import FromPath
from captainslog._fulcrum import FULCRUM_CODECS
from captainslog.fgumi._reader import check_fgumi_class


class FgumiWriter(TsvWriter[RecordType]):
    """A writer of a fgumi metrics file, from its fgumi dataclass.

    A float is written as fgumi writes one where that reads back as the same number: `NaN`,
    `Infinity`, and `-Infinity` for the non-finite floats, and a whole number without a point.
    Any other float is written as the shortest text that reads back as the same number.
    """

    from_path: FromPath = FromPath()  # type: ignore[assignment]  # pyright: ignore[reportIncompatibleVariableOverride]  # ty: ignore[invalid-attribute-override]

    def __init__(self, handle: TextIO, /, **options: Unpack[WriterOptions]) -> None:
        """Write the rows of a fgumi metrics file, under its header row.

        With no record written, the header row is written alone, as fgumi writes it.

        Args:
            handle: a text stream to write the file to, opened with `newline=""`.
            options: the options of the writer, left at fgumi's defaults when not given.

        Raises:
            TypeError: if the record type is not a fgumi dataclass or a subclass of one.
        """
        check_fgumi_class(self.record_type)
        _ = options.setdefault("codecs", FULCRUM_CODECS)
        _ = options.setdefault("comment_prefixes", ("\n",))
        _ = options.setdefault("header", True)
        super().__init__(handle, **options)

    @override
    def write_comment(self, comment: str | Comment) -> None:
        """Refuse a comment, since a fgumi metrics file holds none.

        Raises:
            TypeError: always.
        """
        raise TypeError("A fgumi metrics file holds no comments!")
