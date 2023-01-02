# Contributing

Contributing to this project is very welcome. Below you find a short introduction of how to develop
in this project.


## Getting started


This project is using poetry as build tool. Example of how to set it up:

```sh
# If Linux:
python3 -m venv .venv && source .venv/bin/activate

# If Windows (Git bash):
py -3 -m venv .venv && source .venv/Scripts/activate

# Then:
pip install poetry
```

Install project:

```sh
poetry install
```

## Editing UI

PySide6 comes with the tool `pyside6-designer` which is used to edit the graphical parts of the UI.
All the UI components (`*.ui`) are located in the `ui/` folder which can be opened and edited with
the tool.

When ruinning `poetry install` Python code is generated from the `.ui` files.


## Testing

Tests are written with `unittest` framework and run with `pytest`. Tests are placed in the source
structure in folders called `test`.

```sh
poetry run pytest
```

## Static code analysis and style check

There is a script at `tools/check_code.py` that shall be run without errors.
