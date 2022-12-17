from typing import Callable, Optional

from PySide6.QtWidgets import QDialog, QDialogButtonBox

from doorstop_edit.ui_gen.ui_info_dialog import Ui_Dialog


class _InfoDialog(QDialog):
    def __init__(self) -> None:
        super().__init__()
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)


class InfoDialog:
    def __init__(
        self,
        title: str,
        text: str,
        extra_button_name: Optional[str] = None,
        extra_button_cb: Optional[Callable[[], bool]] = None,
    ) -> None:
        self._extra_button_cb = extra_button_cb

        self._dialog = _InfoDialog()
        extra_button = self._dialog.ui.buttons.button(QDialogButtonBox.StandardButton.Apply)
        self._dialog.ui.text.setText(text)
        self._dialog.setWindowTitle(title)
        if extra_button_name is None:
            extra_button.hide()
        else:
            extra_button.clicked.connect(self._on_extra_button_clicked)  # type: ignore
            extra_button.setText(extra_button_name)

        self._dialog.exec()

    def _on_extra_button_clicked(self) -> None:
        if self._extra_button_cb is not None:
            if not self._extra_button_cb():
                self._dialog.close()
