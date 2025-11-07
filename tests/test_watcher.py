"""Unit tests for watcher module."""

import atexit
import threading
import time
from pathlib import Path
from queue import Queue
from unittest.mock import MagicMock, Mock, patch

import pytest
from watchdog.events import FileClosedEvent

from ubiops_file_sync.watcher import (
    NewFileEventHandler,
    file_queue,
    shutdown,
    watch_local_and_upload,
    worker,
)


class TestNewFileEventHandler:
    """Test NewFileEventHandler class."""

    @patch("ubiops_file_sync.watcher.should_ignore_file")
    @patch("ubiops_file_sync.watcher.file_queue")
    def test_on_closed_ignores_directories(self, mock_queue, mock_should_ignore, tmp_path):
        """Test that directory events are ignored."""
        handler = NewFileEventHandler()
        event = FileClosedEvent(str(tmp_path / "dir"))
        event.is_directory = True

        handler.on_closed(event)

        mock_queue.put.assert_not_called()

    @patch("ubiops_file_sync.watcher.should_ignore_file")
    @patch("ubiops_file_sync.watcher.file_queue")
    def test_on_closed_ignores_ignored_files(self, mock_queue, mock_should_ignore, tmp_path):
        """Test that ignored files are not added to queue."""
        mock_should_ignore.return_value = True
        handler = NewFileEventHandler()
        file_path = tmp_path / "file.txt"
        file_path.write_text("content")
        event = FileClosedEvent(str(file_path))
        event.is_directory = False

        handler.on_closed(event)

        mock_queue.put.assert_not_called()

    @patch("ubiops_file_sync.watcher.should_ignore_file")
    @patch("ubiops_file_sync.watcher.file_queue")
    def test_on_closed_adds_file_to_queue(self, mock_queue, mock_should_ignore, tmp_path):
        """Test that valid files are added to queue."""
        mock_should_ignore.return_value = False
        handler = NewFileEventHandler()
        file_path = tmp_path / "file.txt"
        file_path.write_text("content")
        event = FileClosedEvent(str(file_path))
        event.is_directory = False

        handler.on_closed(event)

        mock_queue.put.assert_called_once()
        call_args = mock_queue.put.call_args[0][0]
        assert call_args == file_path.absolute()


class TestWorker:
    """Test worker function."""

    @patch("ubiops_file_sync.watcher.upload_file")
    @patch("ubiops_file_sync.watcher.file_queue")
    def test_worker_processes_files(self, mock_queue, mock_upload_file, tmp_path):
        """Test that worker processes files from queue."""
        file_path = tmp_path / "test.txt"
        file_path.write_text("content")

        # Mock queue behavior
        mock_queue.get.side_effect = [file_path, None]
        mock_queue.task_done = MagicMock()

        # Call worker directly (it will exit when None is received)
        worker()

        mock_upload_file.assert_called_once_with(local_path=file_path)
        # task_done is called in finally block for each item, plus once in the if block for None
        # So for file_path: once in finally
        # For None: once in if block, once in finally
        # Total: 3 calls
        assert mock_queue.task_done.call_count == 3

    @patch("ubiops_file_sync.watcher.upload_file")
    @patch("ubiops_file_sync.watcher.file_queue")
    def test_worker_handles_exceptions(self, mock_queue, mock_upload_file, tmp_path):
        """Test that worker handles upload exceptions gracefully."""
        file_path = tmp_path / "test.txt"
        file_path.write_text("content")

        mock_upload_file.side_effect = Exception("Upload failed")
        mock_queue.get.side_effect = [file_path, None]
        mock_queue.task_done = MagicMock()

        # Worker should handle exception and continue
        worker()

        mock_upload_file.assert_called_once_with(local_path=file_path)
        # task_done is called in finally block for each item, plus once in the if block for None
        # So for file_path: once in finally (exception doesn't prevent finally)
        # For None: once in if block, once in finally
        # Total: 3 calls
        assert mock_queue.task_done.call_count == 3

    @patch("ubiops_file_sync.watcher.file_queue")
    def test_worker_shuts_down_on_none(self, mock_queue):
        """Test that worker shuts down when None is received."""
        mock_queue.get.side_effect = [None]
        mock_queue.task_done = MagicMock()

        worker()

        # task_done is called once in the if block when None is received,
        # and once in the finally block
        # Total: 2 calls
        assert mock_queue.task_done.call_count == 2


