import functools
import logging
import re
from typing import Any, Callable, List, Optional, Tuple

import doorstop
import mdformat
from doorstop.core.types import UID as DOORSTOP_UID
from doorstop.core.types import Level as doorstop_Level
from doorstop.core.types import Text as doorstop_Text
from PySide6.QtCore import QPoint, QSize, Qt
from PySide6.QtGui import QAction, QGuiApplication, QIcon, QTextCursor, QValidator
from PySide6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QPlainTextEdit,
    QSizePolicy,
    QWidget,
)

from doorstop_edit.dialogs import ConfirmDialog, DiffDialog
from doorstop_edit.doorstop_data import DoorstopData
from doorstop_edit.item_edit.item_picker_dialog import ItemPickerDialog
from doorstop_edit.theme import Theme
from doorstop_edit.ui_gen.ui_main import Ui_MainWindow
from doorstop_edit.utils.custom_color_item_delegate import CustomColorItemDelegate
from doorstop_edit.utils.debug_timer import time_function

logger = logging.getLogger("gui")


class LevelQValidator(QValidator):
    def validate(self, text: str, _: int) -> QValidator.State:
        intermediate = re.match(r"^\d+(\.\d+)*?\.$", text)
        if len(text) == 0 or intermediate is not None:
            # On the way to be ok but not ok as final.
            return QValidator.State.Intermediate
        acceptable = re.match(r"^\d+(?:\.\d+)*?$", text)
        if acceptable is None:
            return QValidator.State.Invalid
        return QValidator.State.Acceptable

    def fixup(self, text: str) -> str:
        if text.endswith("."):
            text = text[:-1]
        return text


def bool_to_check_box(value: Any) -> Qt.CheckState:
    retval = Qt.CheckState.Unchecked
    if isinstance(value, str):
        if value.lower() == "true":
            retval = Qt.CheckState.Checked
    elif isinstance(value, bool):
        if value:
            retval = Qt.CheckState.Checked
    elif value is None:
        pass
    else:
        raise TypeError(f"Bad value type: {type(value)}")
    return retval


def check_box_to_bool(value: Any, _: Any) -> bool:
    if isinstance(value, int):
        state_value = Qt.CheckState(value)
    elif isinstance(value, Qt.CheckState):
        state_value = value
    else:
        raise TypeError(f"Bad value type: {type(value)}")
    return state_value == Qt.CheckState.Checked


def level_to_text_widget(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, doorstop_Level):
        return str(value)
    raise TypeError(f"Bad value type: {type(value)}")


def text_widget_to_level(value: str, _: Any) -> doorstop_Level:
    return doorstop_Level(value)


def str_to_str(value: Any, _: Any = None) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    raise TypeError(f"Bad value type: {type(value)}")


def str_to_doorstop_text(value: Any, _: Any) -> Any:
    if not isinstance(value, str):
        raise TypeError(f"Bad value type: {type(value)}")
    return doorstop_Text(value)


def links_to_list_widget(value: Any, doorstop_data: DoorstopData) -> List[QListWidgetItem]:
    if value is None:
        return []
    if isinstance(value, set):
        retval: List[QListWidgetItem] = []
        for link in value:
            if not (isinstance(link, DOORSTOP_UID) and isinstance(link.value, str)):
                logger.warning("Unknown type of link: %s, value: %s", type(link), link)
                continue

            parent_item = doorstop_data.find_item(link.value)
            extra_info = ""
            bg_color = None
            fg_color = None
            if parent_item is None or link.stamp != parent_item.stamp():
                extra_info = " (SUSPECT)"
                fg_color = Theme.WARNING_COLOR

            w_item = QListWidgetItem(link.value + extra_info)
            w_item.setText(link.value + extra_info)
            w_item.setData(Qt.ItemDataRole.UserRole, link.value)
            w_item.setData(CustomColorItemDelegate.STYLED_ITEM_ROLE, (bg_color, fg_color))
            retval.append(w_item)

        return retval

    raise TypeError(f"Bad value type: {type(value)}")


