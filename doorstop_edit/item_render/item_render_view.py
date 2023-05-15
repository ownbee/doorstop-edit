import enum
import logging
from pathlib import Path
from typing import Callable, List, Optional, Union

import doorstop
from PySide6.QtCore import QObject, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import QWebEnginePage
from PySide6.QtWebEngineWidgets import QWebEngineView

from doorstop_edit.doorstop_data import DoorstopData
from doorstop_edit.item_render.markdown_css import MARKDOWN_CSS
from doorstop_edit.item_render.render_worker import RenderWorker
from doorstop_edit.utils.debug_timer import time_function
from doorstop_edit.utils.item_utils import match_level

logger = logging.getLogger("gui")


HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
<style type="text/css">
{style}
</style>
<script src="qrc:///qtwebchannel/qwebchannel.js"></script>
<script type="text/javascript">
new QWebChannel(qt.webChannelTransport, function(channel) {{
    window.py = channel.objects.py;
    window.selected_uid = null;

    py.html_update_item.connect(function(id, content, focus, hide) {{
        var display = "block";
        if (hide) {{
            display = "none";
        }}

        var obj = document.getElementById(id);
        if (obj) {{
            obj.innerHTML = content;
            obj.style.display = display;
        }}
        else {{
            var body = document.getElementById('markdown-body');
            if (body) {{
                let div = document.createElement("div");
                div.id = id;
                div.innerHTML = content
                div.style.display = display;
                body.append(div);
            }}
        }}

        if (focus) {{
            select_item(id);
        }}
        else {{
            focus_item(window.selected_uid);
        }}

    }});

    py.html_select_item.connect(function(id) {{
        select_item(id);
    }});
}});

function open_item(e, uid) {{
    py.open_item(uid);
    e.preventDefault();   // use this to NOT go to href site
}}

function select_item(id) {{
    if (id === window.selected_uid) {{
        return;
    }}

    var obj = document.getElementById(id);
    if (obj) {{
        obj.classList.add('selected');
        focus_item(id);
    }}

    var prev_obj = document.getElementById(window.selected_uid);
    if (prev_obj) {{
        prev_obj.classList.remove('selected');

    }}
    window.selected_uid = id;
}}


