from pathlib import Path
from typing import Any

from captainslog.picard._java import JAVA_NAMES

DATA = Path(__file__).parents[1] / "data" / "picard"

METRICS_CLASS = "## METRICS CLASS\t"


def _metrics_class_line(path: Path) -> str | None:
    lines = path.read_text().splitlines()
    return next((line for line in lines if line.startswith(METRICS_CLASS)), None)


PICARD_METRICS_FIXTURES = sorted(path for path in DATA.glob("*") if _metrics_class_line(path))


def class_named_in(path: Path) -> type[Any]:
    """The dataclass of the Java class that a file's `## METRICS CLASS` line names."""
    line = _metrics_class_line(path)
    assert line is not None, f"{path} has no {METRICS_CLASS!r} line"
    name = line.removeprefix(METRICS_CLASS)
    return next(kind for kind, java in JAVA_NAMES.items() if java == name)
