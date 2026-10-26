![Banner for shipslog](https://raw.githubusercontent.com/clintval/shipslog/main/.github/img/shipslog_banner.svg)

---

[![PyPi Release](https://badge.fury.io/py/shipslog.svg)](https://badge.fury.io/py/shipslog)
[![CI](https://github.com/clintval/shipslog/actions/workflows/tests.yml/badge.svg?branch=main)](https://github.com/clintval/shipslog/actions/workflows/tests.yml?query=branch%3Amain)
[![Python Versions](https://img.shields.io/badge/python-3.11_|_3.12_|_3.13_|_3.14-blue)](https://github.com/clintval/shipslog)
[![basedpyright](https://img.shields.io/badge/basedpyright-checked-42b983)](https://docs.basedpyright.com/latest/)
[![mypy](https://www.mypy-lang.org/static/mypy_badge.svg)](https://mypy-lang.org/)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://docs.astral.sh/uv/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://docs.astral.sh/ruff/)

Typed dataclasses for the metrics files that Picard and Riker write.

Open a Picard or Riker metrics file and get a list of frozen dataclasses with typed fields, do arithmetic on them without casting, and write them back out.
Integer columns are `int`, decimal columns are `float`, `Y` and `N` are `bool`, categorical columns are enums, and Picard's `?` is NaN.
Each metrics class and histogram that Picard writes has a dataclass, as does each table that Riker writes.

## Installation

The package can be installed with `pip`:

```console
pip install shipslog
```

## At a Glance

Find the type of a Picard file, derive a coverage metric that Picard does not report from its histogram, and write its metrics and histogram to a new Picard file:

```python
from pathlib import Path
from tempfile import TemporaryDirectory

from shipslog import picard
from shipslog.picard import PicardHistogramReader
from shipslog.picard import PicardReader
from shipslog.picard import PicardWriter

path = Path("tests/data/picard/hs.hs_metrics")
metrics_type = picard.metrics_class(path)
histogram_type = picard.histogram_class(path)

with PicardReader.from_path[metrics_type](path) as reader:
    [hs] = list(reader)

bins = list(PicardHistogramReader.from_path[histogram_type](path))
depth = picard.columns(bins)

def frac_target_bases(min_depth: int) -> float:
    pairs = zip(depth.coverage_or_base_quality, depth.high_quality_coverage_count, strict=True)
    covered = sum(bases for coverage, bases in pairs if coverage >= min_depth)
    return float(covered / hs.target_territory)

assert frac_target_bases(50) == hs.pct_target_bases_50x
assert frac_target_bases(60) == 0.862

temp_dir = TemporaryDirectory()
out = Path(temp_dir.name) / "hs.hs_metrics"

with PicardWriter.from_path[metrics_type](out, header=reader.header) as writer:
    writer.write(hs)
    writer.write_histogram(bins)

assert list(PicardReader.from_path[metrics_type](out)) == [hs]
assert list(PicardHistogramReader.from_path[histogram_type](out)) == bins
```

## Quickstart

Each example below runs as written against the test files in this repository.

### Reading Picard Metrics

`PicardReader` reads a Picard metrics file, plain or compressed, into a list of dataclasses.
`reader.header` holds the command line and start time of the program that wrote it.

```python
from shipslog.picard import HsMetrics
from shipslog.picard import PicardReader

with PicardReader.from_path[HsMetrics]("tests/data/picard/hs.hs_metrics") as reader:
    [hs] = list(reader)

assert hs.mean_target_coverage == 70.54
assert hs.hs_library_size == 14903
assert reader.header.command_line.startswith("CollectHsMetrics BAIT_INTERVALS=")
assert reader.header.started_on == "Sat Oct 24 21:42:22 HST 2026"
```

Picard's `?` reads back as NaN:

```python
from math import isnan

from shipslog.picard import JumpingLibraryMetrics
from shipslog.picard import PicardReader

[jumps] = list(PicardReader.from_path[JumpingLibraryMetrics]("tests/data/picard/jump.jumping_metrics"))

assert isnan(jumps.jump_mean_insert_size)
```

### Accumulation Levels

Picard writes a row for each accumulation level it is asked for: all reads, then each sample, library, and read group.
`accumulation_level` reads back the level of a row.

```python
from shipslog import picard
from shipslog.picard import AccumulationLevel
from shipslog.picard import InsertSizeMetrics
from shipslog.picard import PairOrientation
from shipslog.picard import PicardReader

rows = list(PicardReader.from_path[InsertSizeMetrics]("tests/data/picard/cmm.insert_size_metrics"))

assert [picard.accumulation_level(row) for row in rows] == [
    AccumulationLevel.ALL_READS,
    AccumulationLevel.SAMPLE,
    AccumulationLevel.LIBRARY,
    AccumulationLevel.LIBRARY,
    AccumulationLevel.READ_GROUP,
    AccumulationLevel.READ_GROUP,
]

[all_reads] = [row for row in rows if picard.accumulation_level(row) is AccumulationLevel.ALL_READS]

assert all_reads.read_pairs == 478
assert all_reads.pair_orientation is PairOrientation.FR
```

### Histograms and Columns

`PicardHistogramReader` reads the histogram of a file into one dataclass per bin, and `columns` transposes the bins into one tuple per column.
`insert_size_series`, `rna_coverage_series`, and `library_complexity_series` turn the columns Picard names after samples, libraries, and read groups into typed series, and `insert_size_bins` and its siblings turn series back into bins.

```python
from shipslog import picard
from shipslog.picard import InsertSizeHistogram
from shipslog.picard import PairOrientation
from shipslog.picard import PicardHistogramReader

bins = list(PicardHistogramReader.from_path[InsertSizeHistogram]("tests/data/picard/cmm.insert_size_metrics"))
hist = picard.columns(bins)

assert hist.insert_size[:3] == (112, 128, 134)

series = picard.insert_size_series(hist)
all_reads = next(s for s in series if s.name is None and s.orientation is PairOrientation.FR)

assert all_reads.counts[:3] == (1, 1, 1)
assert sum(all_reads.counts) == 478
assert [s.name for s in series] == [None, "NA12891", "Pond-492101", "NormPond-544932", "NA12891.r1", "NA12891.r2"]
```

A file that holds only a histogram, like a `QualityScoreDistribution`, is read the same way:

```python
from shipslog.picard import PicardHistogramReader
from shipslog.picard import QualityScoreDistribution

qualities = list(PicardHistogramReader.from_path[QualityScoreDistribution]("tests/data/picard/cmm.quality_distribution_metrics"))

assert qualities[0].quality == 1
assert qualities[0].count_of_q == 2
```

### Finding the Class of a File

`metrics_class` names the dataclass of a file from its `## METRICS CLASS` line.
`histogram_class` names the dataclass of its histogram from its label row.

```python
from shipslog import picard
from shipslog.picard import HsHistogram
from shipslog.picard import HsMetrics
from shipslog.picard import MeanQualityByCycle

assert picard.metrics_class("tests/data/picard/hs.hs_metrics") is HsMetrics
assert picard.histogram_class("tests/data/picard/hs.hs_metrics") is HsHistogram
assert picard.histogram_class("tests/data/picard/cmm.quality_by_cycle_metrics") is MeanQualityByCycle
```

### Writing Picard Metrics

`PicardWriter` writes a complete Picard file as htsjdk does: the header, the metrics, and with `write_histogram`, the histogram.
It is also a quick way to make realistic Picard files for unit tests.

```python
from pathlib import Path
from tempfile import TemporaryDirectory

from shipslog.picard import InsertSizeHistogram
from shipslog.picard import InsertSizeMetrics
from shipslog.picard import InsertSizeSeries
from shipslog.picard import PairOrientation
from shipslog.picard import PicardHeader
from shipslog.picard import PicardHistogramReader
from shipslog.picard import PicardReader
from shipslog.picard import PicardWriter
from shipslog.picard import insert_size_bins

temp_dir = TemporaryDirectory()
path = Path(temp_dir.name) / "s.insert_size_metrics"
header = PicardHeader(
    command_line="CollectInsertSizeMetrics INPUT=s.bam OUTPUT=s.insert_size_metrics",
    started_on="Sat Oct 24 10:00:00 HST 2026",
)
metric = InsertSizeMetrics(read_pairs=3, mean_insert_size=150.5, pair_orientation=PairOrientation.FR)
insert_sizes = insert_size_bins([
    InsertSizeSeries(name=None, orientation=PairOrientation.FR, insert_size=(150, 151), counts=(2, 1)),
])

with PicardWriter.from_path[InsertSizeMetrics](path, header=header) as writer:
    writer.write(metric)
    writer.write_histogram(insert_sizes)

assert path.read_text().endswith(
    "## HISTOGRAM\tjava.lang.Integer\ninsert_size\tAll_Reads.fr_count\n150\t2\n151\t1\n\n"
)
assert list(PicardReader.from_path[InsertSizeMetrics](path)) == [metric]
assert list(PicardHistogramReader.from_path[InsertSizeHistogram](path)) == insert_sizes
```

A file of only a histogram is written with a `PicardHistogramWriter`:

```python
from pathlib import Path
from tempfile import TemporaryDirectory

from shipslog.picard import PicardHeader
from shipslog.picard import PicardHistogramWriter
from shipslog.picard import QualityScoreDistribution

temp_dir = TemporaryDirectory()
path = Path(temp_dir.name) / "s.quality_distribution_metrics"
header = PicardHeader(
    command_line="QualityScoreDistribution INPUT=s.bam OUTPUT=s.quality_distribution_metrics",
    started_on="Sat Oct 24 10:00:00 HST 2026",
)

with PicardHistogramWriter.from_path[QualityScoreDistribution](path, header=header) as writer:
    writer.write(QualityScoreDistribution(quality=30, count_of_q=5))
    writer.write(QualityScoreDistribution(quality=37, count_of_q=9))

assert path.read_text() == (
    "## htsjdk.samtools.metrics.StringHeader\n"
    "# QualityScoreDistribution INPUT=s.bam OUTPUT=s.quality_distribution_metrics\n"
    "## htsjdk.samtools.metrics.StringHeader\n"
    "# Started on: Sat Oct 24 10:00:00 HST 2026\n"
    "\n"
    "\n"
    "## HISTOGRAM\tjava.lang.Byte\n"
    "QUALITY\tCOUNT_OF_Q\n"
    "30\t5\n"
    "37\t9\n"
    "\n"
)
```

### Per-Target and Per-Base Coverage

CollectHsMetrics and CollectTargetedPcrMetrics can also write plain tables of coverage per target and per base.
`PicardCoverageReader` and `PicardCoverageWriter` read and write them.

```python
from pathlib import Path
from tempfile import TemporaryDirectory

from shipslog.picard import PerTargetCoverage
from shipslog.picard import PicardCoverageReader
from shipslog.picard import PicardCoverageWriter

targets = list(PicardCoverageReader.from_path[PerTargetCoverage]("tests/data/picard/hs.per_target_coverage.txt"))

assert targets[0].name == "rs7555566"
assert targets[0].pct_gc == 0.41

temp_dir = TemporaryDirectory()
path = Path(temp_dir.name) / "s.per_target_coverage.txt"

with PicardCoverageWriter.from_path[PerTargetCoverage](path) as writer:
    writer.write_all(targets)

assert path.read_text().startswith("chrom\tstart\tend\tlength\tname\t%gc\tmean_coverage\t")
assert list(PicardCoverageReader.from_path[PerTargetCoverage](path)) == targets
```

### Reading and Writing Riker Metrics

`RikerReader` and `RikerWriter` read and write Riker's plain tables.
`riker.metrics_class` names the dataclass of a file by the suffix Riker gives it, and `riker.columns` transposes Riker's histograms.

```python
from pathlib import Path
from tempfile import TemporaryDirectory

from shipslog import riker
from shipslog.riker import HybcapMetrics
from shipslog.riker import IsizeHistogram
from shipslog.riker import RikerReader
from shipslog.riker import RikerWriter

assert riker.metrics_class("tests/data/riker/s.hybcap-metrics.txt") is HybcapMetrics

[hybcap] = list(RikerReader.from_path[HybcapMetrics]("tests/data/riker/s.hybcap-metrics.txt"))

assert hybcap.sample == "NA12891"
assert hybcap.mean_target_coverage == 70.54

isize = riker.columns(list(RikerReader.from_path[IsizeHistogram]("tests/data/riker/s.isize-histogram.txt")))

assert isize.insert_size[:3] == (112, 128, 134)
assert isize.fr_count[:3] == (1, 1, 1)

temp_dir = TemporaryDirectory()
path = Path(temp_dir.name) / "s.hybcap-metrics.txt"

with RikerWriter.from_path[HybcapMetrics](path) as writer:
    writer.write(hybcap)

assert list(RikerReader.from_path[HybcapMetrics](path)) == [hybcap]
```

### Deriving Metrics

To derive metrics, subclass a dataclass, add properties or methods, and read into the subclass.
Add no fields, since every field is a column of the file.

```python
from shipslog.picard import HsMetrics
from shipslog.picard import PicardReader

class MyHsMetrics(HsMetrics):
    @property
    def frac_bases_on_target(self) -> float:
        return self.on_target_bases / self.pf_bases_aligned

[hs] = list(PicardReader.from_path[MyHsMetrics]("tests/data/picard/hs.hs_metrics"))

assert round(hs.frac_bases_on_target, 4) == 0.2398
```

## Development and Testing

See the [contributing guide](./CONTRIBUTING.md) for more information.
