import argparse
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any, List, Optional

import doorstop
from doorstop import settings as doorstop_settings
from PySide6.QtCore import QLoggingCategory, QSize
from PySide6.QtGui import QFontDatabase, QIcon, Qt
from PySide6.QtWidgets import QApplication, QSplashScreen
from qt_material import apply_stylesheet

from doorstop_edit.application import DoorstopEdit
from doorstop_edit.theme import setup_colors
from doorstop_edit.utils.version_summary import create_version_summary

logger = logging.getLogger("gui")

# Do not use version control system since it will slow down the UI by calling git/svn etc. on
# every item save.
doorstop_settings.ADDREMOVE_FILES = False
doorstop.Item.auto = False  # Disable automatic save.


def show_splash_screen(app: QApplication) -> QSplashScreen:
    pixmap = QIcon(":/icons/favicon").pixmap(QSize(400, 400))
    splash = QSplashScreen(pixmap)
    splash.showMessage(
        "Loading doorstop tree...", Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom, Qt.GlobalColor.white
    )
    splash.show()
    app.processEvents()
    return splash


def load_custom_css() -> str:
    with open(Path(__file__).parent / "custom.css", "r", encoding="utf-8") as file:
        custom_css = file.read()

    result = re.findall("__(.*)__", custom_css)
    for replace_val in result:
        if replace_val in os.environ:
            custom_css = custom_css.replace("__" + replace_val + "__", os.environ[replace_val])
        else:
            raise RuntimeError(f"Failed to expand {replace_val} in css")

    return custom_css


def setup_style(app: QApplication, args: Any) -> None:
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
    apply_stylesheet(app, theme="dark_teal.xml", extra=extra)
    app.setStyleSheet(app.styleSheet() + load_custom_css())
    setup_colors(extra)


def setup(app: QApplication, argv: List[str]) -> Optional[DoorstopEdit]:
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", action="store_true", help="turn on verbose logging")
    parser.add_argument("--version", action="store_true", help="turn on verbose logging")
    parser.add_argument("--font-size", default=13, type=int, help="set custom font-size")
    parser.add_argument("--density", default=-1, type=int, help="set density scale (make thing smaller or bigger)")
    parser.add_argument("directory", default=".", nargs="?", help="Doorstop root directory")
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

    root_directory = Path(args.directory)
    if not root_directory.is_dir():
        logger.error("Invalid argument: '%s' is not a directory.", root_directory)
        return None

    # Add custom font
    QFontDatabase.addApplicationFont(":/font/DroidSansMono.ttf")

    setup_style(app, args)

    # Disable info logs from WebEngine
    web_engine_context_log = QLoggingCategory("qt.webenginecontext")  # type: ignore
    web_engine_context_log.setFilterRules("*.info=false")

    app.processEvents()  # Make sure splash screen shows.

    editor = DoorstopEdit(root_directory)
    return editor


def main() -> int:
    # As minimalistic as possible since it wont be tested.
    app = QApplication([])
    splash = show_splash_screen(app)
    editor = setup(app, sys.argv)
    app.aboutToQuit.connect(editor.quit)  # type: ignore
    if editor is not None:
        editor.show()
        splash.finish(editor.window)
        return app.exec()

    return 0
