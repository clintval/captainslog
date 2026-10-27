from pathlib import Path

DATA = Path(__file__).parents[1] / "data" / "fgumi"

FGUMI_FIXTURES = sorted([*DATA.glob("*.txt"), *DATA.glob("*.txt.gz")])
