"""Unit tests for info module."""

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
import ubiops  # pyright: ignore[reportMissingTypeStubs]

from ubiops_file_sync.info import (
    _retrieve_local_path,
    _retrieve_remote_file,
    is_local_file_newer,
    list_local_files,
    list_remote_files,
    should_ignore_file,
    should_ignore_file_ext,
)


class TestShouldIgnoreFileExt:
    """Test should_ignore_file_ext function."""

    @patch("ubiops_file_sync.info.config")
    def test_should_ignore_file_ext_no_ignored_extensions(self, mock_config):
        """Test that no files are ignored when ignored_extensions is empty."""
        mock_config.ignored_extensions = []

        result = should_ignore_file_ext("file.txt")

        assert result is False

    @patch("ubiops_file_sync.info.config")
    def test_should_ignore_file_ext_matches_extension(self, mock_config):
        """Test that files with ignored extensions are detected."""
        mock_config.ignored_extensions = ["pyc", "tmp"]

        result = should_ignore_file_ext("file.pyc")

        assert result is True

    @patch("ubiops_file_sync.info.config")
    def test_should_ignore_file_ext_case_insensitive(self, mock_config):
        """Test that extension matching is case insensitive."""
        mock_config.ignored_extensions = ["pyc"]

        result = should_ignore_file_ext("file.PYC")

        assert result is True

    @patch("ubiops_file_sync.info.config")
    def test_should_ignore_file_ext_with_path_object(self, mock_config):
        """Test that function works with Path objects."""
        mock_config.ignored_extensions = ["pyc"]

        result = should_ignore_file_ext(Path("file.pyc"))

        assert result is True

    @patch("ubiops_file_sync.info.config")
    def test_should_ignore_file_ext_no_extension(self, mock_config):
        """Test that files without extensions are not ignored."""
        mock_config.ignored_extensions = ["pyc"]

        result = should_ignore_file_ext("file")

        assert result is False

    @patch("ubiops_file_sync.info.config")
    def test_should_ignore_file_ext_different_extension(self, mock_config):
        """Test that files with different extensions are not ignored."""
        mock_config.ignored_extensions = ["pyc"]

        result = should_ignore_file_ext("file.txt")

        assert result is False


class TestShouldIgnoreFile:
    """Test should_ignore_file function."""

    def test_should_ignore_file_not_a_file(self, tmp_path):
        """Test that directories are ignored."""
        dir_path = tmp_path / "dir"
        dir_path.mkdir()

        result = should_ignore_file(dir_path)

        assert result is True

    def test_should_ignore_file_empty_file(self, tmp_path):
        """Test that empty files are ignored."""
        empty_file = tmp_path / "empty.txt"
        empty_file.touch()

        result = should_ignore_file(empty_file)

        assert result is True

    @patch("ubiops_file_sync.info.should_ignore_file_ext")
    def test_should_ignore_file_with_ignored_extension(self, mock_should_ignore, tmp_path):
        """Test that files with ignored extensions are ignored."""
        mock_should_ignore.return_value = True
        file_path = tmp_path / "file.pyc"
        file_path.write_text("content")

        result = should_ignore_file(file_path)

        assert result is True

    @patch("ubiops_file_sync.info.should_ignore_file_ext")
    def test_should_ignore_file_valid_file(self, mock_should_ignore, tmp_path):
        """Test that valid files are not ignored."""
        mock_should_ignore.return_value = False
        file_path = tmp_path / "file.txt"
        file_path.write_text("content")

        result = should_ignore_file(file_path)

        assert result is False

    @patch("ubiops_file_sync.info.should_ignore_file_ext")
    def test_should_ignore_file_with_string_path(self, mock_should_ignore, tmp_path):
        """Test that function works with string paths."""
        mock_should_ignore.return_value = False
        file_path = tmp_path / "file.txt"
        file_path.write_text("content")

        result = should_ignore_file(str(file_path))

        assert result is False


