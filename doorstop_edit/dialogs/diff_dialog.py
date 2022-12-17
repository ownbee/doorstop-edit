import difflib

import doorstop
import pygments
from pygments.formatters import HtmlFormatter
from pygments.lexers.diff import DiffLexer
from pygments.styles.gh_dark import GhDarkStyle
from PySide6.QtWidgets import QDialog

from doorstop_edit.doorstop_data import DoorstopData
from doorstop_edit.ui_gen.ui_diff_dialog import Ui_diff_dialog


class _DiffDialog(QDialog):
    def __init__(self) -> None:
        super().__init__()
        self.ui = Ui_diff_dialog()
        self.ui.setupUi(self)


class DiffDialog:
    def __init__(self, doorstop_data: DoorstopData) -> None:
        self._dialog = _DiffDialog()
        self._doorstop_data = doorstop_data

    def show(self, item: doorstop.Item):
        raw_diff = ""
        old_item_data = self._doorstop_data.get_original_data(item)
        if old_item_data is not None:
            new_item_data = item._dump(item._yaml_data())
            diffs = difflib.unified_diff(
                old_item_data.splitlines(True),
                new_item_data.splitlines(True),
                fromfile="ORIGINAL",
                tofile="CHANGED",
                n=100,
            )
            raw_diff = "".join(diffs)
        # try:
        #     raw_diff = subprocess.check_output(["git", "diff", "-U100", item.path])
        # except subprocess.CalledProcessError as e:
        #     print(e)
        #     return

        if len(raw_diff) == 0:
            html = "<h1>NO CHANGES</h1>"
        else:
            diff_lexer = DiffLexer()
            formatter = HtmlFormatter(full=True, style=GhDarkStyle, noclasses=True)
            html = pygments.highlight(code=raw_diff, lexer=diff_lexer, formatter=formatter)

        self._dialog.ui.diff_dialog_text.setHtml(html)
        self._dialog.exec()
