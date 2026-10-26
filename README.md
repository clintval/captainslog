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
Each metrics class and histogram that Picard 3.5.0 writes has a dataclass, as does each table that Riker 0.5.0 writes, with the few exceptions under [Limitations](#limitations).
The readers and writers are built on [typeline](https://github.com/clintval/typeline), and are used the same way.

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
    return sum(bases for coverage, bases in pairs if coverage >= min_depth) / hs.target_territory

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

`metrics_class` names the dataclass of a file from its `## METRICS CLASS` line, and `histogram_class` names the dataclass of its histogram from its label row.
Picard reports the fraction of target bases at fixed depths, such as 50x and 100x, so the fraction at 60x comes from the depth histogram, which `columns` turns into one tuple per column.
The fraction at 50x, found the same way, equals the one Picard wrote.
The new file holds the header, the metrics, and the histogram, and reads back as the same records in shipslog and in htsjdk.

## Why shipslog

Pipelines and QC scripts read Picard and Riker metrics, often to derive new metrics from them, and many write their own parsers to do it.
[crimson](https://github.com/bow/crimson) parses Picard metrics into dictionaries: by default it reads the first 1 MiB of a file, it returns a dictionary for one row and a list for several, and it leaves `?`, `Y`, and `N` as text.
[MultiQC](https://github.com/MultiQC/MultiQC) reads Riker outputs inside its report modules.
Riker computes many of Picard's metrics in files of its own shape, so shipslog reads and writes the files of both tools, side by side.

## Quickstart

### Reading Picard Metrics

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

A reader is subscripted with the dataclass to read, as in typeline.
Fields are named for Picard's columns in lowercase snake case, and columns are matched to fields by name, in any order.
An empty cell is `None` in a field Picard may leave empty, like the `sample` of a row for all reads.
`reader.header` holds the command line and the start time of the program that wrote the file, and every other header in `others`.

Picard writes NaN and infinity as `?`, which reads back as NaN, and negative infinity as `-?`, which reads back as negative infinity:

```python
from math import isnan

from shipslog.picard import JumpingLibraryMetrics
from shipslog.picard import PicardReader

[jumps] = list(PicardReader.from_path[JumpingLibraryMetrics]("tests/data/picard/jump.jumping_metrics"))

assert isnan(jumps.jump_mean_insert_size)
```

A file of another metrics class is refused before a row is read, naming both classes, as when `hs.hs_metrics` is read as `AlignmentSummaryMetrics`:

```text
ValueError: tests/data/picard/hs.hs_metrics holds picard.analysis.directed.HsMetrics, not AlignmentSummaryMetrics!
```

A row whose first cell starts with `#`, like a library named `#1`, is still a row, since only Picard's header lines are comments.
`from_path` reads gzip, bzip2, and xz files, and files whose lines end with `\r\n`.
A reader from `from_path` closes its file once it is read to the end, so reading everything into a list needs no `with` block.

### Accumulation Levels

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

Picard writes the rows of each level that `METRIC_ACCUMULATION_LEVEL` asks for, which is `ALL_READS` by default: one row for all reads, then one for each sample, library, and read group.
It marks the level of a row only by which of its `sample`, `library`, and `read_group` cells are empty, and `accumulation_level` reads the level back.
The `read_group` of a row holds the platform unit (`PU`) of its read group, not its ID.
The GC bias metrics name their level in an `accumulation_level` column instead, and `accumulation_level` reads that column for them.

### Histograms and Columns

```python
from shipslog import picard
from shipslog.picard import InsertSizeHistogram
from shipslog.picard import PicardHistogramReader

bins = list(PicardHistogramReader.from_path[InsertSizeHistogram]("tests/data/picard/cmm.insert_size_metrics"))

assert bins[0].insert_size == 112
assert bins[0].counts["All_Reads.fr_count"] == 1

hist = picard.columns(bins)

assert hist.insert_size[:3] == (112, 128, 134)
assert hist.counts["All_Reads.fr_count"][:3] == (1, 1, 1)
assert sum(hist.counts["All_Reads.fr_count"]) == 478
```

The histogram of a file is read by its own reader, so a file that holds metrics and a histogram is read once for each.
Here the counts for all reads sum to the 478 read pairs of the all-reads row above.
A histogram whose columns depend on the data, like one count per level and pair orientation, keeps them in a dict field by column name.
`columns` transposes the bins of a histogram into one tuple per field, and a dict of tuples for the columns kept by name, with a typed result for each histogram.

Some Picard files hold only a histogram, like those of `MeanQualityByCycle` and `QualityScoreDistribution`, and are read the same way:

```python
from shipslog.picard import PicardHistogramReader
from shipslog.picard import QualityScoreDistribution

qualities = list(PicardHistogramReader.from_path[QualityScoreDistribution]("tests/data/picard/cmm.quality_distribution_metrics"))

assert qualities[0] == QualityScoreDistribution(quality=1, count_of_q=2, counts={"COUNT_OF_OQ": 0})
```

### Finding the Class of a File

```python
from shipslog import picard
from shipslog.picard import HsHistogram
from shipslog.picard import HsMetrics
from shipslog.picard import MeanQualityByCycle

assert picard.metrics_class("tests/data/picard/hs.hs_metrics") is HsMetrics
assert picard.histogram_class("tests/data/picard/hs.hs_metrics") is HsHistogram
assert picard.histogram_class("tests/data/picard/cmm.quality_by_cycle_metrics") is MeanQualityByCycle
```

`metrics_class` reads the `## METRICS CLASS` line of a file and returns the dataclass to read it with.
`histogram_class` finds the dataclass of a file's histogram by its label row, and by its metrics class when the file has one.
Each reads only the first lines of a file.
For a file that holds only a histogram, `metrics_class` raises a `ValueError` that points to `histogram_class`.
A class that Picard 3.5.0 does not write, like one that an older Picard named another way, is refused with a `ValueError`.

### Writing Picard Metrics

```python
from pathlib import Path
from tempfile import TemporaryDirectory

from shipslog.picard import InsertSizeHistogram
from shipslog.picard import InsertSizeMetrics
from shipslog.picard import PairOrientation
from shipslog.picard import PicardHeader
from shipslog.picard import PicardHistogramReader
from shipslog.picard import PicardReader
from shipslog.picard import PicardWriter

temp_dir = TemporaryDirectory()
path = Path(temp_dir.name) / "s.insert_size_metrics"
header = PicardHeader(
    command_line="CollectInsertSizeMetrics INPUT=s.bam OUTPUT=s.insert_size_metrics",
    started_on="Sat Oct 24 10:00:00 HST 2026",
)
metric = InsertSizeMetrics(read_pairs=3, mean_insert_size=150.5, pair_orientation=PairOrientation.FR)
insert_sizes = [
    InsertSizeHistogram(insert_size=150, counts={"All_Reads.fr_count": 2}),
    InsertSizeHistogram(insert_size=151, counts={"All_Reads.fr_count": 1}),
]

with PicardWriter.from_path[InsertSizeMetrics](path, header=header) as writer:
    writer.write(metric)
    writer.write_histogram(insert_sizes)

assert path.read_text().endswith(
    "## HISTOGRAM\tjava.lang.Integer\ninsert_size\tAll_Reads.fr_count\n150\t2\n151\t1\n\n"
)
assert list(PicardReader.from_path[InsertSizeMetrics](path)) == [metric]
assert list(PicardHistogramReader.from_path[InsertSizeHistogram](path)) == insert_sizes
```

A `PicardWriter` writes a file as htsjdk does: the header, the `## METRICS CLASS` line, the column labels, and a row for each record.
`write_histogram` then ends the metrics and writes the histogram after them, so one writer writes a complete file.
Without a `header`, a writer writes `shipslog` as the command line, and the local time the writer was made as the start time.
NaN and infinity are written as `?`, negative infinity as `-?`, and booleans as `Y` and `N`.
A path ending in `.gz`, `.bz2`, or `.xz` is written compressed.
Writing is also a quick way to make realistic Picard files for unit tests.

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

CollectHsMetrics and CollectTargetedPcrMetrics write the coverage of each target to `PER_TARGET_COVERAGE`, and of each target base to `PER_BASE_COVERAGE`, as plain tables without a Picard header.
They are read into `PerTargetCoverage` and `PerBaseCoverage` with a `PicardCoverageReader`, and written with a `PicardCoverageWriter`.
The `%gc` column is the `pct_gc` field.

### Reading and Writing Riker Metrics

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

Riker writes one plain table per file, with lowercase column names and the `sample` column first.
`riker.metrics_class` names the dataclass of a file by the suffix Riker gives its path, like `.hybcap-metrics.txt`, and reads no file.
The dataclasses are named after these suffixes, so a `.isize-histogram.txt` file is read into an `IsizeHistogram`.
Riker's histograms are tables of their own, and `riker.columns` transposes them as `picard.columns` does.
A Riker file of no rows is empty, and reads as no records.
A `RikerWriter` given no records writes an empty file, as Riker does.

The Picard and Riker dataclasses are kept apart on purpose.
Riker renames many of Picard's metrics, and some that keep Picard's name mean something else.
For example, `total_reads` counts every read examined in Picard's `HsMetrics`, but leaves out the reads that fail the vendor filter in Riker's `HybcapMetrics`.

### Deriving Metrics

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

To derive metrics, subclass a dataclass, add properties or methods, and read into the subclass.
Readers, writers, and `columns` take a subclass as the dataclass it extends, for Picard and Riker alike.
Add no dataclass fields, since every field is a column, and a file must hold only the columns that Picard or Riker writes.

### Supported Versions

shipslog 0.1.0 reads and writes the files of Picard 3.5.0 and Riker 0.5.0.
A file whose columns differ, from an older or a newer release, is refused with a `ValueError` that names the columns missing from the file and those it does not expect.
A release of shipslog that follows a newer Picard or Riker names it here.

### Limitations

- `HsMetrics` and `TargetedPcrMetrics` histograms are supported as Picard 3.5.0 writes them, at the `ALL_READS` level.
  Picard 3.5.0 throws when either tool is asked for any other accumulation level.
- An `InsertSizeMetrics` or `RnaSeqMetrics` histogram where a sample and a library share a name repeats a column name, such as `NA12891.fr_count`.
  typeline refuses the repeated name with a `ValueError` when the histogram is read.
- The `MATRIX_OUTPUT` file of CollectIndependentReplicateMetrics has no histogram class, because Java writes its key with `toString`.
- Writers write each float as the shortest text that reads back as the same number, such as `0.30000000000000004` or `1e-7`.
  They do not round to htsjdk's six places or to Riker's fixed places, and htsjdk reads either form.
- Writers put the columns a histogram keeps by name after its fixed columns.
  A `DuplicationMetrics` histogram's `optical_sets` therefore moves to the end of the row, and htsjdk reads it by its label.
- A `RikerWriter` path ending in `.bgz` is written uncompressed.
  Name gzipped Riker files `.gz`, as Riker itself does.

## Development and Testing

See the [contributing guide](./CONTRIBUTING.md) for more information.