class TestListRemoteFiles:
    """Test list_remote_files function."""

    @patch("ubiops_file_sync.info.should_ignore_file_ext")
    @patch("ubiops_file_sync.info.config")
    @patch("ubiops_file_sync.info.core_api")
    def test_list_remote_files_single_page(self, mock_core_api, mock_config, mock_should_ignore):
        """Test listing files with a single page of results."""
        mock_config.project_name = "test-project"
        mock_config.bucket_name = "test-bucket"
        mock_config.bucket_dir = Path("test/dir")
        mock_should_ignore.return_value = False

        mock_file1 = MagicMock()
        mock_file1.file = "test/dir/file1.txt"
        mock_file2 = MagicMock()
        mock_file2.file = "test/dir/file2.txt"

        mock_response = MagicMock()
        mock_response.files = [mock_file1, mock_file2]
        mock_response.continuation_token = None
        mock_core_api.files_list.return_value = mock_response

        result = list_remote_files()

        assert len(result) == 2
        assert mock_file1 in result
        assert mock_file2 in result
        mock_core_api.files_list.assert_called_once_with(
            "test-project",
            "test-bucket",
            prefix=Path("test/dir"),
            limit=1000,
            continuation_token=None,
        )

    @patch("ubiops_file_sync.info.should_ignore_file_ext")
    @patch("ubiops_file_sync.info.config")
    @patch("ubiops_file_sync.info.core_api")
    def test_list_remote_files_with_pagination(self, mock_core_api, mock_config, mock_should_ignore):
        """Test listing files with pagination."""
        mock_config.project_name = "test-project"
        mock_config.bucket_name = "test-bucket"
        mock_config.bucket_dir = Path("test/dir")
        mock_should_ignore.return_value = False

        mock_file1 = MagicMock()
        mock_file1.file = "test/dir/file1.txt"
        mock_file2 = MagicMock()
        mock_file2.file = "test/dir/file2.txt"
        mock_file3 = MagicMock()
        mock_file3.file = "test/dir/file3.txt"

        mock_response1 = MagicMock()
        mock_response1.files = [mock_file1, mock_file2]
        mock_response1.continuation_token = "token123"

        mock_response2 = MagicMock()
        mock_response2.files = [mock_file3]
        mock_response2.continuation_token = None

        mock_core_api.files_list.side_effect = [mock_response1, mock_response2]

        result = list_remote_files()

        assert len(result) == 3
        assert mock_core_api.files_list.call_count == 2

    @patch("ubiops_file_sync.info.should_ignore_file_ext")
    @patch("ubiops_file_sync.info.config")
    @patch("ubiops_file_sync.info.core_api")
    def test_list_remote_files_filters_ignored_extensions(
        self, mock_core_api, mock_config, mock_should_ignore
    ):
        """Test that files with ignored extensions are filtered out."""
        mock_config.project_name = "test-project"
        mock_config.bucket_name = "test-bucket"
        mock_config.bucket_dir = Path("test/dir")

        mock_file1 = MagicMock()
        mock_file1.file = "test/dir/file1.txt"
        mock_file2 = MagicMock()
        mock_file2.file = "test/dir/file2.pyc"

        def should_ignore_side_effect(file_path):
            return str(file_path).endswith(".pyc")

        mock_should_ignore.side_effect = should_ignore_side_effect

        mock_response = MagicMock()
        mock_response.files = [mock_file1, mock_file2]
        mock_response.continuation_token = None
        mock_core_api.files_list.return_value = mock_response

        result = list_remote_files()

        assert len(result) == 1
        assert mock_file1 in result
        assert mock_file2 not in result

    @patch("ubiops_file_sync.info.should_ignore_file_ext")
    @patch("ubiops_file_sync.info.config")
    @patch("ubiops_file_sync.info.core_api")
    def test_list_remote_files_with_continuation_token(
        self, mock_core_api, mock_config, mock_should_ignore
    ):
        """Test listing files with a continuation token."""
        mock_config.project_name = "test-project"
        mock_config.bucket_name = "test-bucket"
        mock_config.bucket_dir = Path("test/dir")
        mock_should_ignore.return_value = False

        mock_file = MagicMock()
        mock_file.file = "test/dir/file.txt"

        mock_response = MagicMock()
        mock_response.files = [mock_file]
        mock_response.continuation_token = None
        mock_core_api.files_list.return_value = mock_response

        result = list_remote_files("token123")

        assert len(result) == 1
        mock_core_api.files_list.assert_called_once_with(
            "test-project",
            "test-bucket",
            prefix=Path("test/dir"),
            limit=1000,
            continuation_token="token123",
        )


