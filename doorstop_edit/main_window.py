import os
import re
from pathlib import Path

from PySide6.QtCore import QByteArray
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QMainWindow
from qt_material import QtStyleTools

from doorstop_edit.settings import PersistentSetting
from doorstop_edit.theme import setup_colors
from doorstop_edit.ui_gen.ui_main import Ui_MainWindow


class MainWindow(QMainWindow, QtStyleTools):
    class Settings(PersistentSetting):
        IN_GROUP = "MainWindow"
        geometry = QByteArray()
        state = QByteArray()

    class ThemeSettings(PersistentSetting):
        IN_GROUP = "Theme"
        font_size = 12
        density_scale = -1

    def __init__(self) -> None:
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.theme_settings = self.ThemeSettings()
        self.update_theme()
        self._restore_window_state()

    def closeEvent(self, event: QCloseEvent) -> None:
        self._store_window_state()
        super().closeEvent(event)

    def _store_window_state(self) -> None:
        settings = self.Settings()
        settings.geometry = self.saveGeometry()
        settings.state = self.saveState()

    def _restore_window_state(self) -> None:
        settings = self.Settings()

        if not settings.geometry.isEmpty():
            self.restoreGeometry(settings.geometry)
        if not settings.state.isEmpty():
            self.restoreState(settings.state)

        for dock in [
            self.ui.edit_item_dock_widget,
            self.ui.item_tree_dock_widget,
            self.ui.pinned_items_dock_widget,
        ]:
            self.restoreDockWidget(dock)

    def _load_custom_css(self) -> str:
        with open(Path(__file__).parent / "custom.css", "r", encoding="utf-8") as file:
            custom_css = file.read()

        result = re.findall("__(.*)__", custom_css)
        for replace_val in result:
            if replace_val in os.environ:
                custom_css = custom_css.replace("__" + replace_val + "__", os.environ[replace_val])
            else:
                raise RuntimeError(f"Failed to expand {replace_val} in css")

        return custom_css

    def update_theme(self) -> None:
        # Setup custom theme
        extra = {
            # Button colors
            "danger": "#dc3545",
            "warning": "#ffc107",
            "success": "#17a2b8",
            # Font
            "font_family": "Roboto",
            "font_size": self.theme_settings.font_size,
            "line_height": self.theme_settings.font_size,
            # Density Scale
            "density_scale": self.theme_settings.density_scale,
        }
        self.apply_stylesheet(self, theme="dark_teal.xml", extra=extra)
        self.setStyleSheet(self.styleSheet() + self._load_custom_css())
        setup_colors(extra)
