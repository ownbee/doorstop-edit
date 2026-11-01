from os import fsdecode
from pathlib import Path
from typing import Callable, List

from doorstop import Document
from watchdog.events import (
    FileSystemEvent,
    FileSystemEventHandler,
)
from watchdog.observers import Observer


class FileWatcher(FileSystemEventHandler):
    def __init__(self, on_dir_changed: Callable[[bool, str], None]) -> None:
        self.on_dir_changed = on_dir_changed
        self.observer = Observer()
        # self.observer.start()
        self.scheduled_docs: List[Document] = []

    def start(self) -> None:
        self.observer.start()

    def stop(self) -> None:
        if self.observer.is_alive():
            self.observer.stop()
            self.observer.join(timeout=5)

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

    def on_moved(self, event: FileSystemEvent) -> None:
        self.on_dir_changed(False, Path(fsdecode(event.src_path)).name)

    def on_created(self, event: FileSystemEvent) -> None:
        self.on_dir_changed(False, Path(fsdecode(event.src_path)).name)

    def on_deleted(self, event: FileSystemEvent) -> None:
        self.on_dir_changed(False, Path(fsdecode(event.src_path)).name)

    def on_modified(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            # Dont care.
            return

        self.on_dir_changed(True, Path(fsdecode(event.src_path)).name)
