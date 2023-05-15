import argparse
import logging
import sys
from pathlib import Path
from typing import List, Optional

import doorstop
from doorstop import settings as doorstop_settings
from PySide6.QtCore import QLoggingCategory, QSize
from PySide6.QtGui import QFontDatabase, QIcon, Qt
from PySide6.QtWidgets import QApplication, QSplashScreen

from doorstop_edit.application import DoorstopEdit
from doorstop_edit.utils.version_summary import create_version_summary

logger = logging.getLogger("gui")

# Do not use version control system since it will slow down the UI by calling git/svn etc. on
# every item save.
doorstop_settings.ADDREMOVE_FILES = False
doorstop.Item.auto = False  # Disable automatic save.


def show_splash_screen(app: QApplication) -> QSplashScreen:
    pixmap = QIcon(":/icons/favicon").pixmap(QSize(400, 400))
    splash = QSplashScreen(pixmap)
    splash.show()
    app.processEvents()
    return splash


def update_splash_msg(ss: QSplashScreen, text: str) -> None:
    ss.showMessage(text, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom, Qt.GlobalColor.white)


def setup(app: QApplication, argv: List[str]) -> Optional[DoorstopEdit]:
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", action="store_true", help="turn on verbose logging")
    parser.add_argument("--version", action="store_true", help="turn on verbose logging")
    parser.add_argument("directory", default="", nargs="?", help="Doorstop root directory")
    args = parser.parse_args(argv[1:])

    if args.version:
        print(create_version_summary())
        return None

    logging.basicConfig(
        level=logging.ERROR,  # Mostly to avoid doorstop spamming irrelevant warnings and info.
        format="%(asctime)s [%(name)s] %(message)s",
        datefmt="%H:%M:%S",
    )
    logger.setLevel(logging.DEBUG if args.verbose else logging.INFO)

    if len(args.directory) > 0:
        root_directory = Path(args.directory)
    else:
        root_directory = None

    if root_directory and not root_directory.is_dir():
        logger.error("Invalid argument: '%s' is not a directory.", root_directory)
        return None

    # Add custom font
    QFontDatabase.addApplicationFont(":/font/DroidSansMono.ttf")

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
    update_splash_msg(splash, "Loading UI...")
    editor = setup(app, sys.argv)
    if editor is not None:
        app.aboutToQuit.connect(editor.quit)
        update_splash_msg(splash, "Starting UI ...")
        editor.start()
        splash.finish(editor.window)
        return app.exec()

    return 0
