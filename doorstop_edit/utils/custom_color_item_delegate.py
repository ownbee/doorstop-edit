import logging
from typing import Union

from PySide6.QtCore import QModelIndex, QPersistentModelIndex, QRect, Qt
from PySide6.QtGui import QBrush, QColor, QPainter, QPen
from PySide6.QtWidgets import QStyle, QStyledItemDelegate, QStyleOptionViewItem

from doorstop_edit.theme import Theme

logger = logging.getLogger("gui")


class CustomColorItemDelegate(QStyledItemDelegate):
    """ItemDelegate for coloring individual items in lists.

    This class only exists because it is impossible to set custom style on individual items while
    using a stylesheet on parent (list) object.

    How it works; Create an instance of this class and assign it as ItemDelegate to your list/tree
    widget. Then for each item in the widget, set tuple (background_color, foreground_color, font_style) of type
    (Opional[QColor], Optional[QColor], Optional[str]) as the items data with role
    `STYLE_ITEM_ROLE`. Where font_style can contant characters b (bold), i (italic), u (underline)

    Setting a color to NONE will result in default theme color.
    """

    STYLED_ITEM_ROLE = Qt.ItemDataRole.UserRole + 10

    def __init__(self, parent=None, paint_border: bool = True):
        QStyledItemDelegate.__init__(self)
        if parent is not None:
            self.setParent(parent)
        self.paint_border = paint_border
        # offset item.rect - colored rect
        self.offset = 0
        # different backgroundcolors
        self.selected_brush = QBrush(Theme.PRIMARY_COLOR)
        self.selected_bg_brush = QBrush(
            QColor(
                Theme.PRIMARY_COLOR.red(),
                Theme.PRIMARY_COLOR.green(),
                Theme.PRIMARY_COLOR.blue(),
                10,
            )
        )
        self.warning_brush = QBrush(QColor("darkGray"))
        self.default_background_brush = QBrush(Theme.SECONDARY_COLOR)
        # textcolor
        self.default_textpen = QPen(Theme.SECONDARY_TEXT_COLOR)
        # linecolor and -width
        self.linePen = QPen(Theme.SECONDARY_DARK_COLOR)
        self.linePen.setWidth(2)
        # Alignment
        self.alignment_flag = Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionViewItem,
        index: Union[QModelIndex, QPersistentModelIndex],
    ):

        # Parse out colors from item
        style_data = index.model().data(index, self.STYLED_ITEM_ROLE)
        bg_brush = self.default_background_brush
        fg_pin = self.default_textpen
        font_style = ""
        if style_data is not None:
            if isinstance(style_data, QColor):
                bg_brush = QBrush(style_data)
            elif isinstance(style_data, tuple):
                if isinstance(style_data[0], QColor):
                    bg_brush = QBrush(style_data[0])
                if len(style_data) > 1 and isinstance(style_data[1], QColor):
                    fg_pin = QPen(style_data[1])
                if len(style_data) > 2 and isinstance(style_data[2], str):
                    font_style = style_data[2].lower()

        text = index.model().data(index, Qt.ItemDataRole.DisplayRole)
        item_state: QStyle.StateFlag = option.state  # type: ignore
        rect: QRect = option.rect  # type: ignore
        select_mark_rect = QRect(rect.left(), rect.top(), 10, rect.height())
        item_rect = rect.adjusted(self.offset, self.offset, -self.offset, -self.offset)

        painter.save()
        # paint background
        painter.fillRect(item_rect, bg_brush)

        if item_state & QStyle.StateFlag.State_Selected:
            painter.fillRect(item_rect, self.selected_bg_brush)
            if index.column() == 0:
                painter.fillRect(select_mark_rect, self.selected_brush)

        # paint text
        painter.setPen(fg_pin)
        font = painter.font()
        if "b" in font_style:
            font.setBold(True)
        if "i" in font_style:
            font.setItalic(True)
        if "u" in font_style:
            font.setUnderline(True)
        painter.setFont(font)
        painter.drawText(item_rect, self.alignment_flag, (" " * 6) + text)

        if self.paint_border:
            # paint bottom border
            painter.setPen(self.linePen)
            painter.drawLine(rect.bottomLeft(), rect.bottomRight())
        painter.restore()
