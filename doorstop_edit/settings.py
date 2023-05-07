import logging
from typing import Any

from PySide6.QtCore import QSettings

logger = logging.getLogger("settings")


def get_settings() -> QSettings:
    """Get a application QSettings instance.

    `PersistentSetting` should be used instead when possible.
    """
    return QSettings(
        QSettings.Format.NativeFormat,
        QSettings.Scope.UserScope,
        "doorstop-edit",
        "doorstop-edit",
    )


class PersistentSetting(object):
    """Abstract class helper for easy persistent settings.

    Inherited class attributes will become persistent settings that are automatically saved when
    modified. The set attribute value set type and default value.

    `IN_GROUP` is a special attribute which sets the setting group which all class attributes will
    be saved to.

    An attribute is only save to disk when modified, untouched default attributes will not be save
    to disk.

    Example:

        ```python
        class ThemeSettings(PersistentSetting):
            IN_GROUP = "Theme"
            name = "Default"
            accent = "#121212"
            text_size = 14
        ```
    """

    IN_GROUP = "General"  # Setting group, should be overridden.

    def __init__(self) -> None:
        self.settings = get_settings()

    def __setattr__(self, name: str, value: Any) -> None:
        if name in ["settings", "IN_GROUP"]:
            super().__setattr__(name, value)
            return
        self.settings.beginGroup(self.IN_GROUP)
        if super().__getattribute__(name) == value:
            # If default value is set, remove from disk. This makes users follow changed default
            # behaviours better.
            self.settings.remove(name)
        else:
            self.settings.setValue(name, value)

        self.settings.endGroup()

    def __getattribute__(self, name: str) -> Any:
        default = super().__getattribute__(name)
        if name in ["settings", "IN_GROUP"]:
            return default
        self.settings.beginGroup(self.IN_GROUP)
        val = self.settings.value(name, default, type(default))
        self.settings.endGroup()
        if not isinstance(val, type(default)):
            logger.warning(
                "Inconsistent setting '%s', disk has type '%s', expected type %s", name, type(val), type(default)
            )
            return default
        return val
