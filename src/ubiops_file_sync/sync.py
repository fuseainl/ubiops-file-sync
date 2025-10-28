"""Download from the remote bucket then continuously watch and upload new files."""

import logging

from .config import config
from .downloader import download_from_bucket
from .watcher import watch_local_and_upload

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def sync_and_watch() -> None:
    """Download from the remote bucket then continuously watch and upload new files.

    This function first performs a one-time download (using `download_from_bucket`), then starts
    a background watcher thread (using `watch_local_and_upload`). It returns immediately after starting
    the watcher. At program exit, the watcher will be automatically stopped.
    """
    logger.info("Starting sync: downloading then watching %s", config.local_sync_dir)
    # First, do one-time download from remote to local
    download_from_bucket()
    # Then start continuous watch for new local files
    watch_local_and_upload()
