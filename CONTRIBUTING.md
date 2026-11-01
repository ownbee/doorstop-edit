# Contributing

Contributing to this project is very welcome. Below you find a short introduction of how to develop
in this project.


## Getting started


This project uses uv to manage Python and dependencies. Install uv using its
[official installation instructions](https://docs.astral.sh/uv/getting-started/installation/).

```sh
uv python install 3.14
```

Install project:

```sh
uv sync
```

Supported Python versions are 3.11–3.14. PySide6 6.12 requires macOS 14 or later;
on Linux it requires glibc 2.34+ on x86-64 or 2.39+ on ARM64.

Generate necessary python code (resources and build info):

 ```sh
uv run python build.py
```

## Editing UI

PySide6 comes with the tool `pyside6-designer` which is used to edit the graphical parts of the UI.
All the UI components (`*.ui`) are located in the `ui/` folder which can be opened and edited with
the tool.

When running `build.py` (described in the section above) or simply
`uv run python tools/gen_ui.py`, Python code is generated from the `.ui` files.


## Testing

Tests are written with `pytest` with `pytest-qt` plugin. Tests are placed in the source structure in
folders called `test`.

```sh
uv run pytest
```

## Static code analysis and style check

There is a script at `tools/check_code.py` that runs Ruff and mypy and shall be
run without errors. Run `uv run python tools/check_code.py` from the repository
root; pass `--fix` to apply Ruff lint and formatting fixes.

Ruff handles formatting, imports, and lint checks; mypy remains the type
checker. An alternative type checker has not yet been shown to preserve the
current mypy strictness and handling of PySide6 and generated UI modules.
