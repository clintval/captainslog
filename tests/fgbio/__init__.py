from pathlib import Path

DATA = Path(__file__).parents[1] / "data" / "fgbio"

FGBIO_FIXTURES = sorted([*DATA.glob("*.txt"), *DATA.glob("*.txt.gz")])
