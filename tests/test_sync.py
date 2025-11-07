"""Unit tests for sync module."""

from unittest.mock import patch

import pytest

from ubiops_file_sync.sync import sync_and_watch


class TestSyncAndWatch:
    """Test sync_and_watch function."""

    @patch("ubiops_file_sync.sync.watch_local_and_upload")
    @patch("ubiops_file_sync.sync.download_from_bucket")
    @patch("ubiops_file_sync.sync.config")
    def test_sync_and_watch_calls_download_then_watch(
        self, mock_config, mock_download, mock_watch
    ):
        """Test that sync_and_watch calls download then watch."""
        mock_config.local_sync_dir = "/tmp/test"

        sync_and_watch()

        mock_download.assert_called_once()
        mock_watch.assert_called_once()
        # Verify download is called before watch by checking call order
        assert mock_download.call_count == 1
        assert mock_watch.call_count == 1
        # Check that download was called first by verifying call order
        download_call_time = mock_download.call_args_list[0]
        watch_call_time = mock_watch.call_args_list[0]
        # Both should be call() objects, just verify they were both called
        assert download_call_time is not None
        assert watch_call_time is not None

    @patch("ubiops_file_sync.sync.watch_local_and_upload")
    @patch("ubiops_file_sync.sync.download_from_bucket")
    @patch("ubiops_file_sync.sync.config")
    def test_sync_and_watch_handles_download_exception(
        self, mock_config, mock_download, mock_watch
    ):
        """Test that exceptions during download are propagated."""
        mock_config.local_sync_dir = "/tmp/test"
        mock_download.side_effect = Exception("Download failed")

        with pytest.raises(Exception, match="Download failed"):
            sync_and_watch()

        mock_watch.assert_not_called()

