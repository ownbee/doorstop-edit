import os
from typing import Optional

from PySide6.QtGui import QColor


class Theme:

    PRIMARY_COLOR = QColor(0)
    PRIMARY_LIGHT_COLOR = QColor(0)
    SECONDARY_COLOR = QColor(0)
    SECONDARY_LIGHT_COLOR = QColor(0)
    SECONDARY_DARK_COLOR = QColor(0)
    PRIMARY_TEXT_COLOR = QColor(0)
    SECONDARY_TEXT_COLOR = QColor(0)
    SUCCESS_COLOR = QColor(0)
    WARNING_COLOR = QColor(0)
    DANGER_COLOR = QColor(0)
    DISABLE_COLOR = QColor(0)
    NON_IMPROTANT_COLOR = QColor(0)


def _to_color(val: Optional[str]) -> QColor:
    if val is None:
        raise RuntimeError("Color is None")
    if val.startswith("#"):
        return QColor(int(val[1:], base=16))
    raise RuntimeError(f"Unsupported color value {val}")


def setup_colors(stylesheet_extra: dict) -> None:

    Theme.PRIMARY_COLOR = _to_color(os.environ.get("QTMATERIAL_PRIMARYCOLOR"))
    Theme.PRIMARY_LIGHT_COLOR = _to_color(os.environ.get("QTMATERIAL_PRIMARYLIGHTCOLOR"))
    Theme.SECONDARY_COLOR = _to_color(os.environ.get("QTMATERIAL_SECONDARYCOLOR"))
    Theme.SECONDARY_LIGHT_COLOR = _to_color(os.environ.get("QTMATERIAL_SECONDARYLIGHTCOLOR"))
    Theme.SECONDARY_DARK_COLOR = _to_color(os.environ.get("QTMATERIAL_SECONDARYDARKCOLOR"))
    Theme.PRIMARY_TEXT_COLOR = _to_color(os.environ.get("QTMATERIAL_PRIMARYTEXTCOLOR"))
    Theme.SECONDARY_TEXT_COLOR = _to_color(os.environ.get("QTMATERIAL_SECONDARYTEXTCOLOR"))
    Theme.SUCCESS_COLOR = _to_color(stylesheet_extra["success"])
    Theme.WARNING_COLOR = _to_color(stylesheet_extra["warning"])
    Theme.DANGER_COLOR = _to_color(stylesheet_extra["danger"])
    Theme.DISABLE_COLOR = _to_color("#6b6b6b")
    Theme.NON_IMPROTANT_COLOR = _to_color("#58bafc")
