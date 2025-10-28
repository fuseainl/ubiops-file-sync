"""Upload files to UbiOps bucket."""

import logging
from pathlib import Path

import backoff
import ubiops  # pyright: ignore[reportMissingTypeStubs]
from requests import exceptions

from .config import api_client, config
from .info import is_local_file_newer, list_local_files

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
def upload_file(local_path: Path) -> None:
    """Upload sigle file to remote.

    Parameters
    ----------
    remote_file : ubiops.FileItem
        FileItem containing file, size and time_created
    """
    if config.overwrite_newer and not is_local_file_newer(local_path=local_path):
        logger.info(
            "Skipping upload of %s (remote file is newer)",
            local_path,
        )
        return

    file_name = (
        Path(config.bucket_dir) / local_path.relative_to(config.local_sync_dir)
    ).as_posix()

    ubiops.utils.upload_file(  # pyright: ignore[reportAttributeAccessIssue]
        client=api_client,
        project_name=config.project_name,
        file_path=local_path.as_posix(),
        bucket_name=config.bucket_name,
        file_name=file_name,
    )
    logger.info(
        "Uploaded %s to %s/%s",
        local_path.as_posix(),
        config.bucket_name,
        file_name,
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
def upload_to_bucket() -> None:
    """Upload all files from a local folder to a UbiOps bucket (or bucket directory).

    If `overwrite_newer` is False, any remote file that has a newer timestamp than
    the local file will not be overwritten (skipped). If True, all local files are uploaded,
    overwriting existing files in the bucket even if they are newer.
    """
    if config.overwrite_newer:
        logger.info(
            "Uploading files from local folder %s to bucket '%s'/%s (skipping newer remote files)",
            Path(config.local_sync_dir).as_posix(),
            config.bucket_name,
            Path(config.bucket_dir).as_posix(),
        )
        local_files = list_local_files()

        # Traverse local files and upload conditionally
        for local_path in local_files:
            upload_file(local_path)
    else:
        logger.info(
            "Uploading all files from local folder %s to bucket '%s'/%s",
            Path(config.local_sync_dir).as_posix(),
            config.bucket_name,
            Path(config.bucket_dir).as_posix(),
        )
        try:
            ubiops.utils.upload_files(  # pyright: ignore[reportAttributeAccessIssue]
                client=api_client,
                project_name=config.project_name,
                file_paths=[Path(config.local_sync_dir).as_posix()],
                bucket_name=config.bucket_name,
                # UbiOps doesn't automatically end the file_prefix with a /
                file_prefix=Path(config.bucket_dir).as_posix() + "/",
                parallel_uploads=10,
            )
        except Exception:
            logger.exception("Error during bulk upload.")
            raise
    logger.info("Upload completed.")
