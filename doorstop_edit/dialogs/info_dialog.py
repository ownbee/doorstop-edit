from typing import Callable, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QSizePolicy, QWidget

from doorstop_edit.ui_gen.ui_info_dialog import Ui_Dialog


class _InfoDialog(QDialog):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)


class InfoDialog:
    @staticmethod
    def inform(
        parent: QWidget,
        title: str,
        text: str,
        extra_button_name: Optional[str] = None,
        extra_button_cb: Optional[Callable[[], bool]] = None,
        extra_button_icon: str = "",
    ) -> None:
        dialog = _InfoDialog(parent)
        dialog.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        dialog.resize(100, 100)  # Set to very small, it will autoexpand to fit content.
        dialog.setContentsMargins(12, 12, 6, 0)
        dialog.setWindowTitle(title)
        dialog.ui.text.setTextFormat(Qt.TextFormat.RichText)
        dialog.ui.text.setText(text)

        extra_button = dialog.ui.buttons.button(QDialogButtonBox.StandardButton.Apply)
        if extra_button_name is None:
            extra_button.hide()
        else:
            extra_button.setText(extra_button_name)
            extra_button.setIcon(QIcon(extra_button_icon))
            if extra_button_cb is not None:
                extra_button.clicked.connect(extra_button_cb)

        dialog.exec()
