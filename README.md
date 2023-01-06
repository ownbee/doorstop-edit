[![PyPI Version](https://img.shields.io/pypi/v/doorstop-edit.svg)](https://pypi.org/project/doorstop-edit)
[![Linux Test](https://github.com/ownbee/doorstop-edit/actions/workflows/test.yml/badge.svg)](https://github.com/ownbee/doorstop-edit/actions/workflows/test.yml)
[![Coverage Status](https://img.shields.io/codecov/c/gh/ownbee/doorstop-edit)](https://codecov.io/gh/ownbee/doorstop-edit)

# Doorstop Edit

_A cross-platform GUI editor for [Doorstop](https://github.com/doorstop-dev/doorstop) powered by PySide6 (Qt)._

The goal of this GUI is to provide all the tools needed to efficiently work with a larger set of
requirements within the editor and at the same time have full control of what is happening. The
editor use the doorstop API whenever possible to behave the same way as doorstop.

![Sample](https://raw.githubusercontent.com/ownbee/doorstop-edit/main/sample.png)

**Features:**

* **Resizable and movable modern views** for custom layout.
* **Dark theme**.
* Item tree with **status colors** and **search function** for good overview and fast location.
* **Live markdown-HTML** rendering.
* **Section or single mode** reading.
* **Review** and **clear suspect links**.
* Edit additional attributes with `boolean` and `string` types.
* Built-in **item diff tool** to review changes made on disk.
* **Markdown formatting tool** powered by `mdformat` for the text attribute.
* **Pin feature** for easy access to work-in-progress items.
* And more...


**TODO list:**

* Add and remove document.
* Validating documents and items in a user-friendly manner.
* File watcher for syncing/refreshing when changes made on disk.
* Ability to change project root.

## Install

Automatic install with pip:

```sh
pip install doorstop-edit
```

For source installation see *Contributing* section.

## Demo/Testing

There is a python script that generates a document tree which can be useful when testing this
application.

```sh
python3 tools/gen_sample_tree.py

# Output will be located in the dist/ folder.
```


## Other doorstop GUI's

There exists at least two well known GUI's for doorstop editing,
[doorhole](https://github.com/sevendays/doorhole) and the build-in GUI in doorstop.

Since both are pretty basic and have missing features when working with a large and complex set of
requrements, this new GUI was created to fill in some gaps.


## Contributing

See [CONTRIBUTING.md](https://github.com/ownbee/doorstop-edit/blob/main/CONTRIBUTING.md).
