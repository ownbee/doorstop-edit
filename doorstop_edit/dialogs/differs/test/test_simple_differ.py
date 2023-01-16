from doorstop_edit.dialogs.differs import SimpleDiffer
from pathlib import Path
import tempfile


def test_simple_differ() -> None:
    data = "some\nstring\nthat looks aweful."
    with tempfile.TemporaryDirectory() as tmp_dir:
        path = Path(tmp_dir) / "some_file.txt"
        differ = SimpleDiffer(data, path)
        assert differ.support_history() == False
        assert differ.get_diff(0) == ""  # Return empty when file does not exits
        path.write_text(data, "utf-8")
        assert differ.get_diff(0) == ""  # Return empty when content is same
        data += "added content"
        path.write_text(data, "utf-8")
        assert "added content" in differ.get_diff(0)  # Return diff when changed


def test_none_original_data() -> None:
    data = "some\nstring\nthat looks aweful."
    with tempfile.TemporaryDirectory() as tmp_dir:
        path = Path(tmp_dir) / "some_file.txt"
        path.write_text(data, "utf-8")
        differ = SimpleDiffer(None, path)
        assert differ.get_diff(0) == ""  # Return empty when file does not exits
