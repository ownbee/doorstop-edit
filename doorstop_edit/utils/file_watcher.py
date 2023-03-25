from pathlib import Path
from typing import Callable, List

from doorstop import Document
from watchdog.events import (
    FileCreatedEvent,
    FileDeletedEvent,
    FileModifiedEvent,
    FileMovedEvent,
    FileSystemEventHandler,
)
from watchdog.observers import Observer


class FileWatcher(FileSystemEventHandler):
    def __init__(self, on_dir_changed: Callable[[bool, str], None]) -> None:
        self.on_dir_changed = on_dir_changed
        self.observer = Observer()
        self.observer.start()
        self.scheduled_docs: List[Document] = []

    def pause(self) -> None:
        self.observer.unschedule_all()

    def resume(self) -> None:
        for doc in self.scheduled_docs:
            self.observer.schedule(self, doc.path, recursive=True)

    def watch(self, docs: List[Document]) -> None:
        if len(self.scheduled_docs) > 0:
            self.observer.unschedule_all()
        self.scheduled_docs = docs
        self.resume()

    def on_moved(self, event: FileMovedEvent) -> None:
        super().on_moved(event)

        self.on_dir_changed(False, Path(event.src_path).name)

    def on_created(self, event: FileCreatedEvent) -> None:
        super().on_created(event)

        self.on_dir_changed(False, Path(event.src_path).name)

    def on_deleted(self, event: FileDeletedEvent) -> None:
        super().on_deleted(event)

        self.on_dir_changed(False, Path(event.src_path).name)

    def on_modified(self, event: FileModifiedEvent) -> None:
        super().on_modified(event)
        if event.is_directory:
            # Dont care.
            return

        self.on_dir_changed(True, Path(event.src_path).name)
