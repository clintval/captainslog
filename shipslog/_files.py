import bz2
import gzip
import io
import lzma
from collections.abc import Callable
from pathlib import Path
from typing import Any
from typing import TextIO

from typing_extensions import override

DECOMPRESSORS: dict[bytes, Callable[[io.BufferedReader], Any]] = {
    b"\x1f\x8b": lambda source: gzip.GzipFile(fileobj=source),
    b"BZh": bz2.BZ2File,
    b"\xfd7zXZ\x00": lzma.LZMAFile,
}
"""How to decompress a file, by the first bytes of each compression format."""


class _TextFile(io.TextIOWrapper):
    """UTF-8 text read from a file, named after the file and closing it when closed."""

    def __init__(self, stream: Any, source: io.BufferedReader) -> None:
        super().__init__(stream, encoding="utf-8", newline="")
        self._source: io.BufferedReader = source

    @property
    @override
    def name(self) -> Any:
        return self._source.name

    @override
    def close(self) -> None:
        try:
            super().close()
        finally:
            self._source.close()


def open_text(path: Path | str) -> TextIO:
    """Open a file to read as UTF-8 text, decompressing it when it is gzip, bzip2, or xz.

    Args:
        path: the path to the file.
    """
    source = Path(path).expanduser().open("rb")
    try:
        start = source.peek(max(map(len, DECOMPRESSORS)))
        decompress = next(
            (decompress for magic, decompress in DECOMPRESSORS.items() if start.startswith(magic)),
            None,
        )
        return _TextFile(source if decompress is None else decompress(source), source)
    except BaseException:
        source.close()
        raise
