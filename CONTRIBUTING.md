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

## Regenerating the Test Fixtures

The files in `tests/data/picard` and `tests/data/riker` are written by Picard 3.5.0 and Riker 0.5.0, from inputs in Picard's own test data.
To write them again, install [pixi](https://pixi.sh), then run `make.sh` in the environment of `scripts/fixtures/pixi.toml`, which holds Picard, Riker, samtools, and Java:

```console
pixi run --manifest-path scripts/fixtures/pixi.toml bash scripts/fixtures/make.sh
```

The script downloads its inputs from Picard's repository at the 3.5.0 tag, runs each tool, and replaces both directories.

## Regenerating the Picard Dataclasses

The Picard dataclasses in `captainslog/picard/_metrics.py`, and their Java names and column labels in `captainslog/picard/_java.py`, are generated, so change the generator rather than the files.
`scripts/picard/PicardSchema.java` prints the metrics classes of a Picard jar as JSON, with the columns htsjdk writes for each and the constants of their enums:

```console
pixi run --manifest-path scripts/fixtures/pixi.toml bash -c 'java -cp "$PICARD_JAR" scripts/picard/PicardSchema.java "$PICARD_JAR" > scripts/picard/picard-3.5.0.json'
```

`scripts/picard/generate.py` writes both modules from that JSON, with docstrings from the Javadoc of a checkout of Picard's source at the same release:

```console
git clone --depth 1 --branch 3.5.0 https://github.com/broadinstitute/picard.git /tmp/picard
uv run python scripts/picard/generate.py --schema scripts/picard/picard-3.5.0.json --source /tmp/picard --output captainslog/picard
```

`scripts/picard/units.json` classifies each field whose name holds `PCT` or `PERCENT` as a `fraction` from 0 to 1, a `percent` from 0 to 100, `none` when the word is not its unit, or `unknown`, with the line of Picard's source that sets it.
The generator names a fraction `frac` in place of `pct` or `percent`, maps it to Picard's label in `COLUMN_LABELS`, and says the unit in its docstring.
It refuses to run while a field is missing from the table, so classify each new one from where Picard computes it, never from its name.
`COORDINATE_BASES` in the generator says whether a position or cycle is 0-based or 1-based where its Javadoc does not, so settle each new one from where Picard sets it.

For a new Picard release, set its version in `scripts/fixtures/make.sh` and `scripts/fixtures/pixi.toml`, along with the package build that the path of `PICARD_JAR` names, then update the lock with `pixi lock --manifest-path scripts/fixtures/pixi.toml`.
Write its schema to a new `scripts/picard/picard-X.Y.Z.json`, name that file in `pyproject.toml` and `tests/picard/test_metrics.py`, check the source lines in `scripts/picard/units.json` against the new release, generate the modules from it, and regenerate the fixtures.
`git grep -n -F 3.5.0 -- ':!*.lock' ':!tests/data'` lists every other place that names the release, such as the errors in `captainslog/picard/_reader.py` and this guide.
The histograms in `captainslog/picard/_histograms.py` are written by hand, so check them against the new release too.

## Checking Written Files with htsjdk

`scripts/fixtures/write_back.py` reads every Picard fixture with captainslog and writes it back into a directory, with its header, metrics, and histogram.
`scripts/fixtures/ReadBack.java` then checks that htsjdk reads each written file as the metrics and histogram of its fixture:

```console
uv run python scripts/fixtures/write_back.py /tmp/written
pixi run --manifest-path scripts/fixtures/pixi.toml bash -c 'java -cp "$PICARD_JAR" scripts/fixtures/ReadBack.java tests/data/picard /tmp/written'
```

The check needs Picard and Java, so it is run locally and not in CI.

## Releasing

Commit titles follow [Conventional Commits](https://www.conventionalcommits.org), which group the release notes.
To release, merge a pull request titled `chore(release): bump to X.Y.Z` that sets the version in `pyproject.toml`, then tag its commit on `main` with `X.Y.Z` and push the tag.
The `publish_captainslog.yml` workflow then builds, tests, and publishes the package to PyPI and makes a GitHub release with notes from [git-cliff](https://git-cliff.org).
