from typing import Callable, List

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QListWidgetItem, QWidget

from doorstop_edit.doorstop_data import DoorstopData
from doorstop_edit.ui_gen.ui_item_picker import Ui_ItemPickerDialog
from doorstop_edit.utils.item_utils import match_item


class _ItemPickerDialog(QDialog):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.ui = Ui_ItemPickerDialog()
        self.ui.setupUi(self)


class ItemPickerDialog:
    def __init__(self, parent: QWidget, doorstop_data: DoorstopData, on_selected: Callable[[str], None]) -> None:
        self._dialog = _ItemPickerDialog(parent)
        self._doorstop_data = doorstop_data
        self._on_selected = on_selected

        self._dialog.ui.search.textChanged.connect(self._on_search_input_changed)
        self._dialog.ui.buttons.accepted.connect(self._on_accepted_button_pressed)
        self._update_search_result([])

    def show(self) -> None:
        self._dialog.exec_()

    def _on_search_input_changed(self, text: str) -> None:
        self._update_search_result(text.split())

    def _update_search_result(self, search: List[str]) -> None:
        self._dialog.ui.search_result.clear()
        for item in self._doorstop_data.iter_items():
            if not match_item(item, search):
                continue

            text = f"[{item}] - {item.header}"
            w_item = QListWidgetItem(text)
            w_item.setData(Qt.ItemDataRole.UserRole, str(item.uid))
            w_item.setData(
                Qt.ItemDataRole.ToolTipRole,
                item.text,
            )
            self._dialog.ui.search_result.addItem(w_item)
        self._dialog.ui.search_result.sortItems()

    def _on_accepted_button_pressed(self) -> None:
        selected_items = self._dialog.ui.search_result.selectedItems()
        if len(selected_items) == 0:
            return
        item_uid = selected_items[0].data(Qt.ItemDataRole.UserRole)
        self._on_selected(item_uid)
