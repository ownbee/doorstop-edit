import datetime
import logging
import re
import subprocess
from pathlib import Path

from doorstop_edit.dialogs.differs.differ import Differ

logger = logging.getLogger("gui")


class GitDiffer(Differ):
    """Diff item using Git.

    This differ is is using Git command to fetch the history of the item. The item must be version
    controlled with Git for this differ to work. CURRENT is the current state on disk and change 1
    is the previous commit that made any changes to this item, change 2 the change before 1 and so
    on.
    """

    def __init__(self, file: Path) -> None:
        resolved_file = file.resolve()
        self.working_dir = resolved_file.parent
        file = resolved_file.relative_to(self.working_dir)
        super().__init__(resolved_file)
        self._history = self._get_git_history(file)
        self._history_metadata: list[Differ.ChangeMetadata] = []
        for commit in self._get_git_history(file):
            self._history_metadata.append(self._get_change_metadata(commit))

    def get_diff(self, index: int) -> str:
        if index > len(self._history) - 1:
            index = len(self._history) - 1

        commits: tuple[str, ...]
        if len(self._history) == 0:
            commits = ("HEAD",)
        elif index == 0:
            commits = (self._history[index],)
        else:
            commits = (self._history[index], self._history[index - 1])

        return self._run_git("diff", *commits, str(self.file))

    def support_history(self) -> bool:
        return True

    def get_history_len(self) -> int:
        return len(self._history)

    def get_history_name(self, index: int) -> str:
        number = self.get_history_len() - index
        text = f"{number} ({self.get_history_len()}) -> "
        if index == 0:
            return f"{text}CURRENT"
        return f"{text}{number + 1}"

    def get_history_metadata(self, index: int) -> Differ.ChangeMetadata:
        if index == 0:
            return Differ.ChangeMetadata("UNCOMMITTED", datetime.datetime.now())
        else:
            return self._history_metadata[index - 1]

    def _run_git(self, *args: str) -> str:
        arguments = ["git"] + list(args)
        try:
            return subprocess.check_output(arguments, cwd=str(self.working_dir)).decode("utf-8")
        except subprocess.CalledProcessError as e:
            logger.error("Failed to execute '%s'", " ".join(arguments), exc_info=e)
        return ""

    def _get_git_history(self, file: Path) -> list[str]:
        lines = self._run_git("log", "--follow", "--oneline", str(file))
        retval = []
        for line in lines.splitlines():
            retval.append(line.split()[0])
        return retval

    def _get_change_metadata(self, commit: str) -> Differ.ChangeMetadata:
        data = self._run_git("show", "-s", "--format=raw", commit).splitlines()
        author_line = ""
        for line in data:
            if line.startswith("author"):
                author_line = line
                break
        m = re.match(r"^author\s(.+)\s\<(.*)\>\s(\d+)\s.*$", author_line)
        if m is not None:
            author = m.group(1)
            timestamp = int(m.group(3))
            return Differ.ChangeMetadata(author, datetime.datetime.fromtimestamp(timestamp))

        logger.error("Could not parse 'git show' data from: %s" "\n".join(data))
        return Differ.ChangeMetadata("Error", datetime.datetime.fromtimestamp(0, tz=datetime.timezone.utc))
