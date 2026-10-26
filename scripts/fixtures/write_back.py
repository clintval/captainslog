"""Read every Picard fixture with shipslog, and write it back, with its header, into a directory.

Run `ReadBack.java` on the directory after, to check that htsjdk reads each file as its fixture.
"""

import argparse
from collections.abc import Iterable
from contextlib import AbstractContextManager
from contextlib import nullcontext
from pathlib import Path
from typing import Any

from shipslog.picard import PicardHistogramReader
from shipslog.picard import PicardHistogramWriter
from shipslog.picard import PicardReader
from shipslog.picard import PicardWriter
from shipslog.picard import histogram_class
from shipslog.picard import metrics_class

FIXTURES = Path(__file__).parents[2] / "tests" / "data" / "picard"
METRICS_CLASS = "## METRICS CLASS"
HISTOGRAM = "## HISTOGRAM"


def holds(lines: list[str], marker: str) -> bool:
    """Whether the lines of a file hold one that starts a section with a marker."""
    return any(line.startswith(f"{marker}\t") for line in lines)


def bins_of(path: Path, histogram: type[Any] | None) -> AbstractContextManager[Iterable[Any]]:
    """Open the histogram of a file to read its bins, or open no bins when it has none."""
    if histogram is None:
        return nullcontext([])
    return PicardHistogramReader.from_path[histogram](path)


def write_metrics(path: Path, out: Path, metrics: type[Any], histogram: type[Any] | None) -> None:
    """Write the metrics of a Picard metrics file to another path, then its histogram if any."""
    with (
        PicardReader.from_path[metrics](path) as reader,
        bins_of(path, histogram) as bins,
        PicardWriter.from_path[metrics](out, header=reader.header) as writer,
    ):
        writer.write_all(reader)
        writer.write_histogram(bins)


def write_histogram(path: Path, out: Path, histogram: type[Any]) -> None:
    """Write the histogram of a Picard metrics file of only a histogram to another path."""
    with (
        PicardHistogramReader.from_path[histogram](path) as reader,
        PicardHistogramWriter.from_path[histogram](out, header=reader.header) as writer,
    ):
        writer.write_all(reader)


def main() -> None:
    """Write every Picard fixture that holds metrics or a histogram into the directory given."""
    parser = argparse.ArgumentParser(description=__doc__)
    _ = parser.add_argument("out_dir", type=Path, help="the directory to write the files into")
    out_dir: Path = parser.parse_args().out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    for path in sorted(FIXTURES.iterdir()):
        lines = path.read_text().splitlines()
        metrics = metrics_class(path) if holds(lines, METRICS_CLASS) else None
        histogram = histogram_class(path) if holds(lines, HISTOGRAM) else None
        if metrics is not None:
            write_metrics(path, out_dir / path.name, metrics, histogram)
        elif histogram is not None:
            write_histogram(path, out_dir / path.name, histogram)


if __name__ == "__main__":
    main()
