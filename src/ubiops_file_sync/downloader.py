"""Download files from UbiOps bucket."""

import logging
import shutil
from pathlib import Path

import backoff
import ubiops  # pyright: ignore[reportMissingTypeStubs]
from requests import exceptions

from .config import api_client, config
from .info import is_local_file_newer, list_remote_files

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


@backoff.on_exception(
    backoff.expo,
    (
        exceptions.RequestException,
        exceptions.Timeout,
        exceptions.ConnectionError,
        ubiops.ApiException,
    ),
    max_time=300,
    max_tries=5,
)
def download_file(remote_file: ubiops.FileItem) -> None:
    """Download sigle file from remote.

    Parameters
    ----------
    remote_file : ubiops.FileItem
        FileItem containing file, size and time_created
    """
    if config.overwrite_newer and is_local_file_newer(remote_file=remote_file):
        logger.info(
            "Skipping download of %s (local file is newer)",
            remote_file.file,
        )
        return

    (config.local_sync_dir / Path(str(remote_file.file))).parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    ubiops.utils.download_file(  # pyright: ignore[reportAttributeAccessIssue]
        api_client,
        config.project_name,
        bucket_name=config.bucket_name,
        file_name=Path(config.bucket_dir) / str(remote_file.file),
        output_path=str(config.local_sync_dir),
        stream=True,
        chunk_size=8192,
    )

    logger.info(
        "Downloaded %s from %s/%s",
        (Path(config.local_sync_dir) / str(remote_file.file)).as_posix(),
        config.bucket_name,
        (Path(config.bucket_dir) / str(remote_file.file)).as_posix(),
    )


def _move_downloaded_files() -> None:
    """
    Move files to intended sync path, removing the unwanted remote subpath.

    Only exists to mitigate design choices in upstream.
    """
    downloaded_files = [
        f
        for f in (Path(config.local_sync_dir) / config.bucket_dir).rglob("*")
        if f.is_file()
    ]
    remote_subpath = Path(config.bucket_dir).as_posix() + "/"

    for f in downloaded_files:
        new_location = f.as_posix().replace(remote_subpath, "")
        f.replace(new_location)

    shutil.rmtree(
        Path(config.local_sync_dir) / Path(config.bucket_dir).parts[0],
    )


@backoff.on_exception(
    backoff.expo,
    (
        exceptions.RequestException,
        exceptions.Timeout,
        exceptions.ConnectionError,
        ubiops.ApiException,
    ),
    max_tries=5,
)
def download_from_bucket() -> None:
    """Download all files from a UbiOps bucket (or bucket directory) to a local folder.

    If `overwrite_newer` is False, any local file that has a newer modification timestamp than
    the corresponding remote file will be preserved (not overwritten by an older remote file).
    If True, all files from the remote bucket (or prefix) are downloaded, overwriting local files if needed.
    """
    local_sync_dir = Path(config.local_sync_dir)
    local_sync_dir.mkdir(parents=True, exist_ok=True)

    if config.overwrite_newer:
        logger.info(
            "Downloading files from bucket '%s'/%s to local folder %s (skipping newer local files)",
            config.bucket_name,
            Path(config.bucket_dir).as_posix(),
            local_sync_dir.as_posix(),
        )
        remote_files = list_remote_files()

        # Download each file conditionally
        for remote_file in remote_files:
            download_file(remote_file)
    else:
        logger.info(
            "Downloading all files from bucket '%s'/%s to local folder %s",
            config.bucket_name,
            Path(config.bucket_dir).as_posix(),
            local_sync_dir.as_posix(),
        )
        try:
            ubiops.utils.download_files(  # pyright: ignore[reportAttributeAccessIssue]
                client=api_client,
                project_name=config.project_name,
                bucket_name=config.bucket_name,
                prefix=Path(config.bucket_dir).as_posix(),
                output_path=local_sync_dir.as_posix(),
                stream=True,
                chunk_size=8192,
                parallel_downloads=10,
            )
        except Exception:
            logger.exception("Error during bulk download.")
            raise

    _move_downloaded_files()

    logger.info("Download completed.")
