import logging
import multiprocessing as mp
import tempfile
import time
from pathlib import Path
from queue import Empty
from typing import List, Optional, Tuple, Union

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


def process(q: mp.Queue, root: str, items: List[doorstop.Item]) -> None:
    try:
        md = FragmentedMarkdown(base_dir=root)
        progress = ProgressTracker(len(items) * 2)
        prepared_items = []
        for item in items:
            prepared_items.append(_prepare(md, item))
            if progress.progress_one():
                q.put([QUEUE_PROGRESS_TYPE, progress.get()])

        md.process_fragments()

        for i, item in enumerate(items):
            content = _render_item(md, item, prepared_items[i])
            q.put([QUEUE_DATA_TYPE, item.uid.value, content])
            if progress.progress_one():
                q.put([QUEUE_PROGRESS_TYPE, progress.get()])

        q.put([QUEUE_DATA_TYPE, "footer", md.render_footer()])
        if progress.progress_one():
            q.put([QUEUE_PROGRESS_TYPE, 100])
    except Exception as e:
        logger.error("Failed to process markdown:", e)


def _render_item(md: FragmentedMarkdown, item: doorstop.Item, attrs: List[Tuple[str, Union[str, Element]]]) -> str:
    if str(item.level).endswith(".0") and not item.normative:
        levels = str(item.level).count(".")
        header_tag = f"h{levels}"
    else:
        header_tag = "p"

    html = f"<{header_tag}><b>{str(item.level)} {item.header}</b> <small>{item.uid.value}</small></{header_tag}>"

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


def _prepare(md: FragmentedMarkdown, item: doorstop.Item) -> List[Tuple[str, Union[str, Element]]]:
    rows: List[Tuple[str, Union[str, Element]]] = []
    rows.append(("text", md.add_fragement(item.text) or ""))
    if item.document and item.document.publish:
        for attr in item.document.publish:
            if attr in [row[0] for row in rows]:
                continue
            val = item.attribute(attr)
            if val is None:
                continue
            if isinstance(val, str) and len(val) > 0:
                rows.append((attr, md.add_fragement(val) or ""))
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

    return rows


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

        self.items: List[doorstop.Item] = []
        self.root: Path = Path()

    def destroy(self) -> None:
        with QMutexLocker(self.mutex):
            self.abort = True
            self.condition.wakeOne()
        self.wait()

    @time_function("render")
    def render(self, items: List[doorstop.Item], root: Path) -> None:
        """Render HTML from doorstop items.

        Args:
            items: Items to render HTML from.
            root: File system path to document root. Needed to load images etc. correctly.
        """
        with QMutexLocker(self.mutex):
            self.items = items
            self.root = root
            self.change += 1
            self.restart = True
            self.condition.wakeOne()

        if not self.isRunning():
            self.start(QThread.Priority.NormalPriority)

    def _process_queue_data(self, queue: mp.Queue, block: bool) -> bool:
        try:
            max_count = 10
            while max_count > 0:
                max_count -= 1
                result = queue.get(block=block, timeout=0.5)
                q_type = result[0]
                if q_type == QUEUE_DATA_TYPE:
                    id: str = result[1]
                    content: str = result[2]
                    self.result_ready.emit(id, content)
                else:
                    progress: int = result[1]
                    self.progress.emit(progress)
        except Empty:
            return False
        return True

    def run(self) -> None:

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
                root = Path(self.root)

            queue: mp.Queue = mp.Queue()
            # Using multiprocessing to work-around Python's GIL. If rendering is done on main
            # thread, it will make the GUI non-responsive.
            p = mp.Process(
                target=process,
                args=(
                    queue,
                    str(root),
                    items,
                ),
            )
            deadline = time.time() + 10  # In case process hangs...
            p.start()
            aborted = False
            while p.is_alive() and time.time() < deadline:
                with QMutexLocker(self.mutex):
                    if self.restart or self.abort:
                        aborted = True
                        break
                self._process_queue_data(queue, block=True)

            if aborted:
                p.terminate()

            # Process rest of the queue.
            while self._process_queue_data(queue, block=False):
                pass

            if p.is_alive():
                p.kill()
