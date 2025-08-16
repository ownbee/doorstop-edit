from doorstop_edit.item_edit.mdformat import format as format_md


def test_keep_undefined_references_as_is() -> None:
    text = r"""\
Some example text with undefined [ref1] and a footnote [^ref2] [Cool][ref1 asd]

Line with ok link [ref3] and ok footnote [^ref4] and escaped \[[ref3]\].

[^ref4]: Good footnote.

[ref3]: http://example.se
"""
    assert format_md(text) == text
