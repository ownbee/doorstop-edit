import logging
from typing import Callable

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QListWidget, QListWidgetItem, QMenu

from doorstop_edit.doorstop_data import DoorstopData

logger = logging.getLogger("gui")


class PinnedItemsView:
    def __init__(self, doorstop_data: DoorstopData, list_widget: QListWidget) -> None:
        self._doorstop_data = doorstop_data
        self._list_widget = list_widget
        self.on_selected_item: Callable[[str], None] = lambda item_uid: logger.debug(
            "on_selected_item not connected, called with: %d", item_uid
        )
        self._list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._list_widget.customContextMenuRequested.connect(self._prepare_links_context_menu)
        self._list_widget.itemClicked.connect(self._on_item_clicked)

    def add(self, item_uid: str) -> None:
        item = self._doorstop_data.find_item(item_uid)
        if item is None:
            return
        text = f"[{item.uid}] {item.level} - {item.header}"
        w_item = QListWidgetItem(text)
        w_item.setData(1, str(item.uid))
        self._list_widget.addItem(w_item)

    def _remove_selected(self) -> None:
        selected = self._list_widget.selectedItems()
        for s in selected:
            self._list_widget.takeItem(self._list_widget.row(s))

    def _on_item_clicked(self, _: bool) -> None:
        selected_items = self._list_widget.selectedItems()
        if len(selected_items) == 0:
            return
        selected = selected_items[-1]
        uid: str = selected.data(1)
        self.on_selected_item(uid)

    def _prepare_links_context_menu(self, pos: QPoint) -> None:
        """Called when user right-click on an item."""
        w_item = self._list_widget.itemAt(pos)
        actions = []

        if w_item is not None:
            remove_action = QAction(QIcon(":/icons/unpin"), "Unpin", self._list_widget)
            remove_action.triggered.connect(self._remove_selected)
            actions.append(remove_action)

        menu = QMenu(self._list_widget)
        menu.addActions(actions)
        menu.exec(self._list_widget.mapToGlobal(pos))
