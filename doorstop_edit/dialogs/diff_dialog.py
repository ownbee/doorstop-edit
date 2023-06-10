import enum
import functools
import logging
from pathlib import Path
from typing import Optional

import doorstop
import pygments
from pygments.formatters import HtmlFormatter
from pygments.lexers.diff import DiffLexer
from pygments.styles.gh_dark import GhDarkStyle
from PySide6.QtWidgets import QDialog, QWidget

from doorstop_edit.dialogs.differs import Differ, GitDiffer, SimpleDiffer
from doorstop_edit.doorstop_data import DoorstopData
from doorstop_edit.ui_gen.ui_diff_dialog import Ui_diff_dialog

logger = logging.getLogger("gui")


class _DiffDialog(QDialog):
    def __init__(self, parent: Optional[QWidget]) -> None:
        super().__init__(parent)
        self.ui = Ui_diff_dialog()
        self.ui.setupUi(self)


class DiffMode(enum.Enum):
    SIMPLE = 1
    GIT = 2


class DiffDialog:
    _current_mode = DiffMode.SIMPLE  # Class global to remember choice to next time it opens.

    def __init__(self, parent: Optional[QWidget], item: doorstop.Item, doorstop_data: DoorstopData) -> None:
        self.dialog = _DiffDialog(parent)
        self._item = item
        self._doorstop_data = doorstop_data
        self._current_history_index = 0

        self._differ: Optional[Differ] = None

        self._mode_buttons = {
            DiffMode.SIMPLE: self.dialog.ui.simple_mode_button,
            DiffMode.GIT: self.dialog.ui.git_mode_button,
        }

        for m, button in self._mode_buttons.items():
            button.clicked.connect(functools.partial(self._on_mode_button_clicked, mode_ctrl=m))

        self.dialog.ui.vcs_backward_button.clicked.connect(self._on_backward_clicked)
        self.dialog.ui.vcs_forward_button.clicked.connect(self._on_forward_clicked)

        self._on_mode_button_clicked(DiffDialog._current_mode)
        self._update_current_mode(DiffDialog._current_mode, force=True)
        self._update_view()

    def _on_mode_button_clicked(self, mode_ctrl: DiffMode) -> None:
        for m, button in self._mode_buttons.items():
            if m != mode_ctrl and button.isChecked():
                button.setChecked(False)  # Uncheck others
            elif m == mode_ctrl and not button.isChecked():
                button.setChecked(True)  # Re-check it.

        self._update_current_mode(mode_ctrl)

    def _on_backward_clicked(self) -> None:
        assert self._differ is not None
        assert self._differ.support_history()

        if self._current_history_index < self._differ.get_history_len() - 1:
            self._current_history_index += 1

        self._update_view()

    def _on_forward_clicked(self) -> None:
        assert self._differ is not None
        assert self._differ.support_history()

        if self._current_history_index > 0:
            self._current_history_index -= 1

        self._update_view()

    def _update_current_mode(self, new_mode: DiffMode, force: bool = False) -> None:
        if not force and DiffDialog._current_mode == new_mode:
            return

        if new_mode == DiffMode.SIMPLE:
            self._differ = SimpleDiffer(self._doorstop_data.get_original_data(self._item), Path(self._item.path))
        else:
            self._differ = GitDiffer(Path(self._item.path))

        DiffDialog._current_mode = new_mode
        self._update_view()

    def _update_view(self) -> None:
        assert self._differ is not None

        self.dialog.resize(800, 800)
        description = ""
        if self._differ.__doc__:
            description = "\n".join([line.strip() for line in self._differ.__doc__.splitlines()])
        self.dialog.ui.description.setText(description)
        if self._differ.support_history():
            self.dialog.ui.vcs_frame.show()
            self.dialog.ui.vcs_current_diff_label.setText(self._differ.get_history_name(self._current_history_index))
            metadata = self._differ.get_history_metadata(self._current_history_index)
            self.dialog.ui.vcs_author.setText(metadata.author)
            self.dialog.ui.vcs_date.setText(metadata.timestamp.isoformat(" ", "seconds"))

            if self._current_history_index == 0:
                self.dialog.ui.vcs_forward_button.setDisabled(True)
            else:
                self.dialog.ui.vcs_forward_button.setDisabled(False)

            if self._current_history_index == self._differ.get_history_len() - 1:
                self.dialog.ui.vcs_backward_button.setDisabled(True)
            else:
                self.dialog.ui.vcs_backward_button.setDisabled(False)
        else:
            self.dialog.ui.vcs_frame.hide()

        raw_diff = self._differ.get_diff(self._current_history_index)

        if len(raw_diff) == 0:
            html = "<h1>NO CHANGES</h1>"
        else:
            diff_lexer = DiffLexer()
            formatter = HtmlFormatter(full=True, style=GhDarkStyle, noclasses=True)
            html = pygments.highlight(code=raw_diff, lexer=diff_lexer, formatter=formatter)

        self.dialog.ui.diff_dialog_text.setHtml(html)

    def _run(self) -> None:
        self.dialog.exec()

    @classmethod
    def show(cls, parent: QWidget, item: doorstop.Item, doorstop_data: DoorstopData) -> "DiffDialog":
        instance = cls(parent, item, doorstop_data)
        instance._run()
        return instance
