import logging

from PySide6.QtCore import QPoint, Qt, Slot
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QListWidget, QListWidgetItem, QMenu

from doorstop_edit.app_signals import AppSignals
from doorstop_edit.doorstop_data import DoorstopData

logger = logging.getLogger("gui")


class PinnedItemsView:
    def __init__(self, signals: AppSignals, doorstop_data: DoorstopData, list_widget: QListWidget) -> None:
        self._signals = signals
        self._doorstop_data = doorstop_data
        self._list_widget = list_widget
        self._list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._list_widget.customContextMenuRequested.connect(self._prepare_links_context_menu)
        self._list_widget.itemDoubleClicked.connect(self._on_item_clicked)

    @Slot(str)
    def add(self, item_uid: str) -> None:
        item = self._doorstop_data.find_item(item_uid)
        if item is None:
            return
        text = f"[{item.uid}] [{item.level}] {item.header}"
        w_item = QListWidgetItem(text)
        w_item.setData(Qt.ItemDataRole.UserRole, item.uid.value)
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
        uid: str = selected.data(Qt.ItemDataRole.UserRole)
        self._signals.view_item.emit(uid, False)

    def _prepare_links_context_menu(self, pos: QPoint) -> None:
        """Called when user right-click on an item."""
        w_item = self._list_widget.itemAt(pos)
        actions = []

        if w_item is not None:
            remove_action = QAction(QIcon(":/icons/unpin"), "Unpin", self._list_widget)
            remove_action.triggered.connect(self._remove_selected)
            actions.append(remove_action)

            view_action = QAction(QIcon(":/icons/view-item"), "Popup", self._list_widget)
            view_action.triggered.connect(
                lambda checked=False, item_uid=w_item.data(Qt.ItemDataRole.UserRole): self._signals.view_item.emit(
                    item_uid, True
                )
            )
            actions.append(view_action)

        menu = QMenu(self._list_widget)
        menu.addActions(actions)
        menu.exec(self._list_widget.mapToGlobal(pos))
