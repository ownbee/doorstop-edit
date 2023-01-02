import logging
from typing import List, Optional

import doorstop
import markdown
from PySide6.QtCore import QThread, Signal

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


class RenderWorker(QThread):
    """Concurrent worker for generating HTML from markdown.

    Rendering can sometimes be a bit slow, especially if it contains plantUML.
    """

    result_ready = Signal((str, str))  # type: ignore

    def __init__(self, md: markdown.Markdown, items: List[doorstop.Item], highlight_item: Optional[doorstop.Item]):
        super().__init__()
        self.md = md
        self.items = items
        self.highlight_item = highlight_item

    def run(self):
        html = ""
        for render_item in self.items:
            html_part = self._generate_html(render_item)
            if self.highlight_item is not None and render_item.uid == self.highlight_item.uid:
                html += f'<div id="{HTML_ID_SELECTED}">{html_part}</div>'
            else:
                html += f'<div class="{HTML_CLASS_UNSELECTED}">{html_part}</div>'

        if self.highlight_item is None:
            base_url = BASE_URL + "none"
        else:
            # Relative to document good?
            # This is needed for images etc. in markdown to load properly...
            base_url = BASE_URL + self.highlight_item.document.path

        self.result_ready.emit(HTML_TEMPLATE.format(content=html, style=MARKDOWN_CSS), base_url)

    def _generate_html(self, item: doorstop.Item) -> str:
        markdown_content = ""

        for line in doorstop.publisher._lines_markdown([item], linkify=True):  # pylint: disable=protected-access
            markdown_content += str(line) + "\n"

        try:
            return self.md.convert(markdown_content)
        except Exception as e:
            msg = "Failed to render HTML from markdown."
            logger.error(msg, exc_info=e)
            return msg
