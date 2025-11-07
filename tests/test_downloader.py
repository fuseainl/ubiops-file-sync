"""Unit tests for downloader module."""

import shutil
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
import ubiops  # pyright: ignore[reportMissingTypeStubs]

from ubiops_file_sync.downloader import (
    _move_downloaded_files,
    _retrieve_remote_file_path,
    download_file,
    download_from_bucket,
)


class TestRetrieveRemoteFilePath:
    """Test _retrieve_remote_file_path function."""

    @patch("ubiops_file_sync.downloader.config")
    def test_retrieve_remote_file_path_with_bucket_dir(self, mock_config):
        """Test retrieving path when file is relative to bucket_dir."""
        mock_config.bucket_dir = Path("test/dir")
        mock_file_item = MagicMock()
        mock_file_item.file = "test/dir/subdir/file.txt"

        result = _retrieve_remote_file_path(mock_file_item)

        assert result == Path("test/dir/subdir/file.txt")

    @patch("ubiops_file_sync.downloader.config")
    def test_retrieve_remote_file_path_without_bucket_dir(self, mock_config):
        """Test retrieving path when file is not relative to bucket_dir."""
        mock_config.bucket_dir = Path("test/dir")
        mock_file_item = MagicMock()
        mock_file_item.file = "other/file.txt"

        result = _retrieve_remote_file_path(mock_file_item)

        assert result == Path("test/dir/other/file.txt")


class TestDownloadFile:
    """Test download_file function."""

    @patch("ubiops_file_sync.downloader.should_ignore_file_ext")
    @patch("ubiops_file_sync.downloader.is_local_file_newer")
    @patch("ubiops_file_sync.downloader.config")
    @patch("ubiops_file_sync.downloader.ubiops")
    def test_download_file_skips_ignored_extensions(
        self, mock_ubiops, mock_config, mock_is_newer, mock_should_ignore
    ):
        """Test that files with ignored extensions are skipped."""
        mock_config.bucket_dir = Path("test/dir")
        mock_config.local_sync_dir = Path("/tmp/local")
        mock_config.overwrite_newer = False
        mock_should_ignore.return_value = True

        mock_file_item = MagicMock()
        mock_file_item.file = "test/dir/file.pyc"

        download_file(mock_file_item)

        mock_ubiops.utils.download_file.assert_not_called()

    @patch("ubiops_file_sync.downloader.should_ignore_file_ext")
    @patch("ubiops_file_sync.downloader.is_local_file_newer")
    @patch("ubiops_file_sync.downloader.config")
    @patch("ubiops_file_sync.downloader.ubiops")
    def test_download_file_skips_newer_local_file(
        self, mock_ubiops, mock_config, mock_is_newer, mock_should_ignore
    ):
        """Test that newer local files are skipped when overwrite_newer is True."""
        mock_config.bucket_dir = Path("test/dir")
        mock_config.local_sync_dir = Path("/tmp/local")
        mock_config.overwrite_newer = True
        mock_should_ignore.return_value = False
        mock_is_newer.return_value = True

        mock_file_item = MagicMock()
        mock_file_item.file = "test/dir/file.txt"

        download_file(mock_file_item)

        mock_ubiops.utils.download_file.assert_not_called()

    @patch("ubiops_file_sync.downloader.should_ignore_file_ext")
    @patch("ubiops_file_sync.downloader.is_local_file_newer")
    @patch("ubiops_file_sync.downloader.config")
    @patch("ubiops_file_sync.downloader.ubiops")
    @patch("ubiops_file_sync.downloader.api_client")
    def test_download_file_downloads_file(
        self,
        mock_api_client,
        mock_ubiops,
        mock_config,
        mock_is_newer,
        mock_should_ignore,
        tmp_path,
    ):
        """Test that file is downloaded when conditions are met."""
        local_dir = tmp_path / "local"
        local_dir.mkdir()
        mock_config.bucket_dir = Path("test/dir")
        mock_config.local_sync_dir = local_dir
        mock_config.project_name = "test-project"
        mock_config.bucket_name = "test-bucket"
        mock_config.overwrite_newer = False
        mock_should_ignore.return_value = False

        mock_file_item = MagicMock()
        mock_file_item.file = "test/dir/file.txt"

        download_file(mock_file_item)

        # The output_path is the parent of local_subpath, which is local_sync_dir
        # when file_path is "test/dir/file.txt" and bucket_dir is "test/dir"
        mock_ubiops.utils.download_file.assert_called_once_with(
            mock_api_client,
            "test-project",
            bucket_name="test-bucket",
            file_name="test/dir/file.txt",
            output_path=str(local_dir),
            stream=True,
            chunk_size=8192,
        )

    @patch("ubiops_file_sync.downloader.should_ignore_file_ext")
    @patch("ubiops_file_sync.downloader.is_local_file_newer")
    @patch("ubiops_file_sync.downloader.config")
    @patch("ubiops_file_sync.downloader.ubiops")
    @patch("ubiops_file_sync.downloader.api_client")
    def test_download_file_creates_parent_directories(
        self,
        mock_api_client,
        mock_ubiops,
        mock_config,
        mock_is_newer,
        mock_should_ignore,
        tmp_path,
    ):
        """Test that parent directories are created before download."""
        local_dir = tmp_path / "local"
        local_dir.mkdir()
        mock_config.bucket_dir = Path("test/dir")
        mock_config.local_sync_dir = local_dir
        mock_config.project_name = "test-project"
        mock_config.bucket_name = "test-bucket"
        mock_config.overwrite_newer = False
        mock_should_ignore.return_value = False

        mock_file_item = MagicMock()
        mock_file_item.file = "test/dir/subdir/file.txt"

        download_file(mock_file_item)

        # When file_path is "test/dir/subdir/file.txt" and bucket_dir is "test/dir",
        # local_subpath is local_dir / "subdir/file.txt", so parent is local_dir / "subdir"
        expected_dir = local_dir / "subdir"
        assert expected_dir.exists()


