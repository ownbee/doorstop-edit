import functools
import logging
from pathlib import Path
from typing import List, Optional

import doorstop
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication, QDialog, QDockWidget, QMainWindow

from doorstop_edit.dialogs import ConfirmDialog, InfoDialog
from doorstop_edit.doorstop_data import DoorstopData
from doorstop_edit.item_edit.item_edit_view import ItemEditView
from doorstop_edit.item_render.item_render_view import ItemRenderView
from doorstop_edit.item_tree.item_tree_view import ItemTreeView
from doorstop_edit.pinned_items.pinned_items_view import PinnedItemsView
from doorstop_edit.ui_gen.ui_item_viewer import Ui_ItemViewer
from doorstop_edit.ui_gen.ui_main import Ui_MainWindow
from doorstop_edit.utils.version_summary import create_version_summary

logger = logging.getLogger("gui")


class _MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)


class DoorstopEdit:
    def __init__(self, root: Path) -> None:
        self.window = _MainWindow()
        self.doorstop_data = DoorstopData(self.window, root)
        self.doorstop_data.tree_changed.connect(self._on_tree_changed)

        self.window.ui.menu_action_exit.triggered.connect(QApplication.exit)
        self.window.ui.menu_action_show_document_tree.triggered[bool].connect(  # type: ignore
            lambda checked, dock=self.window.ui.item_tree_dock_widget: self._on_toggle_dock_widget(checked, dock)
        )
        self.window.ui.menu_action_show_item_editor.triggered[bool].connect(  # type: ignore
            lambda checked, dock=self.window.ui.edit_item_dock_widget: self._on_toggle_dock_widget(checked, dock)
        )
        self.window.ui.menu_action_show_pinned_items.triggered[bool].connect(  # type: ignore
            lambda checked, dock=self.window.ui.pinned_items_dock_widget: self._on_toggle_dock_widget(checked, dock)
        )
        self.window.ui.menu_action_about.triggered[bool].connect(  # type: ignore
            lambda checked=False: self._on_about_clicked()
        )
        self.item_render_view = ItemRenderView(self.window.ui.web_engine_view, self.doorstop_data)

        self.tree_view = ItemTreeView(
            self.window.ui.item_tree_widget,
            self.window.ui.item_tree_search_input,
            self.doorstop_data,
        )
        self.tree_view.on_items_selected = self._on_item_tree_selection_changed
        self.tree_view.on_add_item = self._on_add_item
        self.tree_view.on_open_viewer = self._popup_item_viewer

        self.pinned_items_view = PinnedItemsView(self.doorstop_data, self.window.ui.pinned_items_list)
        self.pinned_items_view.on_selected_item = self._on_selected_pinned_item
        self.tree_view.on_pinned_item = self.pinned_items_view.add

        self.item_edit_view = ItemEditView(self.window.ui, self.doorstop_data)
        self.item_edit_view.on_item_changed = self._on_item_edit
        self.item_edit_view.on_open_viewer = self._popup_item_viewer
        self.window.ui.tree_combo_box.currentIndexChanged.connect(self._on_selected_document_change)
        self.window.ui.view_items_section_mode.clicked.connect(self._on_section_mode_changed)
        self.window.ui.doc_review_tool_button.clicked.connect(self._on_doc_review_all_button_clicked)
        self.window.ui.doc_clear_links_tool_button.clicked.connect(self._on_doc_clear_all_links_button_clicked)
        self.window.ui.doc_reorder_level_tool_button.clicked.connect(self._on_doc_reoder_all_button_clicked)

        self.selected_document: Optional[doorstop.Document] = None
        # Adjust docks width to a sane default (designer seem to not support it).
        self.window.resizeDocks(
            [self.window.ui.item_tree_dock_widget, self.window.ui.edit_item_dock_widget],
            [500, 800],
            Qt.Orientation.Horizontal,
        )

        self.item_render_view.show(None)  # Set empty but with correct colors (css).

        # Called last since it will trigger view updates.
        self.doorstop_data.rebuild(False)

    def show(self) -> None:
        self.window.show()

        if len(self.doorstop_data.get_documents()) == 0:
            msg = "No doorstop documents found in project root."
            InfoDialog.inform(self.window, "Empty project", msg)

    def quit(self) -> None:
        """Tear down resources that needs to be teared down before exit."""
        logger.debug("Quitting...")
        self.item_render_view.destroy()
        self.window.close()

    def _update_document_list(self) -> None:

        self.window.ui.tree_combo_box.clear()
        for name, doc in self.doorstop_data.get_documents().items():
            parent = self.doorstop_data.find_document(doc.parent)
            if parent is None:
                parent_text = ""
            else:
                parent_text = f" (-> {parent.prefix})"
            text = name + parent_text
            self.window.ui.tree_combo_box.addItem(text, name)

    def _update_item_tree(self, document: doorstop.Document) -> None:
        self.tree_view.update(document.prefix)

    def _update_used_document(self, document: doorstop.Document) -> None:
        """Reload or change used/selected document."""
        self.selected_document = document
        self._update_item_tree(document)

    def _on_item_tree_selection_changed(self, item_uids: List[str]) -> None:
        if len(item_uids) == 0:
            return

        if not self.selected_document:
            return

        logger.debug("Item tree selection changed to %s", item_uids)

        try:
            item = self.doorstop_data.find_item(item_uids[0], self.selected_document)
            if item is None:
                return
            item.load(reload=True)  # In case change on disk.
            self.item_render_view.show(item)
            self.item_edit_view.update_item(item)
        except doorstop.DoorstopError as e:
            print(e)
            return

    def _on_selected_document_change(self, index: int) -> None:
        if index == -1:
            return  # Document list cleared, do nothing.

        doc_uid = self.window.ui.tree_combo_box.itemData(index)

        logger.debug("Selected document changed to %s", doc_uid)

        doc = self.doorstop_data.find_document(doc_uid)
        if doc is None:
            return

        self._update_used_document(doc)

    def _on_section_mode_changed(self, is_active: bool) -> None:
        self.item_render_view.set_section_mode(is_active)

    def _on_item_edit(self, item: doorstop.Item) -> None:
        self.item_render_view.show(item)
        self.tree_view.update_selected_items([item])

    def _on_add_item(self, item_uid: Optional[str]) -> None:
        if self.selected_document is None:
            return

        level = None
        if item_uid is not None:
            item = self.doorstop_data.find_item(item_uid)
            if item is not None:
                try:
                    level = str(item.level)
                    level_last = int(level[-1])
                    level = level[:-1] + str(level_last + 1)
                except Exception:
                    pass

        new_item = self.selected_document.add_item(level=level, reorder=False)
        new_item.header = "New item"
        new_item.normative = True
        new_item.active = True
        self.doorstop_data.save_item(new_item)
        self.tree_view.set_selected_items([new_item])

    def _on_toggle_dock_widget(self, checked: bool, dock: QDockWidget) -> None:
        if checked:
            dock.show()
        else:
            dock.close()

    def _on_selected_pinned_item(self, item_uid: str) -> None:
        item = self.doorstop_data.find_item(item_uid)
        if item is None:
            return
        self.item_render_view.show(item)
        self.item_edit_view.update_item(item)

    def _on_about_clicked(self) -> None:
        def on_clicked(text: str) -> bool:
            QGuiApplication.clipboard().setText(text)
            return True

        version_summary = create_version_summary()
        msg = f"""\n
<h3>Doorstop Edit</h3>
<p>
{"".join([f'{x}<br>' for x in version_summary.splitlines()])}
</p>
"""
        InfoDialog.inform(
            self.window,
            "About",
            msg,
            extra_button_name="Copy",
            extra_button_cb=functools.partial(on_clicked, version_summary),
            extra_button_icon=":/icons/copy",
        )

    def _popup_item_viewer(self, item_uid: str) -> None:
        item = self.doorstop_data.find_item(item_uid)
        if item is None:
            return
        ui = Ui_ItemViewer()
        w = QDialog(self.window, Qt.WindowType.Window)
        ui.setupUi(w)
        irv = ItemRenderView(ui.web_engine_view, self.doorstop_data)
        irv.show(item)
        w.show()
        w.setWindowTitle(f"[{item.uid}] {item.header}")

    def _on_doc_review_all_button_clicked(self) -> None:
        if not ConfirmDialog.ask(
            self.window,
            """\
Are you sure you want to mark all items as reviewed?

WARNING: This operation cannot be undone!
""",
        ):
            return

        if self.selected_document is None:
            return

        for item in self.doorstop_data.iter_items(self.selected_document):
            item.review()
            self.doorstop_data.save_item(item)

        self.tree_view.update(self.selected_document.prefix)
        self.item_edit_view.update_item(None)

    def _on_doc_clear_all_links_button_clicked(self) -> None:
        if not ConfirmDialog.ask(
            self.window,
            """\
Are you sure you want to clear all suspect links in selected document?

WARNING: This operation cannot be undone!
""",
        ):
            return

        if self.selected_document is None:
            return

        for item in self.doorstop_data.iter_items(self.selected_document):
            item.clear()
            self.doorstop_data.save_item(item)

        self.tree_view.update(self.selected_document.prefix)
        self.item_edit_view.update_item(None)

    def _on_doc_reoder_all_button_clicked(self) -> None:
        if not ConfirmDialog.ask(
            self.window,
            """\
Are you sure you want do an automatic level reorder of of all items in selected document?

WARNING: This operation cannot be undone!
""",
        ):
            return

        if self.selected_document is None:
            return

        self.selected_document.reorder(manual=False)

        for item in self.doorstop_data.iter_items(self.selected_document):
            self.doorstop_data.save_item(item)

        self.tree_view.update(self.selected_document.prefix)
        self.item_edit_view.update_item(None)

    @Slot(bool)
    def _on_tree_changed(self, modified_only: bool) -> None:
        if not modified_only:
            self._update_document_list()
        if self.selected_document:
            self._update_item_tree(self.selected_document)
        self.item_edit_view.reload()
