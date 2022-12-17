import logging
import re
from typing import Callable, List, Optional, Union

import doorstop
from markdown_it import MarkdownIt
from PySide6.QtCore import QObject, QUrl
from PySide6.QtWebEngineCore import QWebEnginePage
from PySide6.QtWebEngineWidgets import QWebEngineView

from doorstop_edit.doorstop_data import DoorstopData
from doorstop_edit.item_render.markdown_css import MARKDOWN_CSS
from doorstop_edit.utils.debug_timer import time_function
from doorstop_edit.utils.item_matcher import match_level

logger = logging.getLogger("gui")

HTML_ID_SELECTED = "selected_item"
HTML_CLASS_UNSELECTED = "unselected"
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
<style type="text/css">
{style}
.unselected {{
    background-color: #121214;
}}
</style>
</head>
<body class="markdown-body">
{content}
 <script>
document.getElementById('selected_item')?.scrollIntoView();
</script>
</body>
</html>
"""


class RedirectOverridePage(QWebEnginePage):
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

        web_view.show()  # Render empty view to set backround color.

    @time_function("Rendering item HTML")
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

        html = ""
        for render_item in items_to_render:
            html_part = self._generate_html(render_item)
            if item is not None and render_item.uid == item.uid:
                html += f'<div id="{HTML_ID_SELECTED}">{html_part}</div>'
            else:
                html += f'<div class="{HTML_CLASS_UNSELECTED}">{html_part}</div>'

        if item is None:
            base_url = self.BASE_URL + "none"
        else:
            # Relative to document good?
            # This is needed for images etc. in markdown to load properly...
            base_url = self.BASE_URL + item.document.path
        self.web_view.setHtml(HTML_TEMPLATE.format(content=html, style=MARKDOWN_CSS), base_url)

    def _on_load_finished(self, ok: bool) -> None:
        if not ok:
            logger.warning("Web page failed to load.")

        if self._clear_history_on_load:
            self.web_view.history().clear()
            self._clear_history_on_load = False

    def _generate_html(self, item: doorstop.Item) -> str:
        markdown_content = ""

        for line in doorstop.publisher._lines_markdown([item], linkify=True):  # pylint: disable=protected-access
            markdown_content += str(line) + "\n"

        md = MarkdownIt("commonmark").enable("table")
        return md.render(markdown_content)

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
