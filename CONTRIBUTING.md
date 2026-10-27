# Development and Testing

## Setup

Install [uv](https://docs.astral.sh/uv/), then install the library and its development tools:

```console
uv sync
```

## Primary Development Commands

To check and resolve linting issues in the codebase, run:

```console
uv run ruff check --fix
```

To check and resolve formatting issues in the codebase, run:

```console
uv run ruff format
```

To check the unit tests in the codebase, run:

```console
uv run pytest
```

To check the typing in the codebase, run:

```console
uv run mypy && uv run basedpyright && uv run ty check
```

To generate a code coverage report after testing locally, run:

```console
uv run coverage html
```

To check the lock file is up-to-date:

```console
uv lock --check
```

## Shortcut Task Commands

### For Running Individual Checks

```console
uv run poe check-lock
uv run poe check-pyproject
uv run poe check-format
uv run poe check-lint
uv run poe check-tests
uv run poe check-typing
```

### For Running All Checks

```console
uv run poe check-all
```

### For Running Individual Fixes

```console
uv run poe fix-format
uv run poe fix-lint
```

### For Running All Fixes

```console
uv run poe fix-all
```

### For Running All Fixes and Checks

```console
uv run poe fix-and-check-all
```

## Regenerating the Riker and Picard Fixtures

The files in `tests/data/picard` and `tests/data/riker` are written by Picard 3.5.0 and Riker 0.5.0, from inputs in Picard's own test data.
To write them again, install [pixi](https://pixi.sh), then run `make.sh` in the environment of `scripts/fixtures/pixi.toml`, which holds Riker, Picard, samtools, and Java:

```console
pixi run --manifest-path scripts/fixtures/pixi.toml bash scripts/fixtures/make.sh
```

The script downloads its inputs from Picard's repository at the 3.5.0 tag, runs each tool, and replaces both directories.

## Regenerating the Picard Dataclasses

The Picard dataclasses in `captainslog/picard/_metrics.py`, and their Java names and column labels in `captainslog/picard/_java.py`, are generated, so change the generator rather than the files.
The script `scripts/picard/PicardSchema.java` prints the metrics classes of a Picard jar as JSON, with the columns htsjdk writes for each and the constants of their enumerations:

```console
pixi run --manifest-path scripts/fixtures/pixi.toml bash -c 'java -cp "$PICARD_JAR" scripts/picard/PicardSchema.java "$PICARD_JAR" > scripts/picard/picard-3.5.0.json'
```

The generator, `scripts/picard/generate.py`, writes both modules from that JSON, with docstrings from the Javadoc of a checkout of Picard's source at the same release:

```console
git clone --depth 1 --branch 3.5.0 https://github.com/broadinstitute/picard.git /tmp/picard
uv run python scripts/picard/generate.py --schema scripts/picard/picard-3.5.0.json --source /tmp/picard --output captainslog/picard
```

The table in `scripts/picard/units.json` classifies each field whose name holds `PCT` or `PERCENT` as a `fraction` from 0 to 1, a `percent` from 0 to 100, `none` when the word is not its unit, or `unknown`, with the line of Picard's source that sets it.
The generator names a fraction `frac` in place of `pct` or `percent`, maps it to Picard's label in `COLUMN_LABELS`, and says the unit in its docstring.
It refuses to run while a field is missing from the table, so classify each new one from where Picard computes it, never from its name.
The generator's `COORDINATE_BASES` says whether a position or cycle is 0-based or 1-based where its Javadoc does not, so settle each new one from where Picard sets it.
Its `SHARED_ENUMS` imports `PairOrientation` from `captainslog/_htsjdk.py` rather than declaring it, since fgbio and Riker write it too, and refuses to run unless that class holds the constants Picard writes.

For a new Picard release, set its version in `scripts/fixtures/make.sh` and `scripts/fixtures/pixi.toml`, along with the package build that the path of `PICARD_JAR` names, then update the lock with `pixi lock --manifest-path scripts/fixtures/pixi.toml`.
Write its schema to a new `scripts/picard/picard-X.Y.Z.json`, name that file in `pyproject.toml` and `tests/picard/test_metrics.py`, check the source lines in `scripts/picard/units.json` against the new release, generate the modules from it, and regenerate the fixtures.
Running `git grep -n -F 3.5.0 -- ':!*.lock' ':!tests/data'` lists every other place that names the release, such as the errors in `captainslog/picard/_reader.py` and this guide.
The histograms in `captainslog/picard/_histograms.py` are written by hand, so check them against the new release too.

## Regenerating the fgbio Dataclasses

The fgbio dataclasses in `captainslog/fgbio/_metrics.py`, and their Scala names in `captainslog/fgbio/_scala.py`, are generated, so change the generator rather than the files.
The script `scripts/fgbio/FgbioSchema.java` prints the metric classes of an fgbio jar as JSON, with the constructor parameters that `Metric.write` writes as columns and the entries of their enumerations.
It reads the parameters with Scala reflection, since Java's erases `Option[Double]` to `Option<Object>`:

```console
pixi run --manifest-path scripts/fixtures/pixi.toml bash -c 'java -cp "$FGBIO_JAR" scripts/fgbio/FgbioSchema.java "$FGBIO_JAR" > scripts/fgbio/fgbio-4.1.1.json'
```

The generator, `scripts/fgbio/generate.py`, writes both modules from that JSON, with docstrings from the Scaladoc of a checkout of fgbio's source at the same release:

```console
git clone --depth 1 --branch 4.1.1 https://github.com/fulcrumgenomics/fgbio.git /tmp/fgbio
uv run python scripts/fgbio/generate.py --schema scripts/fgbio/fgbio-4.1.1.json --source /tmp/fgbio --output captainslog/fgbio
```

The generator's `SKIPPED` names the classes that extend `Metric` only to be read as tables, such as the primer pairs of `AssignPrimers`, and refuses to run while one of them is gone from the jar.
Its `FALLBACK_DOCS` documents a field the Scaladoc leaves out, and its `COORDINATE_BASES` says whether a position is 0-based or 1-based where the Scaladoc does not, so settle each new one from where fgbio sets it.
Its `SHARED_ENUMS` imports `PairOrientation` from `captainslog/_htsjdk.py` and `ReadType` from `captainslog/_fulcrum.py` rather than declaring them, and refuses to run unless each holds the entries fgbio writes.
The histograms in `captainslog/fgbio/_histograms.py`, which fgbio writes line by line rather than as metrics, are written by hand, so check them against each new release too.

## Regenerating the fgumi Dataclasses

The fgumi dataclasses in `captainslog/fgumi/_metrics.py`, with their Rust sources and metrics files in `captainslog/fgumi/_rust.py`, are generated from a checkout of fgumi's source:

```console
git clone --depth 1 --branch v0.8.0 https://github.com/fulcrumgenomics/fgumi.git /tmp/fgumi
uv run python scripts/fgumi/generate.py --source /tmp/fgumi --output captainslog/fgumi --manifest scripts/fgumi/fgumi-0.8.0.json
```

fgumi publishes the columns of every metrics file it writes in `crates/fgumi-metrics/metric_columns.json`, and its integration test `test_metric_contract.rs` pairs each file with the struct that writes it.
The generator reads the fields, types, and doc comments of each struct, follows serde's `rename` and `skip`, and refuses to run unless the columns it finds are the published columns of every file.
It copies the published columns to `scripts/fgumi/fgumi-0.8.0.json`, which the tests check the dataclasses against.
Its `SHARED_ENUMS` imports `ReadType` from `captainslog/_fulcrum.py` rather than declaring it, since fgbio writes it too, and refuses to run unless that class holds the variants fgumi writes.

## Regenerating the fgbio and fgumi Fixtures

The files in `tests/data/fgbio` and `tests/data/fgumi` are written by fgbio 4.1.1 and fgumi 0.8.0 from reads that `scripts/fixtures/simulate_umis.py` simulates and bwa aligns, so no input is downloaded:

```console
pixi run --manifest-path scripts/fixtures/pixi.toml bash scripts/fixtures/make_fg.sh
```

The script replaces only those two directories, and writes them byte for byte the same on each run.

## Checking Written Files with htsjdk

The script `scripts/fixtures/write_back.py` reads every Picard fixture with captainslog and writes it back into a directory, with its header, metrics, and histogram.
Then `scripts/fixtures/ReadBack.java` checks that htsjdk reads each written file as the metrics and histogram of its fixture:

```console
uv run python scripts/fixtures/write_back.py /tmp/written
pixi run --manifest-path scripts/fixtures/pixi.toml bash -c 'java -cp "$PICARD_JAR" scripts/fixtures/ReadBack.java tests/data/picard /tmp/written'
```

The check needs Picard and Java, so it is run locally and not in CI.

## Releasing

Commit titles follow [Conventional Commits](https://www.conventionalcommits.org), which group the release notes.
To release, merge a pull request titled `chore(release): bump to X.Y.Z` that sets the version in `pyproject.toml`, then tag its commit on `main` with `X.Y.Z` and push the tag.
The `publish_captainslog.yml` workflow then builds, tests, and publishes the package to PyPI and makes a GitHub release with notes from [git-cliff](https://git-cliff.org).