class TestShutdown:
    """Test shutdown function."""

    @patch("ubiops_file_sync.watcher.observer")
    @patch("ubiops_file_sync.watcher.file_queue")
    @patch("ubiops_file_sync.watcher.worker_thread")
    @patch("ubiops_file_sync.watcher.api_client")
    def test_shutdown_stops_observer(
        self, mock_api_client, mock_worker_thread, mock_queue, mock_observer
    ):
        """Test that shutdown stops the observer."""
        mock_observer.is_alive.return_value = True
        mock_worker_thread.is_alive.return_value = False

        shutdown()

        mock_observer.stop.assert_called_once()
        mock_observer.join.assert_called_once_with(timeout=5)

    @patch("ubiops_file_sync.watcher.observer")
    @patch("ubiops_file_sync.watcher.file_queue")
    @patch("ubiops_file_sync.watcher.worker_thread")
    @patch("ubiops_file_sync.watcher.api_client")
    def test_shutdown_signals_worker_thread(
        self, mock_api_client, mock_worker_thread, mock_queue, mock_observer
    ):
        """Test that shutdown signals worker thread to stop."""
        mock_observer.is_alive.return_value = False
        mock_worker_thread.is_alive.return_value = True

        shutdown()

        mock_queue.put.assert_called_once_with(None)
        mock_queue.join.assert_called_once()
        mock_worker_thread.join.assert_called_once_with(timeout=10)

    @patch("ubiops_file_sync.watcher.observer")
    @patch("ubiops_file_sync.watcher.file_queue")
    @patch("ubiops_file_sync.watcher.worker_thread")
    @patch("ubiops_file_sync.watcher.api_client")
    def test_shutdown_closes_api_client(
        self, mock_api_client, mock_worker_thread, mock_queue, mock_observer
    ):
        """Test that shutdown closes the API client."""
        mock_observer.is_alive.return_value = False
        mock_worker_thread.is_alive.return_value = False

        shutdown()

        mock_api_client.close.assert_called_once()


class TestWatchLocalAndUpload:
    """Test watch_local_and_upload function."""

    @patch("ubiops_file_sync.watcher.atexit")
    @patch("ubiops_file_sync.watcher.observer")
    @patch("ubiops_file_sync.watcher.worker_thread")
    @patch("ubiops_file_sync.watcher.config")
    def test_watch_local_and_upload_starts_observer(
        self, mock_config, mock_worker_thread, mock_observer, mock_atexit, tmp_path
    ):
        """Test that watch_local_and_upload starts the observer."""
        local_dir = tmp_path / "local"
        local_dir.mkdir()
        mock_config.local_sync_dir = local_dir

        watch_local_and_upload()

        mock_observer.schedule.assert_called_once()
        mock_observer.start.assert_called_once()
        mock_worker_thread.start.assert_called_once()
        mock_atexit.register.assert_called_once_with(shutdown)

    @patch("ubiops_file_sync.watcher.atexit")
    @patch("ubiops_file_sync.watcher.observer")
    @patch("ubiops_file_sync.watcher.worker_thread")
    @patch("ubiops_file_sync.watcher.config")
    def test_watch_local_and_upload_schedules_recursive_watch(
        self, mock_config, mock_worker_thread, mock_observer, mock_atexit, tmp_path
    ):
        """Test that observer is scheduled with recursive=True."""
        local_dir = tmp_path / "local"
        local_dir.mkdir()
        mock_config.local_sync_dir = local_dir

        watch_local_and_upload()

        call_args = mock_observer.schedule.call_args
        assert call_args[1]["recursive"] is True
        assert call_args[0][1] == str(local_dir)

    @patch("ubiops_file_sync.watcher.atexit")
    @patch("ubiops_file_sync.watcher.observer")
    @patch("ubiops_file_sync.watcher.worker_thread")
    @patch("ubiops_file_sync.watcher.config")
    def test_watch_local_and_upload_registers_shutdown(
        self, mock_config, mock_worker_thread, mock_observer, mock_atexit, tmp_path
    ):
        """Test that shutdown is registered with atexit."""
        local_dir = tmp_path / "local"
        local_dir.mkdir()
        mock_config.local_sync_dir = local_dir

        watch_local_and_upload()

        mock_atexit.register.assert_called_once_with(shutdown)

