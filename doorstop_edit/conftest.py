# This file conains all shared test fixtures in the project.

import tempfile
from pathlib import Path
from typing import Any, Iterator

import pytest

from doorstop_edit.doorstop_data import DoorstopData
from tools.gen_sample_tree import generate_tree

NUM_DOC = 3
NUM_ITEMS_PER_DOC = 30


@pytest.fixture(scope="session")
def tree_root() -> Iterator[Path]:
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        generate_tree(root, NUM_DOC, NUM_ITEMS_PER_DOC)
        yield root


@pytest.fixture()
def doorstop_data(tree_root: Path) -> DoorstopData:
    dd = DoorstopData(None, tree_root)
    dd.rebuild(False)
    return dd


class QSettingsMock:
    def __init__(self) -> None:
        pass

    def value(self, name: Any, default_val: Any, type: Any) -> Any:
        return default_val

    def beginGroup(self, val: str) -> None:
        pass

    def endGroup(self) -> None:
        pass

    def setValue(self, name: Any, value: Any) -> None:
        pass

    def remove(self, name: Any) -> None:
        pass


@pytest.fixture(autouse=True)
def noop_qsettings(monkeypatch: pytest.MonkeyPatch) -> Any:
    """Automatcially replace QSettings with QSettingsMock in all tests to avoid writing settings to
    disk during tests."""

    def get_settings() -> Any:
        return QSettingsMock()

    monkeypatch.setattr("doorstop_edit.settings.get_settings", get_settings)
