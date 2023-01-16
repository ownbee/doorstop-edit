from doorstop_edit.dialogs.differs.differ import Differ
from pathlib import Path
import difflib
from typing import Optional


class SimpleDiffer(Differ):
    """Diff changes made by this editor.

    This differ does not need any external tool. This simple differ diff the original item from
    application startup with the current state on disk."""

    def __init__(self, original: Optional[str], path: Path) -> None:
        super().__init__(path)
        self._original = original

    def get_diff(self, _: int) -> str:
        if not self.file.exists() or self._original is None:
            return ""

        new_item_data = self.file.read_text(encoding="utf-8")
        diffs = difflib.unified_diff(
            self._original.splitlines(True),
            new_item_data.splitlines(True),
            fromfile="ORIGINAL",
            tofile="NEW",
            n=100,
        )
        return "".join(diffs)

    def support_history(self) -> bool:
        return False
