import logging
import tempfile
from typing import List, Optional

import doorstop
import markdown
from plantuml_markdown import PlantUMLMarkdownExtension
from PySide6.QtCore import QObject, QThread, Signal, Slot

from doorstop_edit.item_render.markdown_css import MARKDOWN_CSS

logger = logging.getLogger("gui")

BASE_URL = "file://"

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


class RenderWorker(QObject):
    """Concurrent worker for generating HTML from markdown.

    Rendering can sometimes be a bit slow, especially if it contains plantUML.
    """

    result_ready = Signal((str, str))  # type: ignore

    def __init__(self) -> None:
        super().__init__()

        self.plantuml_cache = tempfile.gettempdir()

        # Thread that will run until we destroy it.
        self.workerThread = QThread()
        self.moveToThread(self.workerThread)  # Move this object into the thread. All slots will run on the thread.
        self.workerThread.finished.connect(self.workerThread.deleteLater)  # type: ignore
        self.workerThread.start()

        self.markdown_instance: Optional[markdown.Markdown] = None
        self.markdown_instance_base_path = ""

    def destroy(self) -> None:
        self.workerThread.quit()
        if not self.workerThread.wait(5):
            self.workerThread.terminate()

    def _get_markdown(self, path: str) -> markdown.Markdown:
        """Get cached markdown instance.

        If document changes a new PlantUMLMarkdownExtension must be created since base_dir must be
        changed to the new document path in case files are included in the plantuml.
        """
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

    @Slot(list, doorstop.Item)
    def render(self, items: List[doorstop.Item], highlight_item: Optional[doorstop.Item]) -> None:
        html = ""
        for render_item in items:
            html_part = self._generate_html(render_item)
            if highlight_item is not None and render_item.uid == highlight_item.uid:
                html += f'<div id="{HTML_ID_SELECTED}">{html_part}</div>'
            else:
                html += f'<div class="{HTML_CLASS_UNSELECTED}">{html_part}</div>'

        if highlight_item is None:
            base_url = BASE_URL + "none/"
        else:
            # Relative to document good?
            # This is needed for images etc. in markdown to load properly...
            base_url = BASE_URL + highlight_item.document.path + "/"

        self.result_ready.emit(HTML_TEMPLATE.format(content=html, style=MARKDOWN_CSS), base_url)

    def _generate_html(self, item: doorstop.Item) -> str:
        markdown_content = ""

        for line in doorstop.publisher._lines_markdown([item], linkify=True):  # pylint: disable=protected-access
            markdown_content += str(line) + "\n"

        md = self._get_markdown(item.document.path)
        try:
            return md.convert(markdown_content)
        except Exception as e:
            msg = "Failed to render HTML from markdown."
            logger.error(msg, exc_info=e)
            return msg
