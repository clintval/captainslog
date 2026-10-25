def test_the_package_holds_the_picard_and_riker_modules() -> None:
    """The package exposes the picard and riker modules."""
    from captainslog import picard
    from captainslog import riker

    assert picard.__name__ == "captainslog.picard"
    assert riker.__name__ == "captainslog.riker"
