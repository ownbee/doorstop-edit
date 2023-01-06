from pathlib import Path
from typing import Dict, Generator, Iterable, Optional, Union

import doorstop

from doorstop_edit.utils.debug_timer import time_function


class DoorstopData:
    """Container holding all doorstop data (tree) for the whole application.

    It has accessors for easily getting and finding the data in a preferred form.

    The doorstop objects returned from this class should not be stored locally in a permanent way.
    The rule is: access the pieces that you need for the moment and access this class again when
    updates are needed. Object will be replaced when tree is reloaded and should therefore not be
    cached longterm since it can lead to saving old data, for example.
    """

    def __init__(self) -> None:
        self._tree: doorstop.Tree
        self.rebuild()
        self.original_item_data: Dict[str, str] = {}

    @time_function("Rebuilding document tree")
    def rebuild(self) -> None:
        self._tree = doorstop.build()
        self._tree.load()  # No lazy load to avoid lag spikes when user starts clicking around.

    def get_documents(self) -> Dict[str, doorstop.Document]:
        """Get all documents in doorstop tree.

        Return: A dict of {document_name: Document}
        """
        retval = {}
        for doc in self._tree:
            retval[doc.prefix] = doc
        return retval

    def find_document(self, name: str) -> Optional[doorstop.Document]:
        return self.get_documents().get(name, None)

    def find_item(self, item_uid: str, document: Union[str, doorstop.Document, None] = None) -> Optional[doorstop.Item]:
        doc: Optional[doorstop.Document] = None
        if document is None:
            for i_doc_name, i_doc in self.get_documents().items():
                if i_doc_name in item_uid:
                    doc = i_doc
                    break
        elif isinstance(document, str):
            doc = self.find_document(document)
        else:
            doc = document

        if doc is None:
            return None

        for item in doc:
            if item_uid == item.uid:
                return item

        return None

    def iter_items(self, document: Optional[doorstop.Document] = None) -> Generator[doorstop.Item, None, None]:
        tree: Iterable[doorstop.Document]
        if document is None:
            tree = self._tree
        else:
            tree = [document]
        doc: doorstop.Document
        for doc in tree:
            for item in doc:
                yield item

    def save_item(self, item: doorstop.Item) -> None:
        """Save item to disk.

        This application must always call this instead of directly calling Item.save() to be able to
        restore the item later.
        """
        p = Path(item.path)
        if str(item.uid) not in self.original_item_data and p.is_file():
            self.original_item_data[str(item.uid)] = p.read_text("utf-8")
        elif not p.is_file():
            # New file
            self.original_item_data[str(item.uid)] = ""
        item.save()
        item.auto = False  # Turn off auto-save that is enabled when calling save().
        if self.original_item_data.get(str(item.uid), "") == Path(item.path).read_text("utf-8"):
            # If no change, delete from database.
            del self.original_item_data[str(item.uid)]

    def get_original_data(self, item: doorstop.Item) -> Optional[str]:
        """None means no change."""
        return self.original_item_data.get(str(item.uid))

    def has_item_changed(self, item: doorstop.Item) -> bool:
        """Returns True if item has changed on disk since application start."""
        return str(item.uid) in self.original_item_data

    def restore_item(self, item: doorstop.Item) -> None:
        """Restore item to its original content on disk."""
        if str(item.uid) not in self.original_item_data:
            # Nothing to restore from.
            return
        p = Path(item.path)
        p.write_text(self.original_item_data[str(item.uid)], encoding="utf-8")
        item.load(reload=True)  # Reload item to mirror content on disk.
        del self.original_item_data[str(item.uid)]  # Delete entry to indicate no change.
