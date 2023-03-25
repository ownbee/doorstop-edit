# This file conains all shared test fixtures in the project.

import tempfile
from pathlib import Path
from typing import Iterator

import pytest

from doorstop_edit.doorstop_data import DoorstopData
from tools.gen_sample_tree import generate_tree

NUM_DOC = 3
NUM_ITEMS_PER_DOC = 30


@pytest.fixture()
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
