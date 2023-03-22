import logging
import re
from typing import Callable, List, Optional, Union

import doorstop
from PySide6.QtCore import QObject, QUrl, Signal
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

    def acceptNavigationRequest(self, url: Union[QUrl, str], _2: QWebEnginePage.NavigationType, _3: bool) -> bool:
        if isinstance(url, QUrl):
            url = url.url()

        is_nav_ok = url.startswith("data:text/html")
        if not is_nav_ok:
            self._on_navigration_request(url)

        return is_nav_ok


class ItemRenderView(QObject):
    BASE_URL = "file://"

    signal_render_html = Signal((list, doorstop.Item))  # type: ignore

    def __init__(self, web_view: QWebEngineView, doorstop_data: DoorstopData) -> None:
        super().__init__(web_view)
        self.web_view = web_view
        self.doorstop_data = doorstop_data

        self.web_view.loadFinished.connect(self._on_load_finished)

        page = RedirectOverridePage(web_view, self._on_navigration_request)
        web_view.setPage(page)

        self._clear_history_on_load = True
        self._section_mode_on = False
        self._viewed_item: Optional[doorstop.Item] = None

        self._render_worker = RenderWorker()
        self._render_worker.result_ready.connect(self._on_render_finished)
        self.signal_render_html.connect(self._render_worker.render)

        web_view.show()  # Render empty view to set backround color.

    @time_function("Changing content in HTML view")
    def show(self, item: Optional[doorstop.Item]) -> None:
        self._viewed_item = item
        self._clear_history_on_load = True
        self._show(item)

    def destroy(self) -> None:
        self.web_view.page().deleteLater()
        self._render_worker.destroy()

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

        self.signal_render_html.emit(items_to_render, item)

    def _on_render_finished(self, html: str, base_url: str) -> None:
        self.web_view.setHtml(html, base_url)

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
