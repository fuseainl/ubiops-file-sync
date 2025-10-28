"""Download files from UbiOps bucket."""

import logging
from pathlib import Path

import backoff
import ubiops  # pyright: ignore[reportMissingTypeStubs]
from requests import exceptions

from .config import config, core_api, parse_remote_time

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
    max_time=600,
    max_tries=5,
)
def list_remote_files(continuation_token: str | None = None) -> list[ubiops.FileItem]:
    """List files in remote bucket/prefix (with pagination)

    Returns
    -------
    list[ubiops.FileItem]
        List of files in remote bucket.
    """
    remote_files: list[ubiops.FileItem] = []

    response = core_api.files_list(
        config.project_name,
        config.bucket_name,
        prefix=config.bucket_dir,
        limit=1000,
        continuation_token=continuation_token,
    )

    remote_files.extend(response.files)
    token = getattr(response, "continuation_token", None)

    if token:
        remote_files.extend(list_remote_files(token))

    return remote_files


def list_local_files() -> list[Path]:
    """Recursively list all files in the locally synced directory

    Returns
    -------
    list[Path]
        List of local file paths
    """
    return [f for f in Path(config.local_sync_dir).rglob("*") if f.is_file()]


def _retrieve_local_path(remote_file: ubiops.FileItem | None) -> Path | None:
    if not remote_file:
        msg = "Please provide a remote file"
        raise ValueError(msg)

    local_path = Path(config.local_sync_dir) / str(remote_file.file)

    if local_path.exists() and local_path.is_file():
        return local_path

    return None


def _retrieve_remote_file(local_path: Path | None) -> ubiops.FileItem | None:
    if not local_path:
        msg = "Please provide a local path"
        raise ValueError(msg)

    remote_path = local_path.relative_to(config.local_sync_dir)
    remote_file = core_api.files_get(
        config.project_name,
        config.bucket_name,
        Path(config.bucket_dir) / remote_path,
    )

    return remote_file if remote_file else None  # pyright: ignore[reportReturnType]


def is_local_file_newer(
    remote_file: ubiops.FileItem | None = None,
    local_path: Path | None = None,
) -> bool:
    """Check if local (target) file is newer than remote.

    Parameters
    ----------
    remote_file : ubiops.FileItem
        FileItem containing file, size and time_created

    Returns
    -------
    bool
        True if local file is newer, False otherwise
    """
    if not (remote_file or local_path) or (remote_file and local_path):
        msg = "Please provide either remote_file or local_path."
        raise ValueError(msg)

    remote_file = remote_file or _retrieve_remote_file(local_path)
    local_path = local_path or _retrieve_local_path(remote_file)

    if not remote_file:
        return True

    if not local_path:
        return False

    remote_time = parse_remote_time(str(remote_file.time_created))
    local_mtime = local_path.stat().st_mtime

    return local_mtime > remote_time
