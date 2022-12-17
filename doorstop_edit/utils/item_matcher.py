import re
from typing import List, Union

import doorstop
from doorstop.core.types import Level as doorstop_Level


def match_item(item: doorstop.Item, search: List[str]) -> bool:
    result: List[bool] = []
    for term in search:
        pattern = re.compile(re.escape(term), re.IGNORECASE)
        found = False
        if item.header is not None and pattern.search(item.header):
            found = True
        elif pattern.search(str(item.uid)):
            found = True
        elif pattern.search(item.text):
            found = True
        elif pattern.search(str(item.level)):
            found = True
        result.append(found)
    return all(result)


def match_level(item: doorstop.Item, level: Union[str, doorstop_Level], include_parent=False) -> bool:
    """Returns True if `item` is on the same level as `level`."""

    def level_to_parts(_level: str) -> List[int]:
        parts = [int(part) for part in str(_level).split(".")]
        if parts[-1] == 0:
            parts = parts[:-1]
        return parts

    if isinstance(level, doorstop_Level):
        level = str(level)

    item_level_parts = level_to_parts(item.level)
    level_parts = level_to_parts(level)
    if include_parent:
        if len(item_level_parts) == len(level_parts) - 1 and item_level_parts == level_parts[:-1]:
            return True

    if len(item_level_parts) != len(level_parts):
        return False

    if item_level_parts == level_parts:
        return True

    if len(level_parts) > 0 and item_level_parts[:-1] == level_parts[:-1]:
        return True

    return False