def list_widget_to_links(value: Tuple[QListWidgetItem, bool], orig: set, doorstop_data: DoorstopData) -> set:
    """Called when an item is removed or added."""
    if not isinstance(value, tuple):
        raise TypeError(f"Bad value type: {type(value)}")
    if not isinstance(orig, set):
        raise TypeError(f"Bad orig type: {type(orig)}")
    w_item, added = value
    item_uid = w_item.data(Qt.ItemDataRole.UserRole)

    link: DOORSTOP_UID

    found = False
    for link in orig:
        if not isinstance(link, DOORSTOP_UID):
            raise TypeError(f"Bad orig type: {type(link)}")
        if link.value == item_uid:
            found = True
            if not added:
                orig.remove(link)
            break

    if added and not found:
        parent = doorstop_data.find_item(item_uid)
        stamp = None
        if parent is not None:
            # If added, add ok stamp (non suspect) directly.
            stamp = parent.stamp()
        orig.add(DOORSTOP_UID(item_uid, stamp=stamp))

    return orig


class Field:
    def __init__(
        self,
        widget: QWidget,
        item_attr: str,
        conv_to_widget: Callable[[Any], Any],
        conv_from_widget: Callable[[Any, Any], Any],
        widget_validator: Optional[QValidator],
    ) -> None:
        self.widget = widget
        self.item_attr = item_attr
        self.conv_to_widget = conv_to_widget
        self.conv_from_widget = conv_from_widget
        self.widget_validator = widget_validator


