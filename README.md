![Banner for captainslog](https://raw.githubusercontent.com/clintval/captainslog/main/.github/img/captainslog_banner.svg)

---

[![PyPi Release](https://badge.fury.io/py/captainslog-ngs.svg)](https://pypi.org/project/captainslog-ngs/)
[![CI](https://github.com/clintval/captainslog/actions/workflows/tests.yml/badge.svg?branch=main)](https://github.com/clintval/captainslog/actions/workflows/tests.yml?query=branch%3Amain)
[![Python Versions](https://img.shields.io/badge/python-3.11_|_3.12_|_3.13_|_3.14-blue)](https://github.com/clintval/captainslog)
[![basedpyright](https://img.shields.io/badge/basedpyright-checked-42b983)](https://docs.basedpyright.com/latest/)
[![mypy](https://www.mypy-lang.org/static/mypy_badge.svg)](https://mypy-lang.org/)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://docs.astral.sh/uv/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://docs.astral.sh/ruff/)

Typed dataclasses for the metrics files that Riker and Picard write.

Open a [Riker](https://github.com/fulcrumgenomics/riker) or [Picard](https://github.com/broadinstitute/picard) metrics file, plain or compressed, and get a list of frozen dataclasses with typed fields.
Integer columns are `int`, decimal columns are `float`, `Y` and `N` are `bool`, categorical columns are enumerations, and Picard's `?` is NaN.

## Installation

The package can be installed with `pip`:

```console
pip install captainslog-ngs
```

## At a Glance

Read two Riker metrics files from the same run, and combine their typed fields without casting:

```python
from captainslog.riker import AlignmentMetrics
from captainslog.riker import IsizeMetrics
from captainslog.riker import ReadCategory
from captainslog.riker import RikerReader

with (
    RikerReader.from_path[AlignmentMetrics]("tests/data/riker/s.alignment-metrics.txt") as alignments,
    RikerReader.from_path[IsizeMetrics]("tests/data/riker/s.isize-metrics.txt") as isizes,
):
    alignment = {row.category: row for row in alignments}
    [isize] = isizes

frac_reads_in_fr_pairs = 2 * isize.read_pairs / alignment[ReadCategory.PAIR].total_reads

assert round(frac_reads_in_fr_pairs, 3) == 0.972
```

## Quickstart

### Reading Riker Metrics

A `RikerReader` reads a Riker metrics file into dataclasses, one per row.

```python
from captainslog import riker
from captainslog.riker import HybcapMetrics
from captainslog.riker import IsizeHistogram

assert riker.metrics_class("tests/data/riker/s.hybcap-metrics.txt") is HybcapMetrics

with RikerReader.from_path[HybcapMetrics]("tests/data/riker/s.hybcap-metrics.txt") as reader:
    [hybcap] = reader

assert hybcap.sample == "NA12891"
assert hybcap.mean_target_coverage == 70.54

with RikerReader.from_path[IsizeHistogram]("tests/data/riker/s.isize-histogram.txt") as reader:
    isize = riker.columns(list(reader))

assert isize.insert_size[:3] == (112, 128, 134)
assert isize.fr_count[:3] == (1, 1, 1)
```

### Reading Picard Metrics

A `PicardReader` reads a Picard metrics file into dataclasses, one per row.

```python
from captainslog.picard import HsMetrics
from captainslog.picard import PicardReader

with PicardReader.from_path[HsMetrics]("tests/data/picard/hs.hs_metrics") as reader:
    [hs_metrics] = reader

assert hs_metrics.mean_target_coverage == 70.54
assert hs_metrics.hs_library_size == 14903
assert reader.header.command_line.startswith("CollectHsMetrics BAIT_INTERVALS=")
assert reader.header.started_on == "Sat Oct 24 21:42:22 HST 2026"
```

> [!TIP]
> A Picard column named for a percent that holds a fraction from 0 to 1 is a `frac` field, such as `frac_pf_reads_aligned` for `PCT_PF_READS_ALIGNED`.
> Writing the metrics back out keeps Picard's label for each `frac` field.

### Writing Metrics

Each reader has a writer, which makes realistic files for unit tests:

- `RikerWriter`
- `PicardWriter`, with `write_histogram`
- `PicardHistogramWriter`
- `PicardCoverageWriter`

```python
from pathlib import Path
from tempfile import TemporaryDirectory

from captainslog.picard import PicardWriter

temp_dir = TemporaryDirectory()
path = Path(temp_dir.name) / "s.hs_metrics"

with PicardWriter.from_path[HsMetrics](path) as writer:
    writer.write(hs_metrics)

with PicardReader.from_path[HsMetrics](path) as reader:
    assert list(reader) == [hs_metrics]
```

### Interacting with Metrics

#### Finding the Class of a File

The `metrics_class` and `histogram_class` functions return the metric type in a data file.

```python
from captainslog import picard
from captainslog.picard import HsHistogram
from captainslog.picard import MeanQualityByCycle

assert picard.metrics_class("tests/data/picard/hs.hs_metrics") is HsMetrics
assert picard.histogram_class("tests/data/picard/hs.hs_metrics") is HsHistogram
assert picard.histogram_class("tests/data/picard/cmm.quality_by_cycle_metrics") is MeanQualityByCycle
```

#### Histograms and Columns

A `PicardHistogramReader` reads the histogram of a file into one dataclass per bin, and `columns` transposes the bins into one tuple per column.
For the histograms whose columns Picard names after samples, libraries, and read groups, these functions turn the columns into typed series and the series back into bins:

- `insert_size_series` and `insert_size_bins`, for an `InsertSizeHistogram`
- `rna_coverage_series` and `rna_coverage_bins`, for an `RnaCoverageHistogram`
- `library_complexity_series` and `library_complexity_bins`, for a `LibraryComplexityHistogram`

```python
from captainslog.picard import InsertSizeHistogram
from captainslog.picard import PairOrientation
from captainslog.picard import PicardHistogramReader

with PicardHistogramReader.from_path[InsertSizeHistogram]("tests/data/picard/cmm.insert_size_metrics") as reader:
    hist = picard.columns(list(reader))

assert hist.insert_size[:3] == (112, 128, 134)

series = picard.insert_size_series(hist)
all_reads = next(s for s in series if s.name is None and s.orientation is PairOrientation.FR)

assert all_reads.counts[:3] == (1, 1, 1)
assert sum(all_reads.counts) == 478
assert [s.name for s in series] == [None, "NA12891", "Pond-492101", "NormPond-544932", "NA12891.r1", "NA12891.r2"]
```

Histogram-only files read the same way:

```python
from captainslog.picard import QualityScoreDistribution

with PicardHistogramReader.from_path[QualityScoreDistribution]("tests/data/picard/cmm.quality_distribution_metrics") as reader:
    qualities = list(reader)

assert qualities[0].quality == 1
assert qualities[0].count_of_q == 2
```

#### Accumulation Levels

Picard writes a row for each accumulation level: all reads, then each sample, library, and read group.

```python
from captainslog.picard import AccumulationLevel
from captainslog.picard import InsertSizeMetrics

with PicardReader.from_path[InsertSizeMetrics]("tests/data/picard/cmm.insert_size_metrics") as reader:
    rows = list(reader)

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

### Per-Target and Per-Base Coverage

CollectHsMetrics and CollectTargetedPcrMetrics can also write plain tables of coverage per target and per base.

```python
from captainslog.picard import PerTargetCoverage
from captainslog.picard import PicardCoverageReader

with PicardCoverageReader.from_path[PerTargetCoverage]("tests/data/picard/hs.per_target_coverage.txt") as reader:
    targets = list(reader)

assert targets[0].name == "rs7555566"
assert targets[0].frac_gc == 0.41
```

### Deriving Metrics

To derive metrics, subclass a dataclass, add properties or methods, and read into the subclass.

```python
class MyHsMetrics(HsMetrics):
    @property
    def frac_bases_on_target(self) -> float:
        return self.on_target_bases / self.pf_bases_aligned

with PicardReader.from_path[MyHsMetrics]("tests/data/picard/hs.hs_metrics") as reader:
    [hs_metrics] = reader

assert round(hs_metrics.frac_bases_on_target, 4) == 0.2398
```

## Intervals with bedspec

The [bedspec](https://github.com/clintval/bedspec) package reads the targets, bases, SNPs, and CpGs of captainslog as 0-based, half-open intervals, so they work with its overlap detectors:

<!-- skip: next -->
```python
from bedspec import Bed3
from bedspec import register_locatable
from bedspec.ext.captainslog import as_interval
from bedspec.overlap import TreeDetector

with (
    register_locatable(PerTargetCoverage, as_interval),
    PicardCoverageReader.from_path[PerTargetCoverage]("tests/data/picard/hs.per_target_coverage.txt") as reader,
):
    targets = TreeDetector(reader)
    [target] = targets.overlapping(Bed3("1", start=200, end=201))

assert target.name == "rs7555566"
```

## Development and Testing

See the [contributing guide](./CONTRIBUTING.md) for more information.
