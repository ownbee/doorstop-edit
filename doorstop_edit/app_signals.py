import doorstop
from PySide6.QtCore import QObject, Signal


class AppSignals(QObject):
    view_item = Signal(str, bool)  # (item_uid, new_window)
    add_item = Signal(str)  # (after_item_uid)
    add_pin = Signal(str)  # (item_uid)
    item_changed = Signal(doorstop.Item)  # (item)

    def __init__(self, parent: QObject) -> None:
        super().__init__(parent)