class TestListLocalFiles:
    """Test list_local_files function."""

    @patch("ubiops_file_sync.info.should_ignore_file_ext")
    @patch("ubiops_file_sync.info.config")
    def test_list_local_files(self, mock_config, mock_should_ignore, tmp_path):
        """Test listing local files."""
        local_dir = tmp_path / "local"
        local_dir.mkdir()
        mock_config.local_sync_dir = local_dir
        mock_should_ignore.return_value = False

        file1 = local_dir / "file1.txt"
        file1.write_text("content1")
        file2 = local_dir / "file2.txt"
        file2.write_text("content2")
        subdir = local_dir / "subdir"
        subdir.mkdir()
        file3 = subdir / "file3.txt"
        file3.write_text("content3")

        result = list_local_files()

        assert len(result) == 3
        assert file1 in result
        assert file2 in result
        assert file3 in result

    @patch("ubiops_file_sync.info.should_ignore_file_ext")
    @patch("ubiops_file_sync.info.config")
    def test_list_local_files_filters_ignored_extensions(
        self, mock_config, mock_should_ignore, tmp_path
    ):
        """Test that files with ignored extensions are filtered out."""
        local_dir = tmp_path / "local"
        local_dir.mkdir()
        mock_config.local_sync_dir = local_dir

        def should_ignore_side_effect(file_path):
            return str(file_path).endswith(".pyc")

        mock_should_ignore.side_effect = should_ignore_side_effect

        file1 = local_dir / "file1.txt"
        file1.write_text("content1")
        file2 = local_dir / "file2.pyc"
        file2.write_text("content2")

        result = list_local_files()

        assert len(result) == 1
        assert file1 in result
        assert file2 not in result

    @patch("ubiops_file_sync.info.should_ignore_file_ext")
    @patch("ubiops_file_sync.info.config")
    def test_list_local_files_empty_directory(self, mock_config, mock_should_ignore, tmp_path):
        """Test listing files from empty directory."""
        local_dir = tmp_path / "local"
        local_dir.mkdir()
        mock_config.local_sync_dir = local_dir
        mock_should_ignore.return_value = False

        result = list_local_files()

        assert result == []


class TestRetrieveLocalPath:
    """Test _retrieve_local_path function."""

    @patch("ubiops_file_sync.info.config")
    def test_retrieve_local_path_file_exists(self, mock_config, tmp_path):
        """Test retrieving local path when file exists."""
        local_dir = tmp_path / "local"
        local_dir.mkdir()
        mock_config.local_sync_dir = local_dir
        mock_config.bucket_dir = Path("test/dir")

        file_path = local_dir / "subdir" / "file.txt"
        file_path.parent.mkdir()
        file_path.write_text("content")

        mock_file_item = MagicMock()
        mock_file_item.file = "test/dir/subdir/file.txt"

        result = _retrieve_local_path(mock_file_item)

        assert result == file_path

    @patch("ubiops_file_sync.info.config")
    def test_retrieve_local_path_file_not_exists(self, mock_config, tmp_path):
        """Test retrieving local path when file doesn't exist."""
        local_dir = tmp_path / "local"
        local_dir.mkdir()
        mock_config.local_sync_dir = local_dir
        mock_config.bucket_dir = Path("test/dir")

        mock_file_item = MagicMock()
        mock_file_item.file = "test/dir/subdir/file.txt"

        result = _retrieve_local_path(mock_file_item)

        assert result is None

    def test_retrieve_local_path_no_remote_file(self):
        """Test that ValueError is raised when no remote file is provided."""
        with pytest.raises(ValueError, match="Please provide a remote file"):
            _retrieve_local_path(None)


class TestRetrieveRemoteFile:
    """Test _retrieve_remote_file function."""

    @patch("ubiops_file_sync.info.config")
    @patch("ubiops_file_sync.info.core_api")
    def test_retrieve_remote_file_exists(self, mock_core_api, mock_config, tmp_path):
        """Test retrieving remote file when it exists."""
        local_dir = tmp_path / "local"
        local_dir.mkdir()
        mock_config.local_sync_dir = local_dir
        mock_config.project_name = "test-project"
        mock_config.bucket_name = "test-bucket"
        mock_config.bucket_dir = Path("test/dir")

        file_path = local_dir / "subdir" / "file.txt"
        file_path.parent.mkdir()
        file_path.write_text("content")

        mock_remote_file = MagicMock()
        mock_core_api.files_get.return_value = mock_remote_file

        result = _retrieve_remote_file(file_path)

        assert result == mock_remote_file
        mock_core_api.files_get.assert_called_once_with(
            "test-project",
            "test-bucket",
            Path("test/dir") / Path("subdir/file.txt"),
        )

    @patch("ubiops_file_sync.info.config")
    @patch("ubiops_file_sync.info.core_api")
    def test_retrieve_remote_file_not_exists(self, mock_core_api, mock_config, tmp_path):
        """Test retrieving remote file when it doesn't exist."""
        local_dir = tmp_path / "local"
        local_dir.mkdir()
        mock_config.local_sync_dir = local_dir
        mock_config.project_name = "test-project"
        mock_config.bucket_name = "test-bucket"
        mock_config.bucket_dir = Path("test/dir")

        file_path = local_dir / "subdir" / "file.txt"
        file_path.parent.mkdir()
        file_path.write_text("content")

        mock_core_api.files_get.return_value = None

        result = _retrieve_remote_file(file_path)

        assert result is None

    def test_retrieve_remote_file_no_local_path(self):
        """Test that ValueError is raised when no local path is provided."""
        with pytest.raises(ValueError, match="Please provide a local path"):
            _retrieve_remote_file(None)


