from typing import Callable

from PySide6.QtWidgets import QDialog

from doorstop_edit.ui_gen.ui_confirm_dialog import Ui_Dialog


class _ConfirmDialog(QDialog):
    def __init__(self) -> None:
        super().__init__()
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)


class ConfirmDialog:
    def __init__(self, question: str, on_yes: Callable[[], None]) -> None:
        self._dialog = _ConfirmDialog()
        self._on_yes = on_yes
        self._dialog.ui.text.setText(question)
        self._dialog.ui.button.accepted.connect(self._on_yes)  # type: ignore
        self._dialog.exec()
