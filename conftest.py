from pathlib import Path

import pytest
from sybil import Sybil
from sybil.parsers.markdown import PythonCodeBlockParser
from sybil.parsers.markdown import SkipParser


@pytest.fixture
def in_test_data(monkeypatch: pytest.MonkeyPatch) -> None:
    """Run each README example from the test data, so it names files as a user would."""
    monkeypatch.chdir(Path(__file__).parent / "tests" / "data")


pytest_collect_file = Sybil(
    parsers=[PythonCodeBlockParser(), SkipParser()], patterns=["*.md"], fixtures=["in_test_data"]
).pytest()
