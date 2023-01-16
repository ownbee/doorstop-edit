from pathlib import Path
from typing import Iterator
from unittest.mock import patch

import doorstop
import pytest
from PySide6.QtCore import Qt
from pytestqt.qtbot import QtBot

from doorstop_edit.application import DoorstopEdit
from doorstop_edit.conftest import NUM_DOC, NUM_ITEMS_PER_DOC
from doorstop_edit.dialogs import ConfirmDialog
from doorstop_edit.ui_gen.ui_main import Ui_MainWindow


@pytest.fixture()
def app(qtbot: QtBot, tree_root: Path) -> Iterator[DoorstopEdit]:
    app = DoorstopEdit(tree_root)
    qtbot.add_widget(app.window, before_close_func=lambda x, app=app: app.quit())
    app.show()  # Must show it, clicks wont work otherwise.
    yield app


def click_item_in_tree(qtbot: QtBot, ui: Ui_MainWindow, index: int) -> None:
    w_item = ui.item_tree_widget.topLevelItem(index)
    w_item_rect = ui.item_tree_widget.visualItemRect(w_item)
    with qtbot.wait_signal(ui.item_tree_widget.itemSelectionChanged):  # type: ignore
        qtbot.mouseClick(
            ui.item_tree_widget.viewport(),
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
            w_item_rect.center(),
        )


def click_button_clear_search(qtbot: QtBot, ui: Ui_MainWindow) -> None:
    with qtbot.wait_signal(ui.item_tree_search_input.textChanged):  # type: ignore
        qtbot.mouseClick(ui.item_tree_clear_search, Qt.MouseButton.LeftButton)
    assert ui.item_tree_search_input.text() == ""


def type_in_search_box(qtbot: QtBot, ui: Ui_MainWindow, text: str) -> None:
    with qtbot.wait_signal(ui.item_tree_search_input.textChanged):  # type: ignore
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
        with qtbot.wait_signal(app.window.ui.item_edit_text_text_edit.textChanged):  # type: ignore
            added_text = "Some more content"
            qtbot.keyClicks(app.window.ui.item_edit_text_text_edit, added_text)

    assert item_save.call_count == len(added_text)

    new_content = item_path.read_text("utf-8")
    assert item_file_content != new_content
    assert added_text in new_content


def test_document_reorder(qtbot: QtBot, app: DoorstopEdit, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ConfirmDialog, "ask", classmethod(lambda *_: True))

    with patch.object(doorstop.Document, "reorder") as doc_reorder_mock:
        with qtbot.wait_signal(app.window.ui.doc_reorder_level_tool_button.clicked):  # type: ignore
            qtbot.mouseClick(app.window.ui.doc_reorder_level_tool_button, Qt.MouseButton.LeftButton)

    assert doc_reorder_mock.call_count == 1


def test_document_review_all(qtbot: QtBot, app: DoorstopEdit, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ConfirmDialog, "ask", classmethod(lambda *_: True))

    with patch.object(doorstop.Item, "review") as item_review_mock:
        with qtbot.wait_signal(app.window.ui.doc_review_tool_button.clicked):  # type: ignore
            qtbot.mouseClick(app.window.ui.doc_review_tool_button, Qt.MouseButton.LeftButton)

    assert item_review_mock.call_count == NUM_ITEMS_PER_DOC


def test_document_clear_all_suspect_links(qtbot: QtBot, app: DoorstopEdit, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ConfirmDialog, "ask", classmethod(lambda *_: True))

    with patch.object(doorstop.Item, "clear") as item_clear_mock:
        with qtbot.wait_signal(app.window.ui.doc_clear_links_tool_button.clicked):  # type: ignore
            qtbot.mouseClick(app.window.ui.doc_clear_links_tool_button, Qt.MouseButton.LeftButton)

    assert item_clear_mock.call_count == NUM_ITEMS_PER_DOC
