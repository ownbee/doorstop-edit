from doorstop_edit.dialogs.differs import GitDiffer
from pathlib import Path
from unittest.mock import Mock, patch
from pytest import MonkeyPatch
import subprocess
from typing import Any


GIT_LOG_OUTPUT = """\
f1553da (HEAD -> master) Change 3
5d4f67d Change 2
4ac3b17 FIRST COMMIt
"""

GIT_SHOW_OUTPUT = """\
commit 5d4f67d7f279c88183d6fb3ac3be0fb9e7fda994
tree f43f0fde3f7e1225be759e2c3f82895f13e34c2a
parent 4ac3b1799f5037e19f5c1c70370db3ba9334caef
author Juri Test Master <juri-test-master@gmail.com> 1673205909 +0100
committer Jogi Lover <jogi-lover@gmail.com> 1673205909 +0100

    Change 2
"""

GIT_DIFF_1_2_OUTPUT = """\
diff --git a/REQ-A/REQ-A-122.yml b/REQ-A/REQ-A-122.yml
index bc5a7c0..050257e 100644
--- a/REQ-A/REQ-A-122.yml
+++ b/REQ-A/REQ-A-122.yml
@@ -8,8 +8,12 @@ level: 3
-  DIFF1-2
+  change1...
"""

GIT_DIFF_2_3_OUTPUT = """\
diff --git a/REQ-A/REQ-A-122.yml b/REQ-A/REQ-A-122.yml
index bc5a7c0..050257e 100644
--- a/REQ-A/REQ-A-122.yml
+++ b/REQ-A/REQ-A-122.yml
@@ -8,8 +8,12 @@ level: 3
-  DIFF2-3
+  change1...
"""

GIT_DIFF_3_CURR_OUTPUT = """\
diff --git a/REQ-A/REQ-A-122.yml b/REQ-A/REQ-A-122.yml
index bc5a7c0..050257e 100644
--- a/REQ-A/REQ-A-122.yml
+++ b/REQ-A/REQ-A-122.yml
@@ -8,8 +8,12 @@ level: 3
-  DIFF3-CURR
+  change1...
"""


def check_output_raise_mock(*args: Any, **kwargs: Any) -> None:
    raise subprocess.CalledProcessError(1, [])


class SubprocessCheckOutputMock:
    def __init__(self) -> None:
        self.returned_show = GIT_SHOW_OUTPUT

    def __call__(self, args: list[str], *other_args: Any, **kwargs: Any) -> bytes:
        if "diff" in args:
            if "4ac3b17" in args and "5d4f67d" in args:
                return GIT_DIFF_1_2_OUTPUT.encode("utf-8")
            if "5d4f67d" in args and "f1553da" in args:
                return GIT_DIFF_2_3_OUTPUT.encode("utf-8")
            if "f1553da" in args:
                print(args)
                return GIT_DIFF_3_CURR_OUTPUT.encode("utf-8")
        if "show" in args:
            return self.returned_show.encode("utf-8")
        if "log" in args:
            return GIT_LOG_OUTPUT.encode("utf-8")

        raise RuntimeError("More commands need implementation: " + str(args))


def test_git_not_available_shall_not_raise(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr("subprocess.check_output", check_output_raise_mock)
    differ = GitDiffer(Path("samplefile"))
    assert differ.get_diff(0) == ""
    assert differ.support_history()
    assert differ.get_history_len() == 0
    assert differ.get_history_name(0) != ""
    metadata = differ.get_history_metadata(0)
    assert metadata.author == "UNCOMMITTED"
    assert metadata.timestamp.timestamp() != 0


def test_return_correct_history_by_index(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr("subprocess.check_output", SubprocessCheckOutputMock())
    differ = GitDiffer(Path("samplefile"))

    assert differ.get_history_len() == 3
    assert "DIFF3-CURR" in differ.get_diff(0)
    assert "DIFF2-3" in differ.get_diff(1)
    assert "DIFF1-2" in differ.get_diff(2)
    assert "DIFF1-2" in differ.get_diff(3)  # Shall return last index if index is overflowed.


def test_return_correct_name_by_index(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr("subprocess.check_output", SubprocessCheckOutputMock())
    differ = GitDiffer(Path("samplefile"))

    assert differ.get_history_len() == 3
    assert "CURRENT" in differ.get_history_name(0)
    assert "3" in differ.get_history_name(0)
    assert "3" in differ.get_history_name(1)
    assert "2" in differ.get_history_name(1)
    assert "2" in differ.get_history_name(2)
    assert "1" in differ.get_history_name(2)


def test_return_correct_metadata_by_index(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr("subprocess.check_output", SubprocessCheckOutputMock())
    differ = GitDiffer(Path("samplefile"))

    assert differ.get_history_len() == 3
    assert "UNCOMMITTED" in differ.get_history_metadata(0).author
    assert "Juri Test Master" in differ.get_history_metadata(1).author
    assert "Juri Test Master" in differ.get_history_metadata(2).author
    assert "Juri Test Master" in differ.get_history_metadata(3).author


def test_return_error_author_show_could_not_be_parsed(monkeypatch: MonkeyPatch) -> None:
    mock = SubprocessCheckOutputMock()
    mock.returned_show = "Something unre\nCognized\n"
    monkeypatch.setattr("subprocess.check_output", mock)
    differ = GitDiffer(Path("samplefile"))

    assert differ.get_history_len() == 3
    assert "Error" in differ.get_history_metadata(1).author
    assert "Error" in differ.get_history_metadata(2).author
    assert "Error" in differ.get_history_metadata(3).author
