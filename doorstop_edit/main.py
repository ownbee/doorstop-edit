import argparse
import logging
import os
import sys
from pathlib import Path
from typing import List, Optional

import doorstop
from doorstop import settings as doorstop_settings
from PySide6.QtCore import QLoggingCategory
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


def setup(app: QApplication, argv: List[str]) -> Optional[DoorstopEdit]:
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", action="store_true", help="turn on verbose logging")
    parser.add_argument("--version", action="store_true", help="turn on verbose logging")
    parser.add_argument("--font-size", default=13, type=int, help="set custom font-size")
    parser.add_argument("--density", default=-1, type=int, help="set density scale (make thing smaller or bigger)")
    args = parser.parse_args(argv[1:])

    if args.version:
        print(create_version_summary())
        return None

    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s [%(name)s] %(message)s",
        datefmt="%H:%M:%S",
    )
    logger.setLevel(logging.DEBUG if args.verbose else logging.INFO)

    # Setup custom theme
    extra = {
        # Button colors
        "danger": "#dc3545",
        "warning": "#ffc107",
        "success": "#17a2b8",
        # Font
        "font_family": "Roboto",
        "font_size": args.font_size,
        "line_height": args.font_size,
        # Density Scale
        "density_scale": args.density,
    }
    # qdarktheme.setup_theme()
    apply_stylesheet(app, theme="dark_teal.xml", extra=extra)
    stylesheet = app.styleSheet()
    with open(Path(__file__).parent / "custom.css", "r", encoding="utf-8") as file:
        app.setStyleSheet(stylesheet + file.read().format(**os.environ))

    setup_colors(extra)

    # Add custom font
    QFontDatabase.addApplicationFont(":/font/DroidSansMono.ttf")

    # Disable info logs from WebEngine
    web_engine_context_log = QLoggingCategory("qt.webenginecontext")  # type: ignore
    web_engine_context_log.setFilterRules("*.info=false")

    return DoorstopEdit(app)


def main() -> int:
    # As minimalistic as possible since it wont be tested.
    app = QApplication([])

    editor = setup(app, sys.argv)
    if editor is not None:
        editor.show()
        return app.exec()

    return 0