class TestMoveDownloadedFiles:
    """Test _move_downloaded_files function."""

    @patch("ubiops_file_sync.downloader.config")
    def test_move_downloaded_files(self, mock_config, tmp_path):
        """Test moving downloaded files to correct location."""
        local_dir = tmp_path / "local"
        local_dir.mkdir()
        mock_config.local_sync_dir = local_dir
        mock_config.bucket_dir = Path("test/dir")

        # Create structure as if files were downloaded
        downloaded_dir = local_dir / "test" / "dir"
        downloaded_dir.mkdir(parents=True)
        subdir = downloaded_dir / "subdir"
        subdir.mkdir()

        file1 = subdir / "file1.txt"
        file1.write_text("content1")
        file2 = downloaded_dir / "file2.txt"
        file2.write_text("content2")

        # Create destination directories that will be needed after moving
        # The function removes "test/dir/" from paths, so:
        # - file1: local/test/dir/subdir/file1.txt -> local/subdir/file1.txt
        # - file2: local/test/dir/file2.txt -> local/file2.txt
        (local_dir / "subdir").mkdir(exist_ok=True)

        _move_downloaded_files()

        # Files should be moved to local_dir
        # The remote_subpath "test/dir/" is removed from paths
        assert (local_dir / "subdir" / "file1.txt").exists()
        assert (local_dir / "file2.txt").exists()
        # Original structure should be removed (only the first part of bucket_dir)
        assert not (local_dir / "test").exists()


class TestDownloadFromBucket:
    """Test download_from_bucket function."""

    @patch("ubiops_file_sync.downloader.list_remote_files")
    @patch("ubiops_file_sync.downloader.download_file")
    @patch("ubiops_file_sync.downloader.config")
    def test_download_from_bucket_with_overwrite_newer(
        self, mock_config, mock_download_file, mock_list_remote_files, tmp_path
    ):
        """Test download when overwrite_newer is True."""
        local_dir = tmp_path / "local"
        local_dir.mkdir()
        mock_config.local_sync_dir = local_dir
        mock_config.bucket_name = "test-bucket"
        mock_config.bucket_dir = Path("test/dir")
        mock_config.overwrite_newer = True

        mock_file1 = MagicMock()
        mock_file2 = MagicMock()
        mock_list_remote_files.return_value = [mock_file1, mock_file2]

        download_from_bucket()

        assert mock_list_remote_files.called
        assert mock_download_file.call_count == 2
        mock_download_file.assert_any_call(mock_file1)
        mock_download_file.assert_any_call(mock_file2)

    @patch("ubiops_file_sync.downloader._move_downloaded_files")
    @patch("ubiops_file_sync.downloader.config")
    @patch("ubiops_file_sync.downloader.ubiops")
    @patch("ubiops_file_sync.downloader.api_client")
    def test_download_from_bucket_without_overwrite_newer(
        self, mock_api_client, mock_ubiops, mock_config, mock_move_files, tmp_path
    ):
        """Test bulk download when overwrite_newer is False."""
        local_dir = tmp_path / "local"
        local_dir.mkdir()
        mock_config.local_sync_dir = local_dir
        mock_config.project_name = "test-project"
        mock_config.bucket_name = "test-bucket"
        mock_config.bucket_dir = Path("test/dir")
        mock_config.overwrite_newer = False

        download_from_bucket()

        mock_ubiops.utils.download_files.assert_called_once_with(
            client=mock_api_client,
            project_name="test-project",
            bucket_name="test-bucket",
            prefix="test/dir",
            output_path=str(local_dir),
            stream=True,
            chunk_size=8192,
            parallel_downloads=10,
        )
        mock_move_files.assert_called_once()

    @patch("ubiops_file_sync.downloader._move_downloaded_files")
    @patch("ubiops_file_sync.downloader.config")
    @patch("ubiops_file_sync.downloader.ubiops")
    @patch("ubiops_file_sync.downloader.api_client")
    def test_download_from_bucket_handles_exception(
        self, mock_api_client, mock_ubiops, mock_config, mock_move_files, tmp_path
    ):
        """Test that exceptions during bulk download are logged and re-raised."""
        local_dir = tmp_path / "local"
        local_dir.mkdir()
        mock_config.local_sync_dir = local_dir
        mock_config.project_name = "test-project"
        mock_config.bucket_name = "test-bucket"
        mock_config.bucket_dir = Path("test/dir")
        mock_config.overwrite_newer = False

        mock_ubiops.utils.download_files.side_effect = Exception("Download error")

        with pytest.raises(Exception, match="Download error"):
            download_from_bucket()

        mock_move_files.assert_not_called()

    @patch("ubiops_file_sync.downloader.config")
    def test_download_from_bucket_creates_local_dir(self, mock_config, tmp_path):
        """Test that local directory is created if it doesn't exist."""
        local_dir = tmp_path / "new_local"
        mock_config.local_sync_dir = local_dir
        mock_config.bucket_name = "test-bucket"
        mock_config.bucket_dir = Path("test/dir")
        mock_config.overwrite_newer = True

        with patch("ubiops_file_sync.downloader.list_remote_files") as mock_list:
            mock_list.return_value = []
            download_from_bucket()

        assert local_dir.exists()
        assert local_dir.is_dir()

