from doorstop_edit.dialogs.differs import Differ
from pathlib import Path
import pytest


def test_default_returns() -> None:
    differ = Differ(Path())
    with pytest.raises(NotImplementedError):
        differ.get_diff(1234)
    assert not differ.support_history()
    assert differ.get_history_len() == 0
    assert differ.get_history_metadata(123).author == ""
    assert differ.get_history_metadata(123).timestamp.timestamp() == 0
    assert differ.get_history_name(124) == ""
