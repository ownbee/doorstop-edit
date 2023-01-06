from typing import Dict, List

import doorstop

from doorstop_edit.utils.debug_timer import time_function


class DocumentItemLevelTree:
    def __init__(self) -> None:
        self.content: Dict[int, "DocumentItemLevelTree"] = {}
        self.items: List[doorstop.Item] = []

    def sort(self) -> None:
        self.content = dict(sorted(self.content.items()))
        for child in self.content.values():
            child.sort()

    def __str__(self) -> str:
        return self._to_str(0)

    def _to_str(self, indent: int) -> str:
        text = ""
        for item in self.items:
            text += "> " + (". " * indent) + str(item.level).strip() + "\n"
        for _, child in self.content.items():
            text += child._to_str(indent + 1)
        return text


@time_function("Building item level tree")
def build_item_level_tree(document: doorstop.Document) -> DocumentItemLevelTree:
    """Build a level tree for all items in a document."""

    def parse_level(item: doorstop.Item) -> List[int]:
        level_parts = str(item.level).split(".")

        if len(level_parts) == 0:
            return []
        # 1 and 1.0 is the same thing in doorstop, .0 in 1.0 only means header.
        # Therefore, remove any trailing zeros when creating tree.
        if int(level_parts[-1]) == 0:
            level_parts = level_parts[:-1]
        return [int(p) for p in level_parts]

    root = DocumentItemLevelTree()
    for item in document:
        ptr = root
        for level_part in parse_level(item):
            if level_part not in ptr.content:
                ptr.content[level_part] = DocumentItemLevelTree()
            ptr = ptr.content[level_part]
        ptr.items.append(item)

    root.sort()

    return root
