import logging
from typing import Callable, List, Optional, Tuple, Union

import doorstop
from PySide6.QtCore import QPoint, Qt, Slot
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QLineEdit, QMenu, QTreeWidget, QTreeWidgetItem

from doorstop_edit.dialogs import ConfirmDialog
from doorstop_edit.doorstop_data import DoorstopData
from doorstop_edit.item_tree.document_item_level_tree import (
    DocumentItemLevelTree,
    build_item_level_tree,
)
from doorstop_edit.theme import Theme
from doorstop_edit.utils.custom_color_item_delegate import CustomColorItemDelegate
from doorstop_edit.utils.debug_timer import time_function
from doorstop_edit.utils.item_matcher import match_item

logger = logging.getLogger("gui")


class ItemTreeView:
    UID_COLUMN = 2

    def __init__(
        self,
        tree_widget: QTreeWidget,
        item_tree_search_input: QLineEdit,
        doorstop_data: DoorstopData,
    ) -> None:
        self._tree_widget = tree_widget
        self._tree_widget.setColumnCount(2)
        self._tree_widget.setHeaderLabels(["Level", "Header"])
        self._tree_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._tree_widget.itemSelectionChanged.connect(self._on_item_selection_changed)
        self._tree_widget.itemPressed.connect(self._on_item_pressed)
        self._tree_widget.customContextMenuRequested.connect(self._prepare_context_menu)
        self._tree_widget.setItemDelegate(CustomColorItemDelegate(self._tree_widget, paint_border=False))
        self._item_tree_search_input = item_tree_search_input
        self._item_tree_search_input.textChanged.connect(self._on_search_input_changed)
        self._doorstop_data = doorstop_data

        self._selected_document_name: Optional[str] = None
        self._selected_item_uids: List[str] = []

        self.on_items_selected: Callable[[List[str]], None] = lambda x: logger.info("on_items_selected not conntected")
        self.on_pinned_item: Callable[[str], None] = lambda x: logger.info("on_pinned_item not connected")
        self.on_add_item: Callable[[Optional[str]], None] = lambda item_uid: logger.info(
            "on_add_item not connected, called with uid %s", item_uid
        )
        self.on_open_viewer: Callable[[str], None] = lambda x: logger.info("on_open_viewer not connected")

        self._filter_show_inactive = False
        self._filter_search_input: List[str] = []

        self._tree_widget.clear()  # Clear demo stuff created in designer.

    def _update_style(self, w_item: QTreeWidgetItem, item: doorstop.Item) -> None:

        bg_color = None
        fg_color = None
        font_style = ""
        # Set color indication in priority:
        if not item.reviewed:
            fg_color = Theme.WARNING_COLOR
        elif not bool(item.active):
            fg_color = Theme.DISABLE_COLOR
        elif not item.cleared:
            # Suspect links does not matter if inactive.
            fg_color = Theme.WARNING_COLOR
        elif not bool(item.normative):
            fg_color = Theme.NON_IMPROTANT_COLOR

        text = str(item.header)

        if not bool(item.normative) and str(item.level).endswith(".0"):
            # Header-only item.
            font_style = "b"
            test_lines = item.text.splitlines()
            if len(test_lines) > 0:
                text = test_lines[0]
            else:
                text = ""

        if self._doorstop_data.has_item_changed(item):
            text = "•" + text

        w_item.setText(0, str(item.level))
        w_item.setData(
            0,
            CustomColorItemDelegate.STYLED_ITEM_ROLE,
            (bg_color, fg_color, font_style),
        )
        w_item.setText(1, text)
        w_item.setData(
            1,
            CustomColorItemDelegate.STYLED_ITEM_ROLE,
            (bg_color, fg_color, font_style),
        )

    def _build(
        self, item_tree: DocumentItemLevelTree, parent: Optional[QTreeWidgetItem] = None
    ) -> Tuple[List[QTreeWidgetItem], List[QTreeWidgetItem]]:
        """Build DocumentItemTree into a list of QTreeWidgetItem.

        If parent is None, a list of items will be returned (if anything in the tree). If parent is
        not None, the items will be added to parent instead.

        Return: Tuple of (selected_items, top_level_items)
        """
        selected: List[QTreeWidgetItem] = []
        orphans: List[QTreeWidgetItem] = []
        w_item: Optional[QTreeWidgetItem] = None
        for item in item_tree.items:
            if not item.active and not self._filter_show_inactive:
                continue
            if not match_item(item, self._filter_search_input):
                continue
            w_item = QTreeWidgetItem()
            if item.uid in self._selected_item_uids:
                selected.append(w_item)
            self._update_style(w_item, item)
            w_item.setData(self.UID_COLUMN, Qt.ItemDataRole.UserRole, item.uid.value)
            if parent is None:
                orphans.append(w_item)
            else:
                parent.addChild(w_item)

        children_parent: Optional[QTreeWidgetItem]
        if w_item is None:
            # Ideally, there should only be one item in the above loop, but in case there is
            # mulitple item with same level we use last item as childrens parent.
            children_parent = parent
        else:
            children_parent = w_item

        for child in item_tree.content.values():
            # In case children had no parent, the function will return its items which we need to
            # pass upwards.
            sel, orph = self._build(child, children_parent)
            selected.extend(sel)
            orphans.extend(orph)

        return selected, orphans

    def update_selected_items(self, items: List[doorstop.Item]) -> None:
        for w_item in self._tree_widget.selectedItems():
            uid = w_item.data(ItemTreeView.UID_COLUMN, Qt.ItemDataRole.UserRole)
            for item in items:
                if item.uid == uid:
                    self._tree_widget.openPersistentEditor(w_item)
                    self._update_style(w_item, item)
                    self._tree_widget.closePersistentEditor(w_item)

    def set_selected_items(self, items: List[Union[str, doorstop.Item]]) -> None:
        norm_items = []
        for item in items:
            if isinstance(item, doorstop.Item):
                norm_items.append(str(item.uid))
            else:
                norm_items.append(item)
        self._selected_item_uids = norm_items
        self._update()

    def update(self, document_name: str) -> None:
        self._selected_document_name = document_name
        self._update()

    @time_function("Updating tree view")
    def _update(self, notify_change: bool = True) -> None:
        if self._selected_document_name is None:
            return
        doc = self._doorstop_data.find_document(self._selected_document_name)
        if doc is None:
            self._selected_document_name = None
            return
        selected_w_items, top_level_w_items = self._build(build_item_level_tree(doc))
        # Clear selection before insert since it will generate a lot of selection changed otherwise.
        # Does not completely eleminate the "problem" in all cases though.
        self._tree_widget.clearSelection()
        self._tree_widget.clear()
        self._tree_widget.insertTopLevelItems(0, top_level_w_items)
        if notify_change:
            self.notify_change = True
        for w_item in selected_w_items:
            self._tree_widget.setCurrentItem(w_item)

    @Slot()
    def _on_item_selection_changed(self) -> None:
        pass

    @Slot(QTreeWidgetItem, int)
    def _on_item_pressed(self, item: QTreeWidgetItem, _2: int) -> None:
        self.notify_change = True
        self._set_selection()

    def _set_selection(self) -> None:
        items = self._tree_widget.selectedItems()
        item_uids = [i.data(ItemTreeView.UID_COLUMN, Qt.ItemDataRole.UserRole) for i in items]
        self._selected_item_uids = item_uids
        if self.notify_change and len(self._selected_item_uids) > 0:
            self.on_items_selected(item_uids)
            self.notify_change = False

    def _on_show_inactive_items(self, checked: bool) -> None:
        self._filter_show_inactive = checked
        self._update()

    def _on_search_input_changed(self, text: str) -> None:
        """Called when search box content changes."""
        self._filter_search_input = text.split()
        self._update(notify_change=False)

    def _on_delete_item_button_clicked(self, item_uid: str) -> None:
        if not ConfirmDialog.ask(self._tree_widget, f"Do you really want to delete item with UID '{item_uid}'?"):
            return

        item = self._doorstop_data.find_item(item_uid, self._selected_document_name)
        if item is None:
            return
        item.delete()
        self._update()

    def _prepare_context_menu(self, pos: QPoint) -> None:
        """Called when user right-click on a tree item."""
        w_item = self._tree_widget.itemAt(pos)
        menu = QMenu(self._tree_widget)

        show_inactive_action = QAction(
            QIcon(":/icons/file-hidden"),
            "Hide Inactive" if self._filter_show_inactive else "Show Inactive",
            self._tree_widget,
        )
        show_inactive_action.triggered.connect(self._on_show_inactive_items)
        show_inactive_action.setCheckable(True)
        show_inactive_action.setChecked(self._filter_show_inactive)

        reload_action = QAction(
            QIcon(":/icons/reload"),
            "Reload Tree",
            self._tree_widget,
        )
        reload_action.triggered.connect(self._update)

        expand_action = QAction(
            QIcon(":/icons/unfold-more"),
            "Expand All",
            self._tree_widget,
        )
        expand_action.triggered.connect(self._tree_widget.expandAll)

        collapse_action = QAction(
            QIcon(":/icons/unfold-less"),
            "Collapse All",
            self._tree_widget,
        )
        collapse_action.triggered.connect(self._tree_widget.collapseAll)

        item_uid: Optional[str] = None
        item_actions: List[QAction] = []
        if w_item is not None:
            item_uid = w_item.data(self.UID_COLUMN, Qt.ItemDataRole.UserRole)

            delete_action = QAction(QIcon(":/icons/trash-can"), "Delete Item", self._tree_widget)
            delete_action.setCheckable(False)
            delete_action.triggered.connect(
                lambda checked=False, item_uid=item_uid: self._on_delete_item_button_clicked(item_uid)
            )

            pin_action = QAction(QIcon(":/icons/pin"), "Pin", self._tree_widget)
            pin_action.setCheckable(False)
            pin_action.triggered.connect(lambda checked=False, item_uid=item_uid: self.on_pinned_item(item_uid))

            view_action = QAction(QIcon(":/icons/view-item"), "Popup", self._tree_widget)
            view_action.triggered.connect(lambda checked=False, item_uid=item_uid: self.on_open_viewer(item_uid))

            item_actions.append(delete_action)
            item_actions.append(pin_action)
            item_actions.append(view_action)

        add_action = QAction(QIcon(":/icons/add-item"), "New Item", self._tree_widget)
        add_action.triggered.connect(lambda checked=False, uid=item_uid: self.on_add_item(item_uid=uid))  # type: ignore

        actions = []
        actions.append(add_action)
        actions.append(show_inactive_action)
        actions.append(reload_action)
        actions.append(expand_action)
        actions.append(collapse_action)

        if len(item_actions) > 0:
            actions.append(menu.addSeparator())
            actions.extend(item_actions)

        menu = QMenu(self._tree_widget)
        menu.addActions(actions)
        menu.exec(self._tree_widget.mapToGlobal(pos))
