# UbiOps File Sync

A Python library for synchronizing files between a local directory and a UbiOps bucket. This library provides utilities for downloading files from UbiOps buckets, uploading files to buckets, and automatically watching local directories for changes to keep them in sync with remote storage.

## Features

- **File Download**: Download individual files or entire directories from a UbiOps bucket to a local folder
- **File Upload**: Upload individual files or entire directories from a local folder to a UbiOps bucket
- **Automatic Synchronization**: Watch a local directory for file changes and automatically upload new or modified files
- **Smart Conflict Resolution**: Optionally preserve newer files when syncing to avoid overwriting recent changes
- **Retry Logic**: Built-in exponential backoff retry mechanism for handling network errors and API exceptions
- **Parallel Operations**: Bulk upload and download operations use parallel processing for improved performance

## Installation

Install the library using pip:

```bash
pip install ubiops-file-sync
```

Or using uv:

```bash
uv pip install ubiops-file-sync
```

## Configuration

The library is configured via environment variables. You need to set the following variables before using the library:

| Environment Variable | Description | Required |
|---------------------|-------------|----------|
| `UBIOPS_API_HOST` | UbiOps API host URL (default: `https://api.ubiops.com/v2.1`) | No |
| `UBIOPS_API_TOKEN` | UbiOps API token (with or without "Token " prefix) | Yes |
| `BUCKET_PROJECT_NAME` | Name of the UbiOps project containing the bucket | Yes |
| `BUCKET_NAME` | Name of the UbiOps bucket to sync with | Yes |
| `BUCKET_DIR` | Directory/prefix within the bucket to sync (can be empty for root) | Yes |
| `LOCAL_SYNC_DIR` | Local directory path to sync with the bucket | Yes |
| `OVERWRITE_NEWER_FILES` | Whether to overwrite newer files. Set to `true`/`1`/`yes` to enable smart conflict resolution (preserves newer files), or `false`/`0`/`no` to always overwrite | Yes |

### Configuration Example

```bash
export UBIOPS_API_TOKEN="your_api_token_here"
export BUCKET_PROJECT_NAME="my-project"
export BUCKET_NAME="my-bucket"
export BUCKET_DIR="data"
export LOCAL_SYNC_DIR="/path/to/local/folder"
export OVERWRITE_NEWER_FILES="true"
```

## Usage

### Downloading Files

#### Download a Single File

Download a specific file from the UbiOps bucket:

```python
from ubiops import FileItem
from ubiops_file_sync.downloader import download_file

remote_file = FileItem(file="stub.txt")
download_file(remote_file)
```

#### Download All Files from Bucket

Download all files from the configured bucket directory to your local folder:

```python
from ubiops_file_sync.downloader import download_from_bucket

download_from_bucket()
```

When `OVERWRITE_NEWER_FILES` is `true`, this function will:

- Skip downloading files if the local version is newer than the remote version
- Only download files that are newer on the remote or don't exist locally

When `OVERWRITE_NEWER_FILES` is `false`, all remote files are downloaded, overwriting local files if they exist.

### Uploading Files

#### Upload a Single File

Upload a specific local file to the UbiOps bucket:

```python
from pathlib import Path
from ubiops_file_sync.uploader import upload_file

upload_file(local_path=Path("tests/input/another_stub.txt"))
```

#### Upload All Files to Bucket

Upload all files from your local sync directory to the UbiOps bucket:

```python
from ubiops_file_sync.uploader import upload_to_bucket

upload_to_bucket()
```

When `OVERWRITE_NEWER_FILES` is `true`, this function will:

- Skip uploading files if the remote version is newer than the local version
- Only upload files that are newer locally or don't exist remotely

When `OVERWRITE_NEWER_FILES` is `false`, all local files are uploaded, overwriting remote files if they exist.

### Watching for Changes

#### Watch Local Directory and Auto-Upload

Continuously monitor the local sync directory for file changes and automatically upload new or modified files:

```python
from ubiops_file_sync.watcher import watch_local_and_upload, shutdown

# Start watching for changes
watch_local_and_upload()

# ... your application code ...

# Gracefully shut down the watcher when done
shutdown()
```

The watcher:

- Runs in a background thread
- Monitors the local directory recursively
- Automatically uploads files when they are closed (saved)
- Respects the `OVERWRITE_NEWER_FILES` setting
- Uses a queue-based system for reliable file processing

**Note**: The watcher will automatically clean up when the program exits via `atexit`, but you can also call `shutdown()` explicitly for graceful termination.

#### Full Sync and Watch

Perform an initial download from the bucket and then start watching for local changes:

```python
from ubiops_file_sync.sync import sync_and_watch

# Download all files from bucket, then start watching for local changes
sync_and_watch()
```

This is a convenience function that:

1. First downloads all files from the remote bucket to the local directory
2. Then starts the file watcher to monitor for new or changed local files
3. Automatically handles shutdown on program exit

### Complete Example

Here's a complete example showing typical usage:

```python
from pathlib import Path
from ubiops import FileItem
from ubiops_file_sync.downloader import download_file, download_from_bucket
from ubiops_file_sync.uploader import upload_file, upload_to_bucket
from ubiops_file_sync.watcher import shutdown, watch_local_and_upload

# Download a specific file
remote_file = FileItem(file="stub.txt")
download_file(remote_file)

# Download all files from bucket
download_from_bucket()

# Upload a specific file
upload_file(local_path=Path("tests/input/another_stub.txt"))

# Upload all local files to bucket
upload_to_bucket()

# Start watching for changes
watch_local_and_upload()

# ... your application continues running ...

# Clean shutdown when done
shutdown()
```

## How It Works

### File Comparison Logic

When `OVERWRITE_NEWER_FILES` is enabled (`true`), the library compares file modification times to determine which version is newer:

- **For downloads**: If a local file exists and its modification time is newer than the remote file's creation time, the download is skipped.
- **For uploads**: If a remote file exists and its creation time is newer than the local file's modification time, the upload is skipped.

This ensures that newer changes are preserved in both directions.

### Retry Mechanism

All network operations use exponential backoff retry logic to handle transient errors:

- Maximum retry attempts: 5
- Maximum retry time: 300 seconds (600 seconds for file listing)
- Handles: `RequestException`, `Timeout`, `ConnectionError`, and `UbiOps.ApiException`

### Directory Structure

The library maintains the directory structure between local and remote storage. Files in subdirectories are preserved, and the `BUCKET_DIR` acts as a prefix for all remote file paths.

## Requirements

- Python >= 3.12
- UbiOps API access and credentials
- A configured UbiOps bucket

## Dependencies

- `backoff`: Exponential backoff retry logic
- `pydantic`: Configuration validation
- `ubiops`: UbiOps Python client library
- `watchdog`: File system monitoring for the QT event loop integration

## License

See LICENSE file for details.
