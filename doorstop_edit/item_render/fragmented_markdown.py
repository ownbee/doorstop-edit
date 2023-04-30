import tempfile
import xml.etree.ElementTree as etree
from pathlib import Path
from typing import Any, Optional, Union
from xml.etree.ElementTree import Element

from markdown import Markdown
from plantuml_markdown import PlantUMLMarkdownExtension

PLANTUML_CACHE = tempfile.gettempdir()


class FragmentedMarkdown(Markdown):
    def __init__(self, base_dir: Union[Path, str], **kwargs: Any) -> None:
        self.plantuml_cache = tempfile.gettempdir()
        kwargs["extensions"] = (
            "markdown.extensions.extra",
            "markdown.extensions.sane_lists",
            PlantUMLMarkdownExtension(
                server="http://www.plantuml.com/plantuml",
                cachedir=PLANTUML_CACHE,
                base_dir=str(base_dir),
                format="svg",
                classes="class1,class2",
                title="UML",
                alt="UML Diagram",
                theme="aws-orange",
            ),
        )

        self.fragments = etree.Element("div")
        self.num_fragments = 0
        super().__init__(**kwargs)

    def reset(self) -> None:
        """
        Resets all state variables so that we can start with a new text.
        """
        super().reset()
        self.fragments.clear()
        self.num_fragments = 0

    def add_fragement(self, source: str) -> Optional[Element]:
        """Register and process markdown fragment to be converted later.

        Keyword arguments:

        * source: Source text as a Unicode string.


        Markdown processing takes place in three steps:

        1. A bunch of "preprocessors" munge the input text.
        2. BlockParser() parses the high-level structural elements of the pre-processed text into an
           ElementTree.
        3. Append the created fragement element to a common root which will be processed in
           process_fragments().

        """
        # Fixup the source text
        if not source.strip():
            return None  # a blank unicode string

        try:
            source = str(source)
        except UnicodeDecodeError as e:  # pragma: no cover
            # Customise error message while maintaining original trackback
            e.reason += ". -- Note: Markdown only accepts unicode input!"
            raise

        # Split into lines and run the line preprocessors.
        self.lines = source.split("\n")
        for prep in self.preprocessors:
            self.lines = prep.run(self.lines)

        # Parse the high-level elements.
        root = self.parser.parseDocument(self.lines).getroot()
        self.fragments.append(root)
        self.num_fragments += 1
        return root

    def process_fragments(self) -> None:
        """Process all added fragments.

        This will run tree processors to resolve references, inlines and such. Must be called when
        all fragments have been added and before calling render_fragment()."""
        # Run the tree-processors
        for treeprocessor in self.treeprocessors:
            newRoot = treeprocessor.run(self.fragments)
            if newRoot is not None:
                self.fragments = newRoot

    def render_fragment(self, root: Optional[Element]) -> str:
        """
        Convert markdown to serialized XHTML or HTML.

        Keyword arguments:

        * source: Source text as a Unicode string.

        Markdown rendering takes place in two steps:

        1. Some post-processors are run against the text after the ElementTree
           has been serialized into text.
        2. The output is written to a string.

        """
        if root is None:
            return ""

        # Serialize _properly_.  Strip top-level tags.
        output = self.serializer(root)  # type: ignore

        # Run the text post-processors
        for pp in self.postprocessors:
            output = pp.run(output)

        return output.strip()

    def render_footer(self) -> str:
        """Render the footer div for all fragements.

        This is where footnotes are placed, should be called after process_fragments().
        """
        # The root Element for all fragements will have footer div at the end.
        num_footers = len(self.fragments) - self.num_fragments
        if num_footers > 0:
            footer = ""
            for i in range(num_footers):
                footer += self.render_fragment(self.fragments[self.num_fragments + i])
            return footer
        return ""
