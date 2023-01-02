import logging
import re
import tempfile
from typing import Callable, List, Optional, Union

import doorstop

# from markdown_it import MarkdownIt
import markdown
from plantuml_markdown import PlantUMLMarkdownExtension
from PySide6.QtCore import QObject, QUrl
from PySide6.QtWebEngineCore import QWebEnginePage
from PySide6.QtWebEngineWidgets import QWebEngineView

from doorstop_edit.doorstop_data import DoorstopData
from doorstop_edit.item_render.render_worker import RenderWorker
from doorstop_edit.utils.debug_timer import time_function
from doorstop_edit.utils.item_matcher import match_level

logger = logging.getLogger("gui")


class RedirectOverridePage(QWebEnginePage):
    """Class to enable Child and Parent items link navigation in HTML."""

    def __init__(self, parent: QObject, on_navigration_request: Callable[[str], None]):
        super().__init__(parent)
        self._on_navigration_request = on_navigration_request

    def acceptNavigationRequest(self, url: Union[QUrl, str], _2, _3):  # noqa
        if isinstance(url, QUrl):
            url = url.url()

        is_nav_ok = url.startswith("data:text/html")
        if not is_nav_ok:
            self._on_navigration_request(url)

        return is_nav_ok


class ItemRenderView:
    BASE_URL = "file://"

    def __init__(self, web_view: QWebEngineView, doorstop_data: DoorstopData) -> None:
        self.web_view = web_view
        self.doorstop_data = doorstop_data

        self.web_view.loadFinished.connect(self._on_load_finished)  # type: ignore

        page = RedirectOverridePage(web_view, self._on_navigration_request)
        web_view.setPage(page)

        self._clear_history_on_load = True
        self._section_mode_on = False
        self._viewed_item: Optional[doorstop.Item] = None
        self._render_worker: Optional[RenderWorker] = None

        self.plantuml_cache = tempfile.gettempdir()

        web_view.show()  # Render empty view to set backround color.

    def _get_markdown(self, path: str) -> markdown.Markdown:
        """Get cached markdown instance.

        If document changes a new PlantUMLMarkdownExtension must be created since base_dir must be
        changed to the new document path in case files are included in the plantuml.
        """
        if not hasattr(self, "markdown_instance"):
            self.markdown_instance = None

        if not hasattr(self, "markdown_instance_doc"):
            self.markdown_instance_base_path = ""

        if self.markdown_instance is None or self.markdown_instance_base_path != path:
            self.markdown_instance_base_path = path
            self.markdown_instance = markdown.Markdown(
                extensions=(
                    "markdown.extensions.extra",
                    "markdown.extensions.sane_lists",
                    PlantUMLMarkdownExtension(
                        server="http://www.plantuml.com/plantuml",
                        cachedir=self.plantuml_cache,
                        base_dir=self.markdown_instance_base_path,
                        format="svg",
                        classes="class1,class2",
                        title="UML",
                        alt="UML Diagram",
                        theme="carbon-gray",
                    ),
                )
            )
        return self.markdown_instance

    @time_function("Changing content in HTML view")
    def show(self, item: Optional[doorstop.Item]) -> None:
        self._viewed_item = item
        self._clear_history_on_load = True
        self._show(item)

    def set_section_mode(self, on: bool) -> None:
        self._section_mode_on = on
        self.show(self._viewed_item)

    def _show(self, item: Optional[doorstop.Item]) -> None:
        def sort_func(val: doorstop.Item) -> List[int]:
            return [int(p) for p in str(val.level).split(".")]

        items_to_render: List[doorstop.Item] = []
        if item is not None:
            if self._section_mode_on:
                for doc_item in self.doorstop_data.iter_items(item.document):
                    if not doc_item.active and doc_item.uid != item.uid:
                        # Hide inactive item unless it is the selected one.
                        continue
                    if match_level(doc_item, item.level, include_parent=True):
                        items_to_render.append(doc_item)
                items_to_render.sort(key=sort_func)
            else:
                items_to_render.append(item)

        if item is None:
            base_path = ""
        else:
            base_path = item.document.path

        if self._render_worker is not None and self._render_worker.isRunning():
            # If already running, terminate it first, otherwise the program will crash!
            self._render_worker.terminate()
            if not self._render_worker.wait(2):
                logger.warning("Could not terminate render worker.")
                return

        self._render_worker = RenderWorker(self._get_markdown(base_path), items_to_render, item)
        self._render_worker.result_ready.connect(self._on_render_finished)
        self._render_worker.start()

    def _on_render_finished(self, html: str, base_url: str):
        self.web_view.setHtml(html, base_url + "/")

    def _on_load_finished(self, ok: bool) -> None:
        if not ok:
            logger.warning("Web page failed to load.")
            return

        if self._clear_history_on_load:
            self.web_view.history().clear()
            self._clear_history_on_load = False

    def _on_navigration_request(self, url: str) -> None:
        if not url.startswith(self.BASE_URL):
            return

        item_uid: Optional[str] = None
        for doc_name, doc in self.doorstop_data.get_documents().items():
            if doc_name in url:
                escaped_doc_name = re.escape(doc_name + doc.sep)
                m = re.match(rf".*({escaped_doc_name}\d+).*", url)
                if m is not None:
                    item_uid = m.group(1)
                    break
        if item_uid is None:
            logger.warning("Could not find item uid in url: %s", url)
            return

        item = self.doorstop_data.find_item(item_uid)
        if item is None:
            logger.warning("Could not find item of uid %s", item_uid)
            return

        self._show(item)
