import mdformat
from mdformat.plugins import PARSER_EXTENSIONS

from doorstop_edit.item_edit.mdformat import plugin

PLUGIN_NAME = "doorstop-edit-fix"

# Add this plugin to mdformat
PARSER_EXTENSIONS[PLUGIN_NAME] = plugin  # type: ignore


def format(text: str) -> str:
    return mdformat.text(
        text,
        options={
            "number": True,  # switch on consecutive numbering of ordered lists
            "wrap": 80,
        },
        extensions=["myst", PLUGIN_NAME],
    )
