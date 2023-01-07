from PySide6.QtWidgets import QDialog, QWidget

from doorstop_edit.ui_gen.ui_confirm_dialog import Ui_Dialog


class _ConfirmDialog(QDialog):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)


class ConfirmDialog:
    @classmethod
    def ask(cls, parent: QWidget, question: str) -> bool:
        dialog = _ConfirmDialog(parent)
        dialog.ui.text.setText(question)
        return dialog.exec() == QDialog.DialogCode.Accepted
