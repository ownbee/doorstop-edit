from typing import Callable, Generic, List, TypeVar

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QFrame,
    QLabel,
    QLayout,
    QSizePolicy,
    QSpinBox,
    QWidget,
)
from spellchecker import SpellChecker

from doorstop_edit.main_window import MainWindow
from doorstop_edit.utils.spell_checker import TextEditSpellChecker

T = TypeVar("T")


class _Entry(Generic[T]):
    def __init__(self, label: str, val: T, on_change: Callable[[T], None]) -> None:
        self.label = label
        self.value = val
        self.on_change = on_change

    def add_to_row(self, layout: QFormLayout, row: int) -> None:
        label = QLabel()
        label.setText(self.label)
        label.setMinimumWidth(100)
        layout.setWidget(row, QFormLayout.ItemRole.LabelRole, label)


class _IntEntry(_Entry[int]):
    def __init__(self, label: str, val: int, on_change: Callable[[int], None], min: int, max: int) -> None:
        super().__init__(label, val, on_change)
        self.min = min
        self.max = max

    def add_to_row(self, layout: QFormLayout, row: int) -> None:
        super().add_to_row(layout, row)
        widget = QSpinBox()
        widget.setMinimum(self.min)
        widget.setMaximum(self.max)
        widget.setValue(self.value)
        widget.valueChanged.connect(self.on_change)
        layout.setWidget(row, QFormLayout.ItemRole.FieldRole, widget)


class _EnumEntry(_Entry[str]):
    def __init__(self, label: str, val: str, on_change: Callable[[str], None], choices: List[str]) -> None:
        super().__init__(label, val, on_change)
        self.choices = choices

    def add_to_row(self, layout: QFormLayout, row: int) -> None:
        super().add_to_row(layout, row)
        widget = QComboBox()
        widget.setMinimumWidth(100)
        widget.addItems(self.choices)
        current_index = 0
        for i, choice in enumerate(self.choices):
            if choice == self.value:
                current_index = i
        widget.setCurrentIndex(current_index)
        widget.currentIndexChanged.connect(self._on_index_change)
        layout.setWidget(row, QFormLayout.ItemRole.FieldRole, widget)

    def _on_index_change(self, index: int) -> None:
        self.on_change(self.choices[index])


class _BoolEntry(_Entry[bool]):
    def __init__(self, label: str, val: bool, on_change: Callable[[bool], None]) -> None:
        super().__init__(label, val, on_change)

    def add_to_row(self, layout: QFormLayout, row: int) -> None:
        super().add_to_row(layout, row)
        widget = QCheckBox()
        widget.setChecked(self.value)
        widget.stateChanged.connect(self._on_state_change)
        layout.setWidget(row, QFormLayout.ItemRole.FieldRole, widget)

    def _on_state_change(self, state: int) -> None:
        self.on_change(state != 0)


class _HLineEntry(_Entry[int]):
    def __init__(self) -> None:
        super().__init__("", 0, lambda x: None)

    def add_to_row(self, layout: QFormLayout, row: int) -> None:
        line = QFrame()
        sp = QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        sp.setHorizontalStretch(0)
        sp.setVerticalStretch(0)
        sp.setHeightForWidth(line.sizePolicy().hasHeightForWidth())
        line.setSizePolicy(sp)
        line.setLineWidth(5)
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        layout.setWidget(row, QFormLayout.ItemRole.SpanningRole, line)


class _TitleEntry(_Entry[int]):
    def __init__(self, label: str) -> None:
        super().__init__(label, 0, lambda x: None)

    def add_to_row(self, layout: QFormLayout, row: int) -> None:
        label = QLabel()
        label.setText(self.label)
        font = label.font()
        font.setBold(True)
        label.setFont(font)
        layout.setWidget(row, QFormLayout.ItemRole.LabelRole, label)


class _SettingDialog(QDialog):
    def __init__(self, parent: QWidget, entries: List[_Entry]) -> None:
        super().__init__(parent)
        self._setup(entries)

    def _setup(self, entries: List[_Entry]) -> None:
        self.setWindowTitle("Settings")
        self.setFixedWidth(400)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.MinimumExpanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.sizePolicy().hasHeightForWidth())
        self.setSizePolicy(sizePolicy)
        self.form_layout = QFormLayout(self)
        self.form_layout.setSizeConstraint(QLayout.SizeConstraint.SetDefaultConstraint)
        self.form_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        self.form_layout.setRowWrapPolicy(QFormLayout.RowWrapPolicy.DontWrapRows)
        self.form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.form_layout.setHorizontalSpacing(6)
        self.form_layout.setVerticalSpacing(2)
        self.form_layout.setContentsMargins(12, 12, 12, 12)
        for i, e in enumerate(entries):
            e.add_to_row(self.form_layout, i)


class SettingDialog(QObject):
    on_theme_changed = Signal()

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.theme_setting = MainWindow.ThemeSettings()
        self.spell_settings = TextEditSpellChecker.Settings()

    def open(self) -> None:
        parent = self.parent()
        assert isinstance(parent, QWidget)
        entries: List[_Entry] = [
            _TitleEntry("Theme"),
            _HLineEntry(),
            _IntEntry("Font Size", self.theme_setting.font_size, min=6, max=20, on_change=self._update_font_size),
            _IntEntry(
                "Desity Scale",
                self.theme_setting.density_scale,
                min=-10,
                max=10,
                on_change=self._update_density_scale,
            ),
            _TitleEntry("Edit"),
            _HLineEntry(),
            _BoolEntry("Spellchecker Enable", self.spell_settings.enabled, self._update_spell_enable),
            _EnumEntry(
                "Spellchecker Lang",
                self.spell_settings.langugage,
                choices=list(SpellChecker.languages()),
                on_change=self._update_spell_language,
            ),
        ]
        dialog = _SettingDialog(parent, entries)
        dialog.exec()

    def _update_font_size(self, val: int) -> None:
        self.theme_setting.font_size = val
        self.on_theme_changed.emit()

    def _update_density_scale(self, val: int) -> None:
        self.theme_setting.density_scale = val
        self.on_theme_changed.emit()

    def _update_spell_enable(self, enabled: bool) -> None:
        self.spell_settings.enabled = enabled

    def _update_spell_language(self, val: str) -> None:
        self.spell_settings.langugage = val
