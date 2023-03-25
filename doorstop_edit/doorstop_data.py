from pathlib import Path
from typing import Dict, Generator, Iterable, Optional, Union

import doorstop
from PySide6.QtCore import QObject, Signal, Slot

from doorstop_edit.utils.debug_timer import time_function
from doorstop_edit.utils.file_watcher import FileWatcher


class DoorstopData(QObject):
    """Container holding all doorstop data (tree) for the whole application.

    It has accessors for easily getting and finding the data in a preferred form.

    The doorstop objects returned from this class should not be stored locally in a permanent way.
    The rule is: access the pieces that you need for the moment and access this class again when
    updates are needed. Object will be replaced when tree is reloaded and should therefore not be
    cached longterm since it can lead to saving old data, for example.
    """

    tree_changed = Signal((bool))  # Called when tree changed on disk

    def __init__(self, parent: Optional[QObject], root: Path) -> None:
        super().__init__(parent=parent)
        self._root = root
        self._tree: Optional[doorstop.Tree] = None
        self.original_item_data: Dict[str, str] = {}
        self.file_watcher = FileWatcher(self._on_filewatch_callback)

    def _on_filewatch_callback(self, modified_only: bool, filename: str) -> None:
        do_rebuild = False
        if modified_only:
            item = self.find_item(Path(filename).stem)
            if item is None:
                do_rebuild = True
            else:
                item.load(reload=True)
                self.tree_changed.emit(True)

        if ".doorstop" in filename:
            do_rebuild = True

        if not modified_only or do_rebuild:
            self.rebuild(only_reload=modified_only)

    @Slot(bool)
    @time_function("Rebuilding document tree")
    def rebuild(self, only_reload: bool) -> None:
        if self._tree is None or not only_reload:
            self.file_watcher.pause()  # Dont trigger any events while rebuilding
            self._tree = doorstop.build(cwd=str(self._root), root=str(self._root))

        # Always load after build (no lazy) load to avoid lag spikes when user starts clicking around.
        self._tree.load(reload=True)

        self.file_watcher.watch(list(self.get_documents().values()))
        self.tree_changed.emit(only_reload)

    def get_documents(self) -> Dict[str, doorstop.Document]:
        """Get all documents in doorstop tree.

        Return: A dict of {document_name: Document}
        """
        retval = {}
        for doc in self._tree or []:
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
            tree = self._tree or []
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
        self.file_watcher.pause()  # To not trigger file changes on editor changes.

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

        self.file_watcher.resume()

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
