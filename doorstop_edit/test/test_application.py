import tempfile
from pathlib import Path
from typing import Iterator
from unittest.mock import patch

import doorstop
import pytest
from PySide6.QtCore import Qt
from pytestqt.qtbot import QtBot

from doorstop_edit.application import DoorstopEdit, QFileDialog
from doorstop_edit.conftest import NUM_DOC
from doorstop_edit.dialogs import ConfirmDialog, InfoDialog
from doorstop_edit.ui_gen.ui_main import Ui_MainWindow


@pytest.fixture(scope="session")
def app_session(tree_root: Path) -> Iterator[DoorstopEdit]:
    """Create DoorstopEdit

    Created only once per session since QApplcation cannot be recreated reliably in a process, thus
    it is hard to recreate DoorstopEdit for each test.

    When DoorstopEdit is recreate QApplication still have references to the old instance which cause
    troubles.
    """
    app = DoorstopEdit(tree_root)
    app.start()  # Must show it, clicks wont work otherwise.
    yield app
    app.quit()


@pytest.fixture()
def app(
    app_session: DoorstopEdit, tree_root: Path, monkeypatch: pytest.MonkeyPatch, qtbot: QtBot
) -> Iterator[DoorstopEdit]:
    # Reset directory
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", classmethod(lambda *_: str(tree_root)))
    with qtbot.wait_signal(app_session.window.ui.menu_action_open_folder.triggered):
        app_session.window.ui.menu_action_open_folder.trigger()

    # Reset document tree to the default document for each test.
    app_session.window.ui.tree_combo_box.setCurrentIndex(0)

    yield app_session


def count_items_in_current_document(app: DoorstopEdit) -> int:
    count = 0
    for _ in app.selected_document or []:
        count += 1
    return count


def click_item_in_tree(qtbot: QtBot, ui: Ui_MainWindow, index: int) -> None:
    w_item = ui.item_tree_widget.topLevelItem(index)
    w_item_rect = ui.item_tree_widget.visualItemRect(w_item)
    with qtbot.wait_signal(ui.item_tree_widget.itemSelectionChanged):
        qtbot.mouseClick(
            ui.item_tree_widget.viewport(),
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
            w_item_rect.center(),
        )


def click_button_clear_search(qtbot: QtBot, ui: Ui_MainWindow) -> None:
    with qtbot.wait_signal(ui.item_tree_search_input.textChanged):
        qtbot.mouseClick(ui.item_tree_clear_search, Qt.MouseButton.LeftButton)
    assert ui.item_tree_search_input.text() == ""


def type_in_search_box(qtbot: QtBot, ui: Ui_MainWindow, text: str) -> None:
    with qtbot.wait_signal(ui.item_tree_search_input.textChanged):
        ui.item_tree_search_input.clear()
        qtbot.keyClicks(ui.item_tree_search_input, text)


def test_select_tree_item_show_in_edit(qtbot: QtBot, app: DoorstopEdit) -> None:
    assert app.window.ui.item_tree_widget.topLevelItemCount() == 1
    assert app.window.ui.item_edit_uid.text() == ""
    click_item_in_tree(qtbot, app.window.ui, index=0)
    assert app.window.ui.item_edit_uid.text() == "REQ-A-001"

    item = app.doorstop_data.find_item("REQ-A-001")
    assert item is not None

    assert app.window.ui.item_edit_review_status_label.text() == "NOT REVIEWED"
    assert app.window.ui.item_edit_active_check_box.isChecked() == item.active
    assert app.window.ui.item_edit_normative_check_box.isChecked() == item.normative
    assert app.window.ui.item_edit_derived_check_box.isChecked() == item.derived
    assert app.window.ui.item_edit_level_line_edit.text() == str(item.level)
    assert app.window.ui.item_edit_text_text_edit.toPlainText() == item.text


