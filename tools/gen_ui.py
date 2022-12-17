#!/usr/bin/env python3

import os
import subprocess
from pathlib import Path

UI_FILES_DIR = Path("ui")


def gen_ui_files():
    if not UI_FILES_DIR.is_dir():
        raise RuntimeError("Please stand in repository root when running this script.")
    print("Generating UI files...")
    for p in os.listdir(UI_FILES_DIR):
        path = Path(p)
        root = Path("doorstop_edit") / "ui_gen"
        root.mkdir(exist_ok=True)
        (root / "__init__.py").touch()
        if path.suffix == ".ui":
            py_file = (root / ("ui_" + path.stem)).with_suffix(".py")
            print(f"{path.name:<20} -> {py_file}")
            subprocess.check_call(
                [
                    "pyside6-uic",
                    UI_FILES_DIR / path,
                    "--from-imports",
                    "-o",
                    py_file.as_posix(),
                ]
            )

        if path.suffix == ".qrc":
            py_file = (root / (path.stem + "_rc")).with_suffix(".py")
            print(f"{path.name:<20} -> {py_file}")
            subprocess.check_call(["pyside6-rcc", UI_FILES_DIR / path, "-o", py_file.as_posix()])


if __name__ == "__main__":
    gen_ui_files()
