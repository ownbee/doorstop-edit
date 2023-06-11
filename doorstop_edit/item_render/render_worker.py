import logging
import re
import tempfile
from pathlib import Path
from typing import Callable, Dict, Generator, List, Optional, Tuple, Union

import doorstop
from PySide6.QtCore import (
    QMutex,
    QMutexLocker,
    QObject,
    QThread,
    QWaitCondition,
    Signal,
)

from doorstop_edit.item_render.fragmented_markdown import Element, FragmentedMarkdown
from doorstop_edit.utils import item_utils
from doorstop_edit.utils.debug_timer import time_function

logger = logging.getLogger("gui")

QUEUE_DATA_TYPE = 0
QUEUE_PROGRESS_TYPE = 1


class ProgressTracker:
    def __init__(self, total: int) -> None:
        self.total_count = total
        self.count = 0
        self.report_interval = max(int(self.total_count / 100), 1)

    def progress_one(self) -> bool:
        """Return True if enough to report"""
        if self.count <= self.total_count:
            self.count += 1
        return self.count % self.report_interval == 0

    def get(self) -> int:
        """Returns percetage to completion."""
        if self.total_count == 0:
            return 100
        return round(((self.count) / self.total_count) * 100)


class ItemRenderer:
    def __init__(self, progress_cb: Callable[[int], None]) -> None:
        self.progress_cb = progress_cb
        self.progress: Optional[ProgressTracker] = None
        self.md: Optional[FragmentedMarkdown] = None
        self.cache: Dict[str, int] = {}
        self.prev_refs: Dict[str, List[str]] = {}
        self.current_root = ""

    def process(
        self, root: str, partial: bool, items: List[Tuple[doorstop.Item, int]]
    ) -> Generator[Tuple[str, str], None, None]:
        try:
            if not self.md or root != self.current_root:
                self.md = FragmentedMarkdown(base_dir=root)

            if not partial:
                self._reset_state()

            self.progress = ProgressTracker(len(items) * 2)
            prepared_items: List[Optional[List[Tuple[str, Union[str, Element]]]]] = []
            for item, ts in items:
                if partial and item.uid.value in self.cache and self.cache[item.uid.value] == ts:
                    prepared_items.append(None)
                else:
                    rows, refs = self._prepare(self.md, item)
                    if item.uid.value in self.prev_refs and self.prev_refs[item.uid.value] != refs:
                        # References has changed, rerender all from start...
                        self.prev_refs = {}
                        self.cache = {}
                        self.md.reset()
                        yield from self.process(root=root, partial=False, items=items)
                        return
                    prepared_items.append(rows)
                    self.prev_refs[item.uid.value] = refs

                if self.progress.progress_one():
                    self.progress_cb(self.progress.get())

            self.md.process_fragments()

            for i, (item, ts) in enumerate(items):
                item_rows = prepared_items[i]
                if item_rows is not None:
                    content = self._render_item(self.md, item, item_rows)
                    yield (item.uid.value, content)
                    self.cache[item.uid.value] = ts
                if self.progress.progress_one():
                    self.progress_cb(self.progress.get())

            if not partial:
                yield ("footer", self.md.render_footer())

            self.progress.progress_one()
            self.progress_cb(self.progress.get())
        except Exception as e:
            logger.error("Failed to process markdown:", e)

    def _reset_state(self) -> None:
        self.prev_refs = {}
        self.cache = {}
        if self.md:
            self.md.reset()

    @staticmethod
    def _render_item(md: FragmentedMarkdown, item: doorstop.Item, attrs: List[Tuple[str, Union[str, Element]]]) -> str:
        if item_utils.is_header_item(item):
            levels = str(item.level).count(".")
            header_tag = f"h{levels}"
            header = ""
            text_lines = item.text.splitlines()
            if len(text_lines) > 0:
                header = text_lines[0]
        else:
            header_tag = "p"
            header = item.header

        html = f"<{header_tag}><b>{str(item.level)} {header}</b> <small>{item.uid.value}</small></{header_tag}>"

        html += '<table class="req-table">'
        for attr, val in attrs:
            if len(val) == 0:
                continue
            html += '<tr class="req-table">'
            colspan = 2
            if attr != "text":
                html += f'<th class="req-table">{attr.capitalize()}</th>'
                colspan = 1
            if not isinstance(val, str):
                val = md.render_fragment(val)
            html += f'<td colspan="{colspan}">{val}</td>'
            html += "</tr>"
        html += "</table>"

        return html

    @staticmethod
    def _prepare(
        md: FragmentedMarkdown, item: doorstop.Item
    ) -> Tuple[List[Tuple[str, Union[str, Element]]], List[str]]:
        refs = []

        def add_fragement_proxy(text: str) -> Optional[Element]:
            refs.extend(re.findall(r"^\s*\[(.*)\]:\s(.*)$", text, flags=re.MULTILINE))
            return md.add_fragement(text)

        rows: List[Tuple[str, Union[str, Element]]] = []
        if item_utils.is_header_item(item):
            item_text = "\n".join(item.text.splitlines()[1:])
        else:
            item_text = item.text
        rows.append(("text", add_fragement_proxy(item_text) or ""))
        if item.document and item.document.publish:
            for attr in item.document.publish:
                if attr in [row[0] for row in rows]:
                    continue
                val = item.attribute(attr)
                if val is None:
                    continue
                if isinstance(val, str) and len(val) > 0:
                    rows.append((attr, add_fragement_proxy(val) or ""))
                elif isinstance(val, bool):
                    rows.append((attr, str(val)))

        parent_links = []
        for link_item in item.parent_items:
            if not isinstance(link_item, doorstop.Item):
                continue
            parent_links.append(
                f'<a href="#" onclick="open_item(event, \'{link_item.uid.value}\')">'
                f"{link_item.uid.value} {link_item.header}</a>"
            )
        rows.append(("parents", ", ".join(parent_links)))

        child_links = []
        for link_item in item.find_child_items():
            if not isinstance(link_item, doorstop.Item):
                continue
            child_links.append(
                f'<a href="#" onclick="open_item(event, \'{link_item.uid.value}\')">'
                f"{link_item.uid.value} {link_item.header}</a>"
            )
        rows.append(("children", ", ".join(child_links)))

        return (rows, refs)


