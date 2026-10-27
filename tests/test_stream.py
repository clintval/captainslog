from io import StringIO

import pytest

from captainslog._stream import SectionStream


def test_section_stream_writes_a_label_row_split_across_writes_with_its_first_row() -> None:
    """The pieces of a label row are held, then written after the section line with a row."""
    handle = StringIO()
    stream = SectionStream(handle, "## SECTION")
    _ = stream.write("BIN\t")
    _ = stream.write("VALUE\n")
    assert handle.getvalue() == ""
    _ = stream.write("1\t2\n")
    assert handle.getvalue() == "## SECTION\nBIN\tVALUE\n1\t2\n"


def test_section_stream_writes_a_label_row_and_its_rows_given_in_one_write() -> None:
    """A label row and its rows written at once are written after the section line."""
    handle = StringIO()
    stream = SectionStream(handle, "## SECTION")
    _ = stream.write("BIN\tVALUE\n1\t2\n3\t4\n")
    assert handle.getvalue() == "## SECTION\nBIN\tVALUE\n1\t2\n3\t4\n"


def test_section_stream_writes_a_row_split_mid_line() -> None:
    """A row written in pieces is written as given, after the section line and the labels."""
    handle = StringIO()
    stream = SectionStream(handle, "## SECTION")
    for text in ("BIN\tVALUE\n", "1\t", "2\n", "3\t4\n"):
        _ = stream.write(text)
    assert handle.getvalue() == "## SECTION\nBIN\tVALUE\n1\t2\n3\t4\n"


def test_section_stream_never_writes_a_label_row_without_rows() -> None:
    """A label row no row follows is not written, even when the stream is closed."""
    handle = StringIO()
    stream = SectionStream(handle, "## SECTION")
    _ = stream.write("BIN\tVALUE\n")
    _ = stream.write("")
    assert handle.getvalue() == ""
    stream.close()
    assert handle.closed


def test_section_stream_starts_with_its_first_row() -> None:
    """The section starts with its first row, and not with a label row alone."""
    stream = SectionStream(StringIO(), "## SECTION")
    _ = stream.write("BIN\tVALUE\n")
    assert not stream.started
    _ = stream.write("1\t2\n")
    assert stream.started


def test_section_stream_refuses_a_row_after_its_end_and_writes_nothing() -> None:
    """A row after the section ends is refused, and nothing is written."""
    handle = StringIO()
    stream = SectionStream(handle, "## SECTION")
    _ = stream.write("BIN\tVALUE\n1\t2\n")
    stream.end()
    assert stream.ended
    before = handle.getvalue()
    with pytest.raises(ValueError, match=r"^Cannot write metrics after the histogram!$"):
        _ = stream.write("3\t4\n")
    assert handle.getvalue() == before


def test_section_stream_drops_a_label_row_after_its_end() -> None:
    """A label row after the section ends is dropped, and a row after it is still refused."""
    handle = StringIO()
    stream = SectionStream(handle, "## SECTION")
    stream.end()
    _ = stream.write("BIN\tVALUE\n")
    assert handle.getvalue() == ""
    with pytest.raises(ValueError, match=r"^Cannot write metrics after the histogram!$"):
        _ = stream.write("1\t2\n")
    assert handle.getvalue() == ""


def test_section_stream_without_a_section_holds_a_label_row_alone() -> None:
    """With no section line, a label row no row follows is not written."""
    handle = StringIO()
    stream = SectionStream(handle, None)
    _ = stream.write("BIN\tVALUE\n")
    assert handle.getvalue() == ""


def test_section_stream_without_a_section_writes_no_leading_line() -> None:
    """With no section line, the label row and a row given in one write start the file."""
    handle = StringIO()
    stream = SectionStream(handle, None)
    _ = stream.write("BIN\tVALUE\n1\t2\n")
    assert handle.getvalue() == "BIN\tVALUE\n1\t2\n"


def test_section_stream_runs_its_start_hook_once_before_its_first_write_to_the_handle() -> None:
    """The hook runs before the section line, not for a label row held back, and only once."""
    handle = StringIO()
    starts: list[str] = []
    stream = SectionStream(handle, "## SECTION", on_start=lambda: starts.append(handle.getvalue()))
    _ = stream.write("BIN\tVALUE\n")
    assert starts == []
    _ = stream.write("1\t2\n")
    _ = stream.write("3\t4\n")
    assert starts == [""]
    assert handle.getvalue() == "## SECTION\nBIN\tVALUE\n1\t2\n3\t4\n"


def test_section_stream_relabels_its_label_row_before_writing_it() -> None:
    """A `relabel` hook rewrites the whole label row, held across writes, and no row after it."""
    handle = StringIO()
    stream = SectionStream(handle, "## SECTION", relabel=str.upper)
    _ = stream.write("bin\t")
    _ = stream.write("value\nrow\t1\n")
    _ = stream.write("row\t2\n")
    assert handle.getvalue() == "## SECTION\nBIN\tVALUE\nrow\t1\nrow\t2\n"
