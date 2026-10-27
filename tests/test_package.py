import ast
import re
from collections.abc import Iterator
from pathlib import Path

PACKAGE = Path(__file__).parents[1] / "captainslog"

COORDINATE = re.compile(r"^(?:position|pos|start|end|cycle)$|_(?:position|start|end)$")

BASES = ("0-based", "1-based", "Picard does not say whether this position is 0-based or 1-based.")

# The read of a pair, 1 or 2, rather than a position on it.
NOT_COORDINATES = {"read_end"}


def field_docstrings(path: Path) -> Iterator[tuple[str, str, str]]:
    """The class, name, and docstring of each field of each dataclass in a module's source.

    A `Columns` dataclass is left out, since each of its fields transposes a documented field.
    """
    for kind in ast.parse(path.read_text()).body:
        if not isinstance(kind, ast.ClassDef) or kind.name.endswith("Columns"):
            continue
        if not any("dataclass" in ast.unparse(decorator) for decorator in kind.decorator_list):
            continue
        for node, after in zip(kind.body, [*kind.body[1:], None], strict=True):
            if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                docstring = ""
                if isinstance(after, ast.Expr) and isinstance(after.value, ast.Constant):
                    docstring = str(after.value.value)
                yield kind.name, node.target.id, docstring


def test_the_package_holds_a_module_for_each_tool() -> None:
    """The package exposes the fgbio, fgumi, picard, and riker modules."""
    from captainslog import fgbio
    from captainslog import fgumi
    from captainslog import picard
    from captainslog import riker

    assert fgbio.__name__ == "captainslog.fgbio"
    assert fgumi.__name__ == "captainslog.fgumi"
    assert picard.__name__ == "captainslog.picard"
    assert riker.__name__ == "captainslog.riker"


def test_every_coordinate_field_says_whether_it_is_0_based_or_1_based() -> None:
    """Each position, start, end, or cycle says its base, and each end whether it is inclusive."""
    found = {
        (path.parent.name, kind, name): docstring
        for path in sorted(PACKAGE.glob("*/*.py"))
        for kind, name, docstring in field_docstrings(path)
        if COORDINATE.search(name) and name not in NOT_COORDINATES
    }
    assert {
        ("fgbio", "ConsensusVariantReviewInfo", "pos"),
        ("fgbio", "ErrorRateByReadPositionMetric", "position"),
        ("fgumi", "ConsensusVariantReviewInfo", "pos"),
        ("picard", "BaseDistributionByCycleMetrics", "cycle"),
        ("picard", "MeanQualityByCycle", "cycle"),
        ("picard", "PerTargetCoverage", "end"),
        ("riker", "HybcapPerBase", "pos"),
    } <= set(found)
    for field, docstring in found.items():
        assert any(base in docstring for base in BASES), field
        if re.search(r"(?:^|_)end$", field[2]):
            assert re.search(r"\b(?:in|ex)clusive\b", docstring), field
