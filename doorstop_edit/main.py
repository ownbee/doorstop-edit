import argparse
import logging
import os
import sys
from pathlib import Path

import doorstop
from doorstop import settings as doorstop_settings
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication
from qt_material import apply_stylesheet

from doorstop_edit.application import DoorstopEdit
from doorstop_edit.theme import setup_colors
from doorstop_edit.utils.version_summary import create_version_summary

# import qdarktheme


logger = logging.getLogger("gui")

# Do not use version control system since it will slow down the UI by calling git/svn etc. on
# every item save.
doorstop_settings.ADDREMOVE_FILES = False
doorstop.Item.auto = False  # Disable automatic save.


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", action="store_true", help="Turn on verbose logging.")
    parser.add_argument("--version", action="store_true", help="Turn on verbose logging.")
    args = parser.parse_args()

    if args.version:
        print(create_version_summary())
        return 0

    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s - %(message)s",
        datefmt="%H:%M:%S",
    )
    logger.setLevel(logging.DEBUG if args.verbose else logging.INFO)

    app = QApplication(sys.argv)

    # Setup custom theme
    extra = {
        # Button colors
        "danger": "#dc3545",
        "warning": "#ffc107",
        "success": "#17a2b8",
        # Font
        "font_family": "Roboto",
    }
    # qdarktheme.setup_theme()
    apply_stylesheet(app, theme="dark_teal.xml", extra=extra)
    stylesheet = app.styleSheet()
    with open(Path(__file__).parent / "custom.css", "r", encoding="utf-8") as file:
        app.setStyleSheet(stylesheet + file.read().format(**os.environ))

    setup_colors(extra)

    # Add custom font
    QFontDatabase.addApplicationFont(":/font/DroidSansMono.ttf")

    editor = DoorstopEdit(app)
    editor.show()

    return app.exec()
