import bz2
import gzip
import lzma
from io import BufferedReader
from pathlib import Path
from typing import NoReturn

import pytest

from shipslog._files import DECOMPRESSORS
from shipslog._files import open_text

TEXT = "## htsjdk.samtools.metrics.StringHeader\r\n# Started on: today\n\u00b5\t\u03b2\n"


def test_open_text_reads_plain_and_compressed_files_alike(tmp_path: Path) -> None:
    """A file reads as the same UTF-8 text, line breaks and all, whether it is compressed or not."""
    data = TEXT.encode("utf-8")
    compressed = {
        "plain": data,
        "gzip": gzip.compress(data),
        "bzip2": bz2.compress(data),
        "xz": lzma.compress(data),
    }
    for name, content in compressed.items():
        path = tmp_path / f"{name}.txt"
        _ = path.write_bytes(content)
        with open_text(path) as handle:
            assert handle.read() == TEXT, name
            assert handle.name == str(path), name
        assert handle.closed, name


def test_open_text_closes_the_file_when_it_cannot_decompress_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A file whose text cannot be read is closed before the error is raised."""
    path = tmp_path / "gzip.txt"
    _ = path.write_bytes(gzip.compress(TEXT.encode("utf-8")))
    sources: list[BufferedReader] = []

    def refuse(source: BufferedReader) -> NoReturn:
        sources.append(source)
        raise OSError("cannot decompress")

    monkeypatch.setitem(DECOMPRESSORS, b"\x1f\x8b", refuse)
    with pytest.raises(OSError, match="cannot decompress"):
        _ = open_text(path)
    assert [source.closed for source in sources] == [True]
