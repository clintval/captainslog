from typing import TextIO

from typeline import Comment
from typeline import RecordType
from typeline import TsvWriter
from typeline import WriterOptions
from typing_extensions import Unpack
from typing_extensions import override

from shipslog._binding import FromPath
from shipslog._stream import SectionStream
from shipslog._stream import as_text_io
from shipslog.riker._reader import check_riker_class


class RikerWriter(TsvWriter[RecordType]):
    """A writer of a Riker metrics file, from its Riker dataclass."""

    from_path: FromPath = FromPath()  # type: ignore[assignment]  # pyright: ignore[reportIncompatibleVariableOverride]  # ty: ignore[invalid-attribute-override]

    def __init__(self, handle: TextIO, /, **options: Unpack[WriterOptions]) -> None:
        """Write the rows of a Riker metrics file, under a header written with the first row.

        With no record written, nothing is written, as Riker writes an empty file for no rows.

        Args:
            handle: a text stream to write the file to, opened with `newline=""`.
            options: the options of the writer, left at Riker's defaults when not given.

        Raises:
            TypeError: if the record type is not a Riker dataclass or a subclass of one.
        """
        check_riker_class(self._bound_record_type())
        _ = options.setdefault("comment_prefixes", ("\n",))
        header = options.setdefault("header", True)
        super().__init__(as_text_io(SectionStream(handle, None)) if header else handle, **options)

    @override
    def write_comment(self, comment: str | Comment) -> None:
        """Refuse a comment, since a Riker metrics file holds none.

        Raises:
            TypeError: always.
        """
        raise TypeError("A Riker metrics file holds no comments!")
