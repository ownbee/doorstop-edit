from datetime import datetime
from typing import Iterable

import pytest
from PySide6.QtCore import Qt
from pytestqt.qtbot import QtBot

from doorstop_edit.dialogs import DiffDialog
from doorstop_edit.dialogs.differs import Differ, GitDiffer, SimpleDiffer
from doorstop_edit.doorstop_data import DoorstopData


@pytest.fixture()
def initialized_dialog(
    qtbot: QtBot, doorstop_data: DoorstopData, monkeypatch: pytest.MonkeyPatch
) -> Iterable[DiffDialog]:
    for differ_t in [GitDiffer, SimpleDiffer]:
        monkeypatch.setattr(differ_t, "get_diff", lambda _1, index: str(index))
        monkeypatch.setattr(differ_t, "get_history_len", lambda _1: 2)
        monkeypatch.setattr(
            differ_t,
            "get_history_metadata",
            lambda _1, index: Differ.ChangeMetadata(str(index), datetime.fromtimestamp(index)),
        )
        monkeypatch.setattr(differ_t, "get_history_name", lambda _1, index: str(index))
        monkeypatch.setattr(differ_t, "support_history", lambda _1: True)

    item = doorstop_data.find_item("REQ-B-001")
    assert item is not None

    dialog = DiffDialog(item, doorstop_data)
    qtbot.add_widget(dialog.dialog)
    yield dialog


def test_initialize(initialized_dialog: DiffDialog) -> None:
    assert initialized_dialog.dialog.ui.description.text() != ""
    assert initialized_dialog.dialog.ui.diff_dialog_text.toPlainText().strip() == "0"


def test_traverse_history(qtbot: QtBot, initialized_dialog: DiffDialog) -> None:
    qtbot.mouseClick(initialized_dialog.dialog.ui.vcs_forward_button, Qt.MouseButton.LeftButton)
    assert initialized_dialog.dialog.ui.diff_dialog_text.toPlainText().strip() == "0"

    qtbot.mouseClick(initialized_dialog.dialog.ui.vcs_backward_button, Qt.MouseButton.LeftButton)
    assert initialized_dialog.dialog.ui.diff_dialog_text.toPlainText().strip() == "1"

    qtbot.mouseClick(initialized_dialog.dialog.ui.vcs_backward_button, Qt.MouseButton.LeftButton)
    assert initialized_dialog.dialog.ui.diff_dialog_text.toPlainText().strip() == "1"

    qtbot.mouseClick(initialized_dialog.dialog.ui.vcs_forward_button, Qt.MouseButton.LeftButton)
    assert initialized_dialog.dialog.ui.diff_dialog_text.toPlainText().strip() == "0"


def test_change_mode(qtbot: QtBot, initialized_dialog: DiffDialog) -> None:
    assert initialized_dialog.dialog.ui.simple_mode_button.isChecked()
    assert not initialized_dialog.dialog.ui.git_mode_button.isChecked()

    qtbot.mouseClick(initialized_dialog.dialog.ui.git_mode_button, Qt.MouseButton.LeftButton)
    assert not initialized_dialog.dialog.ui.simple_mode_button.isChecked()
    assert initialized_dialog.dialog.ui.git_mode_button.isChecked()
