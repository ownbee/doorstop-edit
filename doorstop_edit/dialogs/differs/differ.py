import datetime
from pathlib import Path


class Differ:
    class ChangeMetadata:
        def __init__(self, author: str, timestamp: datetime.datetime) -> None:
            self.author = author
            self.timestamp = timestamp

    def __init__(self, file: Path) -> None:
        self.file = file

    def get_diff(self, index: int) -> str:
        """Returns a diff of index.

        A Differ without history ignores the index."""
        raise NotImplementedError()

    def support_history(self) -> bool:
        """Returns True if difftool has history."""
        return False

    def get_history_len(self) -> int:
        """Return how many history items there is."""
        return 0

    def get_history_name(self, index: int) -> str:
        """Returns name of history item."""
        return ""

    def get_history_metadata(self, index: int) -> ChangeMetadata:
        """Get metadata of history item."""
        return Differ.ChangeMetadata("", datetime.datetime.fromtimestamp(0))