function focus_item(id) {{
    var obj = document.getElementById(id);
    if (obj) {{
        obj.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
    }}
}}
</script>
</head>
<body id="markdown-body" class="markdown-body">
{body}
</body>
</html>
"""


class CustomWebEnginePage(QWebEnginePage):
    """Custom WebEnginePage to customize how we handle link navigation"""

    def acceptNavigationRequest(
        self, url: Union[QUrl, str], nav_type: QWebEnginePage.NavigationType, is_main_frame: bool
    ) -> bool:
        if nav_type == QWebEnginePage.NavigationType.NavigationTypeLinkClicked:
            # Send the URL to the system default URL handler.
            QDesktopServices.openUrl(url)
            return False
        return super().acceptNavigationRequest(url, nav_type, is_main_frame)


class ItemRenderView(QObject):
    BASE_URL = "file://"

    signal_render_item_html = Signal(doorstop.Item)
    html_update_item = Signal(str, str, bool, bool)
    html_select_item = Signal(str)
    render_progress = Signal(int)

    class ViewMode(enum.Enum):

        Document = 0
        Section = 1
        Item = 2

    def __init__(self, web_view: QWebEngineView, doorstop_data: DoorstopData) -> None:
        super().__init__(web_view)
        self.web_view = web_view
        self.doorstop_data = doorstop_data

        self.on_open_viewer: Callable[[str], None] = lambda x: logger.info("on_open_viewer not connected")

        self.web_view.loadFinished.connect(self._on_load_finished)

        self.web_view.setPage(CustomWebEnginePage(self.web_view))
        self.channel = QWebChannel(self.web_view.page())
        self.web_view.page().setWebChannel(self.channel)
        self.channel.registerObject("py", self)

        self._clear_history_on_load = True
        self._view_mode = ItemRenderView.ViewMode.Document
        self._viewed_item: Optional[doorstop.Item] = None
        self._viewed_document: Optional[doorstop.Document] = None

        self._render_worker = RenderWorker()
        self._render_worker.result_ready.connect(self._on_render_finished)
        self._render_worker.progress.connect(self._on_render_progress)

        web_view.show()  # Render empty view to set backround color.

    @time_function("Changing content in HTML view")
    def show(self, item: Optional[doorstop.Item], force_reload: bool = False) -> None:
        self._viewed_item = item

        if item is None:
            self._viewed_document = None
            self._update(item, reload=True)
            return

        is_new_document = self._viewed_document is None or item.document.path != self._viewed_document.path

        force_reload = force_reload or is_new_document
        if force_reload:
            self._clear_history_on_load = True

        self._viewed_item = item
        self._viewed_document = item.document
        self._update(self._viewed_item, reload=force_reload)

    def destroy(self) -> None:
        self.web_view.page().deleteLater()
        self._render_worker.destroy()

    def set_view_mode(self, mode: ViewMode) -> None:
        self._view_mode = mode
        self.show(self._viewed_item, force_reload=True)

    def _update(self, item: Optional[doorstop.Item], reload: bool) -> None:
        def sort_func(val: doorstop.Item) -> List[int]:
            return [int(p) for p in str(val.level).split(".")]

        items_to_render: List[doorstop.Item] = []
        baseUrl = Path.cwd()
        if item is not None:
            self.html_select_item.emit(item.uid.value)
            baseUrl = Path(item.document.path)
            for doc_item in self.doorstop_data.iter_items(item.document):
                items_to_render.append(doc_item)
            items_to_render.sort(key=sort_func)

        body = ""
        for item in items_to_render:
            body += f'<div id="{item.uid.value}" class="doorstop-item"></div>\n'

        self.render_progress.emit(0)
        if reload:
            html = HTML_TEMPLATE.format(body=body, style=MARKDOWN_CSS)
            self.web_view.setHtml(html, baseUrl.resolve().as_uri() + "/")
            # Items will be rendered when page has loaded. Elements cannot be updated dynamically
            # before the divs exist in the page.
        else:
            self._render_items()  # Page already loaded, render items.

    @Slot(int)
    def _on_render_progress(self, percentage: int) -> None:
        self.render_progress.emit(percentage)

    @Slot(int)
    def _on_render_finished(self, id: str, content: str) -> None:
        hide = False
        item = self.doorstop_data.find_item(id)

        if item and self._view_mode == ItemRenderView.ViewMode.Section:
            if self._viewed_item and not match_level(item, self._viewed_item.level, include_parent=True):
                hide = True
        elif item and self._view_mode == ItemRenderView.ViewMode.Item:
            if self._viewed_item and self._viewed_item.uid.value != item.uid.value:
                hide = True

        if item and self._viewed_item:
            if not item.active and self._viewed_item.uid.value != item.uid.value:
                # Hide inactive item unless it is the selected one.
                hide = True

        focus = self._viewed_item and id == self._viewed_item.uid.value
        self.html_update_item.emit(id, content, focus, hide)

    @Slot(bool)
    def _on_load_finished(self, ok: bool) -> None:
        if not ok:
            logger.warning("Web page failed to load.")
            return

        if self._clear_history_on_load:
            self.web_view.history().clear()
            self._clear_history_on_load = False

        self._render_items()

    def _render_items(self) -> None:
        if self._viewed_item is None:
            return
        items = []
        for item in self.doorstop_data.iter_items(self._viewed_item.document):
            if item.uid.value == self._viewed_item.uid.value:
                continue  # We will handle this later

            items.append(item)

        items.insert(0, self._viewed_item)

        self._render_worker.render(items, Path(self._viewed_item.document.path))

    @Slot(str)
    def open_item(self, uid: str) -> None:
        self.on_open_viewer(uid)