class TestIsLocalFileNewer:
    """Test is_local_file_newer function."""

    @patch("ubiops_file_sync.info.parse_remote_time")
    @patch("ubiops_file_sync.info._retrieve_local_path")
    def test_is_local_file_newer_with_remote_file_local_newer(
        self, mock_retrieve_local, mock_parse_time, tmp_path
    ):
        """Test when local file is newer than remote."""
        local_file = tmp_path / "file.txt"
        local_file.write_text("content")
        # Set mtime to a recent timestamp
        import time

        recent_time = time.time()
        local_file.touch()
        import os

        os.utime(local_file, (recent_time, recent_time))

        mock_retrieve_local.return_value = local_file
        mock_parse_time.return_value = recent_time - 100  # Remote is older

        mock_remote_file = MagicMock()
        mock_remote_file.time_created = "2024-01-15T10:30:00Z"

        result = is_local_file_newer(remote_file=mock_remote_file)

        assert result is True

    @patch("ubiops_file_sync.info.parse_remote_time")
    @patch("ubiops_file_sync.info._retrieve_local_path")
    def test_is_local_file_newer_with_remote_file_remote_newer(
        self, mock_retrieve_local, mock_parse_time, tmp_path
    ):
        """Test when remote file is newer than local."""
        local_file = tmp_path / "file.txt"
        local_file.write_text("content")
        import time

        old_time = time.time() - 100
        local_file.touch()
        import os

        os.utime(local_file, (old_time, old_time))

        mock_retrieve_local.return_value = local_file
        mock_parse_time.return_value = time.time()  # Remote is newer

        mock_remote_file = MagicMock()
        mock_remote_file.time_created = "2024-01-15T10:30:00Z"

        result = is_local_file_newer(remote_file=mock_remote_file)

        assert result is False

    @patch("ubiops_file_sync.info.parse_remote_time")
    @patch("ubiops_file_sync.info._retrieve_remote_file")
    def test_is_local_file_newer_with_local_path_local_newer(
        self, mock_retrieve_remote, mock_parse_time, tmp_path
    ):
        """Test when local file is newer using local_path parameter."""
        local_file = tmp_path / "file.txt"
        local_file.write_text("content")
        import time

        recent_time = time.time()
        local_file.touch()
        import os

        os.utime(local_file, (recent_time, recent_time))

        mock_remote_file = MagicMock()
        mock_remote_file.time_created = "2024-01-15T10:30:00Z"
        mock_retrieve_remote.return_value = mock_remote_file
        mock_parse_time.return_value = recent_time - 100  # Remote is older

        result = is_local_file_newer(local_path=local_file)

        assert result is True

    @patch("ubiops_file_sync.info._retrieve_local_path")
    def test_is_local_file_newer_no_local_file(self, mock_retrieve_local):
        """Test when local file doesn't exist."""
        mock_retrieve_local.return_value = None

        mock_remote_file = MagicMock()
        mock_remote_file.time_created = "2024-01-15T10:30:00Z"

        result = is_local_file_newer(remote_file=mock_remote_file)

        assert result is False

    @patch("ubiops_file_sync.info._retrieve_remote_file")
    def test_is_local_file_newer_no_remote_file(self, mock_retrieve_remote, tmp_path):
        """Test when remote file doesn't exist."""
        local_file = tmp_path / "file.txt"
        local_file.write_text("content")

        mock_retrieve_remote.return_value = None

        result = is_local_file_newer(local_path=local_file)

        assert result is True

    def test_is_local_file_newer_both_provided(self):
        """Test that ValueError is raised when both parameters are provided."""
        mock_remote_file = MagicMock()
        mock_local_path = Path("file.txt")

        with pytest.raises(ValueError, match="Please provide either remote_file or local_path"):
            is_local_file_newer(remote_file=mock_remote_file, local_path=mock_local_path)

    def test_is_local_file_newer_neither_provided(self):
        """Test that ValueError is raised when neither parameter is provided."""
        with pytest.raises(ValueError, match="Please provide either remote_file or local_path"):
            is_local_file_newer()