class RenderWorker(QThread):
    """Concurrent worker for generating HTML from markdown.

    Rendering can sometimes be a bit slow, especially if it contains plantUML.
    """

    result_ready = Signal(str, str, name="result_ready")
    progress = Signal(int, name="progress")

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)

        self.plantuml_cache = tempfile.gettempdir()

        self.mutex = QMutex()
        self.condition = QWaitCondition()
        self.abort = False
        self.change = 0
        self.restart = False

        self.items: List[Tuple[doorstop.Item, int]] = []
        self.root: Path = Path()

    def destroy(self) -> None:
        with QMutexLocker(self.mutex):
            self.abort = True
            self.condition.wakeOne()
        self.wait()

    @time_function("render")
    def render(self, items: List[Tuple[doorstop.Item, int]], root: Path, partial: bool) -> None:
        """Render HTML from doorstop items.

        Args:
            items: Items to render HTML from.
            root: File system path to document root. Needed to load images etc. correctly.
        """
        with QMutexLocker(self.mutex):
            self.items = items
            self.root = root
            self.partial = partial
            self.change += 1
            self.restart = True
            self.condition.wakeOne()

        if not self.isRunning():
            self.start(QThread.Priority.NormalPriority)

    def _on_progress(self, p: int) -> None:
        self.progress.emit(p)

    def run(self) -> None:
        item_renderer = ItemRenderer(self._on_progress)
        last_change = 0
        while True:
            with QMutexLocker(self.mutex) as qm:
                if self.abort:
                    return
                if self.change == last_change:
                    self.condition.wait(qm.mutex())
                self.restart = False
                last_change = self.change

                items = self.items.copy()
                partial = self.partial
                root = Path(self.root)

            for uid, content in item_renderer.process(root=str(root), partial=partial, items=items):
                self.result_ready.emit(uid, content)