class ItemEditView:
    def __init__(self, ui: Ui_MainWindow, doorstop_data: DoorstopData) -> None:
        self.ui = ui
        self._doorstop_data = doorstop_data
        self.on_item_changed: Callable[[doorstop.Item], None] = lambda x: print("on_item_changed not connected.")
        self.on_open_viewer: Callable[[str], None] = lambda x: logger.info("on_open_viewer not connected")
        self.item: Optional[doorstop.Item] = None
        self._disable_save = False
        self._loaded_extended_attributes: List[str] = []
        self.ui.edit_item_text_format_button.clicked.connect(self._on_text_format_button_pressed)  # type: ignore
        self.ui.edit_item_wrap_text_button.clicked.connect(self._on_wrap_text_button_pressed)  # type: ignore
        self.ui.item_edit_copy_uid_clipboard_button.clicked.connect(  # type: ignore
            self._on_copy_uid_to_clipboard_button_pressed
        )
        self.ui.item_edit_diff_button.clicked.connect(self._on_diff_button_pressed)  # type: ignore
        self.ui.item_edit_undo_button.clicked.connect(self._on_undo_button_pressed)  # type: ignore
        self.ui.item_edit_review_button.clicked.connect(self._on_review_button_pressed)  # type: ignore
        self.ui.item_edit_clear_suspects_button.clicked.connect(  # type: ignore
            self._on_clear_suspect_links_button_pressed
        )

        self.fields = [
            Field(
                widget=self.ui.item_edit_active_check_box,
                item_attr="active",
                conv_to_widget=bool_to_check_box,
                conv_from_widget=check_box_to_bool,
                widget_validator=None,
            ),
            Field(
                widget=self.ui.item_edit_derived_check_box,
                item_attr="derived",
                conv_to_widget=bool_to_check_box,
                conv_from_widget=check_box_to_bool,
                widget_validator=None,
            ),
            Field(
                widget=self.ui.item_edit_normative_check_box,
                item_attr="normative",
                conv_to_widget=bool_to_check_box,
                conv_from_widget=check_box_to_bool,
                widget_validator=None,
            ),
            Field(
                widget=self.ui.item_edit_level_line_edit,
                item_attr="level",
                conv_to_widget=level_to_text_widget,
                conv_from_widget=text_widget_to_level,
                widget_validator=LevelQValidator(),
            ),
            Field(
                widget=self.ui.item_edit_header_line_edit,
                item_attr="header",
                conv_to_widget=str_to_str,
                conv_from_widget=str_to_doorstop_text,
                widget_validator=None,
            ),
            Field(
                widget=self.ui.item_edit_text_text_edit,
                item_attr="text",
                conv_to_widget=str_to_str,
                conv_from_widget=str_to_doorstop_text,
                widget_validator=None,
            ),
        ]
        # Lists need special handling
        self.links_field = Field(
            widget=self.ui.item_edit_link_list,
            item_attr="links",
            conv_to_widget=functools.partial(links_to_list_widget, doorstop_data=self._doorstop_data),
            conv_from_widget=functools.partial(list_widget_to_links, doorstop_data=self._doorstop_data),
            widget_validator=None,
        )
        self.fields.append(self.links_field)

        self.ui.item_edit_link_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.ui.item_edit_link_list.customContextMenuRequested.connect(self._prepare_links_context_menu)  # type: ignore
        self.ui.item_edit_link_list.setItemDelegate(CustomColorItemDelegate(self.ui.item_edit_link_list))
        # Set validators
        for field in self.fields:
            if field.widget_validator is not None:
                if isinstance(field.widget, (QLineEdit)):
                    field.widget.setValidator(field.widget_validator)

        # Connect callbacks.
        for field in self.fields:
            self._connect_field(field)

        self._update_view()

    @time_function("Updating item in edit view")
    def update_item(self, item: Optional[doorstop.Item]) -> None:
        self.item = item

        if self.item is not None:
            self._parse_extended_attributes(self.item)

        self._update_view()

    def _connect_field(self, field: Field) -> None:
        if isinstance(field.widget, QLineEdit):
            field.widget.textChanged.connect(lambda x, field=field: self._on_field_updated(field, x))  # type: ignore
        elif isinstance(field.widget, QPlainTextEdit):
            field.widget.textChanged.connect(  # type: ignore
                lambda field=field: self._on_field_updated(field, field.widget.toPlainText())
            )
        elif isinstance(field.widget, QCheckBox):
            field.widget.stateChanged.connect(lambda x, field=field: self._on_field_updated(field, x))  # type: ignore
        elif isinstance(field.widget, QListWidget):
            pass  # Special handling...
        else:
            print(f"Warning: connect not implemented for {type(field.widget)}")

    def _parse_extended_attributes(self, item: doorstop.Item) -> None:
        """Parse extended attributes (lazy load) from item.

        We are assuming that all items have important extendend attributes and that extended
        attributes have the same type. Therefore extended attributes are added/parsed when an item
        is selected/edited. Found extended attributes will be permanently stored and visible for
        consecutive items (which might not have them).
        """

        def create_label(name: str, row: int) -> QLabel:
            label = QLabel(self.ui.item_edit_group)
            label.setObjectName(name + "_label")
            label.setText(name.replace("_", " ").replace("-", " ").capitalize())
            label.setMaximumWidth(100)  # Larger values will squeeze away space from the input boxes.
            label.setToolTip(f"Custom attribute '{name}'")
            self.ui.item_edit_form_layout.setWidget(row, QFormLayout.ItemRole.LabelRole, label)
            return label

        def create_text_edit(name: str, row: int) -> QPlainTextEdit:
            edit_text = QPlainTextEdit(self.ui.item_edit_group)
            edit_text.setObjectName(name + "_line_edit")
            edit_text.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            edit_text.setMinimumSize(QSize(200, 100))
            edit_text.setMaximumSize(QSize(620, 300))
            self.ui.item_edit_form_layout.setWidget(row, QFormLayout.ItemRole.FieldRole, edit_text)
            return edit_text

        def create_check_box(name: str, row: int) -> QCheckBox:
            check_box = QCheckBox(self.ui.item_edit_group)
            check_box.setObjectName(name + "_check_box")
            self.ui.item_edit_form_layout.setWidget(row, QFormLayout.ItemRole.FieldRole, check_box)
            return check_box

        ex_attr_name: str

        for ex_attr_name in item.extended:
            if ex_attr_name in self._loaded_extended_attributes:
                # Already loaded.
                continue
            row = self.ui.item_edit_form_layout.count() + 1
            attr = item.get(ex_attr_name)
            if attr is None:
                pass  # Do not parse None types, wait for some other time so we can get the proper type.
            if isinstance(attr, str):
                create_label(ex_attr_name, row)
                edit_text_widget = create_text_edit(ex_attr_name, row)
                field = Field(
                    widget=edit_text_widget,
                    item_attr=ex_attr_name,
                    conv_from_widget=str_to_doorstop_text,
                    conv_to_widget=str_to_str,
                    widget_validator=None,
                )
                self._connect_field(field)
                self.fields.append(field)
                self._loaded_extended_attributes.append(ex_attr_name)
            elif isinstance(attr, bool):
                create_label(ex_attr_name, row)
                check_box_widget = create_check_box(ex_attr_name, row)
                field = Field(
                    widget=check_box_widget,
                    item_attr=ex_attr_name,
                    conv_to_widget=bool_to_check_box,
                    conv_from_widget=check_box_to_bool,
                    widget_validator=None,
                )
                self._connect_field(field)
                self.fields.append(field)
                self._loaded_extended_attributes.append(ex_attr_name)
            else:
                # Skip attributes that dont have a supported type.
                logger.debug("Ignoring unsupported custom attribute type %s", type(attr))

    def _update_view(self) -> None:
        """Update all edit fields with item attributes."""
        # Disable saving while updating view, since it will trigger field changed callbacks and
        # write back to disk immidietenly which is problematic in all cases including when reverting
        # changes since it will change doorstop formatting in file.
        self._disable_save = True
        try:
            if self.item is None:
                self._enable(False)
                return

            self.ui.item_edit_uid.setText(str(self.item.uid))
            self._update_review_status()

            for field in self.fields:
                attr = self.item.attribute(field.item_attr)
                if isinstance(field.widget, QCheckBox):
                    field.widget.setCheckState(field.conv_to_widget(attr))
                elif isinstance(field.widget, (QPlainTextEdit)):
                    field.widget.setPlainText(field.conv_to_widget(attr))
                elif isinstance(field.widget, (QLineEdit)):
                    field.widget.setText(field.conv_to_widget(attr))
                elif isinstance(field.widget, (QListWidget)):
                    field.widget.clear()
                    for w_item in field.conv_to_widget(attr):
                        field.widget.addItem(w_item)
                else:
                    print(f"Warning: conv_to_widget not implemented for {type(field.widget)}")
            self._enable(True)
        finally:
            self._disable_save = False

    def _enable(self, enable: bool) -> None:
        self.ui.item_edit_diff_button.setEnabled(enable)
        self.ui.item_edit_review_button.setEnabled(enable)
        self.ui.item_edit_copy_uid_clipboard_button.setEnabled(enable)
        self.ui.item_edit_undo_button.setEnabled(enable)

        for field in self.fields:
            field.widget.setEnabled(enable)
            if not enable:
                if isinstance(field.widget, QCheckBox):
                    field.widget.setCheckState(Qt.CheckState.Unchecked)
                elif isinstance(field.widget, QPlainTextEdit):
                    field.widget.setPlainText("")
                elif isinstance(field.widget, QLineEdit):
                    field.widget.setText("")
                elif isinstance(field.widget, QListWidget):
                    field.widget.clear()
                else:
                    print(f"Warning: clear not implemented for {type(field.widget)}")

    def _update_review_status(self) -> None:
        if self.item is None:
            review_status_text = ""
            review_status_class = "success"
        elif self.item.reviewed:
            review_status_text = "REVIEWED"
            review_status_class = "success"
        else:
            review_status_text = "NOT REVIEWED"
            review_status_class = "warning"
        self.ui.item_edit_review_status_label.setText(review_status_text)
        self.ui.item_edit_review_status_label.setProperty("class", review_status_class)
        self.ui.item_edit_review_status_label.setStyleSheet("/* */")  # force update styling

    def _on_field_updated(self, field: Field, value: Any) -> None:
        if self.item is None or self._disable_save:
            return

        if field.widget_validator and field.widget_validator.validate(value, 0) != QValidator.State.Acceptable:
            return

        try:
            attr = self.item.attribute(field.item_attr)
            self.item._data[field.item_attr] = field.conv_from_widget(value, attr)
        except ValueError as e:
            # Only log, do not save or anything else.
            print(e)
            return

        self._doorstop_data.save_item(self.item)
        self._update_review_status()
        self.on_item_changed(self.item)

    def _remove_selected_links_from_widget(self) -> None:
        if self.item is None:
            return
        selected = self.ui.item_edit_link_list.selectedItems()
        for s in selected:
            w_item = self.ui.item_edit_link_list.takeItem(self.ui.item_edit_link_list.row(s))
            self._on_field_updated(self.links_field, (w_item, False))

    def _open_links_picker(self) -> None:
        dialog = ItemPickerDialog(self._doorstop_data, self._add_link)
        dialog.show()

    def _add_link(self, item_uid: str) -> None:
        w_item = QListWidgetItem(item_uid)
        w_item.setData(Qt.ItemDataRole.UserRole, item_uid)
        self.ui.item_edit_link_list.addItem(w_item)
        self._on_field_updated(self.links_field, (w_item, True))  # Propagate change to item.
        self._update_view()  # Redraw links list

    def _prepare_links_context_menu(self, pos: QPoint) -> None:
        """Called when user right-click on a tree item."""
        w_item = self.ui.item_edit_link_list.itemAt(pos)

        actions = []

        add_action = QAction(QIcon(":/icons/add-link"), "Add", self.ui.item_edit_link_list)
        add_action.triggered.connect(self._open_links_picker)  # type: ignore
        actions.append(add_action)

        if w_item is not None:
            item_uid = w_item.data(Qt.ItemDataRole.UserRole)

            remove_action = QAction(QIcon(":/icons/remove-link"), "Remove", self.ui.item_edit_link_list)
            remove_action.triggered.connect(self._remove_selected_links_from_widget)  # type: ignore
            actions.append(remove_action)

            view_action = QAction(QIcon(":/icons/view-item"), "Popup", self.ui.item_edit_link_list)
            view_action.triggered.connect(  # type: ignore
                lambda checked=False, item_uid=item_uid: self.on_open_viewer(item_uid)
            )
            actions.append(view_action)

        menu = QMenu(self.ui.item_edit_link_list)
        menu.addActions(actions)
        menu.exec(self.ui.item_edit_link_list.mapToGlobal(pos))

    def _on_wrap_text_button_pressed(self, checked: bool) -> None:
        self.ui.item_edit_text_text_edit.setLineWrapMode(
            QPlainTextEdit.LineWrapMode.WidgetWidth if checked else QPlainTextEdit.LineWrapMode.NoWrap
        )

    def _on_text_format_button_pressed(self) -> None:
        new_text = mdformat.text(
            self.ui.item_edit_text_text_edit.toPlainText(),
            options={
                "number": True,  # switch on consecutive numbering of ordered lists
                "wrap": 80,  # set word wrap width to 60 characters
            },
            extensions=["myst"],
        )
        # Using cursor for not bypassing undo buffer (Ctrl-Z).
        #
        # Copy of cursor but can be used since it has pointer to correct document.
        cursor = self.ui.item_edit_text_text_edit.textCursor()
        pos = cursor.position()  # Remember curret pos for restoring after operation
        cursor.beginEditBlock()  # For one entry in undo buffer.
        cursor.select(QTextCursor.SelectionType.Document)  # Select all text in document.
        cursor.removeSelectedText()
        cursor.insertText(new_text)
        cursor.endEditBlock()
        self.ui.item_edit_text_text_edit.setFocus()
        cursor.setPosition(pos)
        self.ui.item_edit_text_text_edit.setTextCursor(cursor)  # Set back the copied cursor for position update.

    def _on_copy_uid_to_clipboard_button_pressed(self) -> None:
        QGuiApplication.clipboard().setText(self.ui.item_edit_uid.text())

    def _on_diff_button_pressed(self) -> None:
        if self.item is None:
            return
        DiffDialog(self._doorstop_data).show(self.item)

    def _on_undo_button_pressed(self) -> None:
        if ConfirmDialog.ask(
            self.ui.edit_item_dock_widget, "Do you really want to undo all changes made to this item?"
        ):
            self._undo_item()

    def _undo_item(self) -> None:
        if self.item is None:
            return
        self._doorstop_data.restore_item(self.item)
        self._update_view()
        self.on_item_changed(self.item)  # Update tree view.

    def _on_review_button_pressed(self) -> None:
        if self.item is None:
            return

        if self.item.reviewed:
            return

        self.item.review()
        self._doorstop_data.save_item(self.item)
        self._update_view()  # Redraw review status.
        self.on_item_changed(self.item)  # Update tree view.

    def _on_clear_suspect_links_button_pressed(self) -> None:
        if self.item is None:
            return

        if self.item.cleared:
            return

        self.item.clear()
        self._doorstop_data.save_item(self.item)
        self._update_view()  # Redraw links list.
        self.on_item_changed(self.item)  # Update tree view.
