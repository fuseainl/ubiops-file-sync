"""Continuously watch a local folder for new or changed files and upload them to a UbiOps bucket."""

import atexit
import logging
import threading
from pathlib import Path
from queue import Queue

from watchdog.events import FileClosedEvent, FileSystemEventHandler
from watchdog.observers import Observer

from .config import (
    api_client,
    config,
)
from .uploader import upload_file

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

file_queue = Queue()


class NewFileEventHandler(FileSystemEventHandler):
    """Event handler for closed files"""

    def on_closed(self, event: FileClosedEvent) -> None:
        """Add a file to the upload queue once it has been saved to disk.

        Parameters
        ----------
        event : FileClosedEvent
            Trigger on a file saving event.
        """
        if not event.is_directory and Path(str(event.src_path)).is_file():
            logger.info("Detected new or modified file: %s", event.src_path)
            file_queue.put(Path(str(event.src_path)))


def worker() -> None:
    """Watch the queue and upload files from it until the shutdown signal."""
    while True:
        local_path = file_queue.get()
        if local_path is None:
            file_queue.task_done()
            break

        upload_file(local_path=local_path)
        file_queue.task_done()


observer = Observer()
worker_thread = threading.Thread(target=worker, daemon=True)


def shutdown() -> None:
    """Register cleanup on exit"""
    logger.info("Shutting down file sync watcher...")
    observer.stop()
    observer.join(timeout=5)
    file_queue.put(None)
    worker_thread.join(timeout=10)
    api_client.close()
    logger.info("File sync watcher stopped.")


def watch_local_and_upload() -> None:
    """Continuously watch a local folder for new or changed files and upload them to a UbiOps bucket.

    If `overwrite_newer` is False, the upload will skip any file if the remote version is newer.
    This function spawns a background thread to monitor the local directory.
    Call `sync_and_watch` to perform an initial download before starting the watch.
    """
    # Start background threads
    observer.schedule(NewFileEventHandler(), str(config.local_sync_dir), recursive=True)
    observer.start()
    worker_thread.start()

    atexit.register(shutdown)
    logger.info("Started watching folder %s for changes", config.local_sync_dir)
