def test_the_package_holds_the_picard_and_riker_modules() -> None:
    """The package exposes the picard and riker modules."""
    from shipslog import picard
    from shipslog import riker

    assert picard.__name__ == "shipslog.picard"
    assert riker.__name__ == "shipslog.riker"