def test_search_tree_item(qtbot: QtBot, app: DoorstopEdit) -> None:
    type_in_search_box(qtbot, app.window.ui, "REQ-B-004")  # Does not exist in current document
    assert app.window.ui.item_tree_widget.topLevelItemCount() == 0

    click_button_clear_search(qtbot, app.window.ui)

    type_in_search_box(qtbot, app.window.ui, "REQ-A-003")
    assert app.window.ui.item_tree_widget.topLevelItemCount() == 1

    click_item_in_tree(qtbot, app.window.ui, index=0)

    assert app.window.ui.item_edit_uid.text() == "REQ-A-003"


def test_change_document(qtbot: QtBot, app: DoorstopEdit) -> None:
    assert app.window.ui.tree_combo_box.count() == NUM_DOC
    qtbot.keyClicks(app.window.ui.tree_combo_box, "REQ-B")
    type_in_search_box(qtbot, app.window.ui, "REQ-B-007")
    assert app.window.ui.item_tree_widget.topLevelItemCount() == 1
    click_item_in_tree(qtbot, app.window.ui, index=0)
    assert app.window.ui.item_edit_uid.text() == "REQ-B-007"


def test_edit_item_then_save(qtbot: QtBot, app: DoorstopEdit) -> None:
    type_in_search_box(qtbot, app.window.ui, "REQ-A-001")
    assert app.window.ui.item_tree_widget.topLevelItemCount() == 1
    click_item_in_tree(qtbot, app.window.ui, index=0)

    item = app.doorstop_data.find_item("REQ-A-001")
    assert item is not None
    item_path = Path(item.path)
    item_file_content = item_path.read_text("utf-8")

    with patch.object(doorstop.Item, "save", wraps=item.save) as item_save:
        with qtbot.wait_signal(app.window.ui.item_edit_text_text_edit.textChanged):
            added_text = "Some more content"
            qtbot.keyClicks(app.window.ui.item_edit_text_text_edit, added_text)
            assert item_save.call_count == 0
            qtbot.wait(1000)  # Should save after a period no typing.
            assert item_save.call_count == 1

    new_content = item_path.read_text("utf-8")
    assert item_file_content != new_content
    assert added_text in new_content


def test_document_reorder(qtbot: QtBot, app: DoorstopEdit, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ConfirmDialog, "ask", classmethod(lambda *_: True))

    with patch.object(doorstop.Document, "reorder") as doc_reorder_mock:
        with qtbot.wait_signal(app.window.ui.doc_reorder_level_tool_button.clicked):
            qtbot.mouseClick(app.window.ui.doc_reorder_level_tool_button, Qt.MouseButton.LeftButton)

    assert doc_reorder_mock.call_count == 1


def test_document_review_all(qtbot: QtBot, app: DoorstopEdit, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ConfirmDialog, "ask", classmethod(lambda *_: True))

    with patch.object(doorstop.Item, "review") as item_review_mock:
        with qtbot.wait_signal(app.window.ui.doc_review_tool_button.clicked):
            qtbot.mouseClick(app.window.ui.doc_review_tool_button, Qt.MouseButton.LeftButton)

    assert item_review_mock.call_count == count_items_in_current_document(app)


def test_document_clear_all_suspect_links(qtbot: QtBot, app: DoorstopEdit, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ConfirmDialog, "ask", classmethod(lambda *_: True))

    with patch.object(doorstop.Item, "clear") as item_clear_mock:
        with qtbot.wait_signal(app.window.ui.doc_clear_links_tool_button.clicked):
            qtbot.mouseClick(app.window.ui.doc_clear_links_tool_button, Qt.MouseButton.LeftButton)

    assert item_clear_mock.call_count == count_items_in_current_document(app)


def test_open_folder(qtbot: QtBot, app: DoorstopEdit, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        InfoDialog, "inform", classmethod(lambda *_: None)
    )  # We will open an empty directory which will trigger an inform.

    with tempfile.TemporaryDirectory() as tempDir, patch.object(doorstop, "build") as doorstop_build:
        monkeypatch.setattr(QFileDialog, "getExistingDirectory", classmethod(lambda *_: tempDir))
        with qtbot.wait_signal(app.window.ui.menu_action_open_folder.triggered):
            app.window.ui.menu_action_open_folder.trigger()

        assert doorstop_build.call_count == 1
