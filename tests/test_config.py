"""Unit tests for config module."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from ubiops_file_sync.config import (
    SyncConfig,
    _build_api_client,
    _build_config,
    _build_core_api,
    parse_remote_time,
)


class TestSyncConfig:
    """Test SyncConfig class and validators."""

    def test_sync_config_valid(self, tmp_path):
        """Test creating a valid SyncConfig."""
        local_dir = tmp_path / "local"
        local_dir.mkdir()

        config = SyncConfig(
            ubiops_api_token="Token test-token",
            project_name="test-project",
            bucket_name="test-bucket",
            bucket_dir="test/dir",
            local_sync_dir=str(local_dir),
            overwrite_newer=True,
            ignored_extensions=["pyc", "tmp"],
        )

        assert config.ubiops_api_token == "Token test-token"
        assert config.project_name == "test-project"
        assert config.bucket_name == "test-bucket"
        assert config.bucket_dir == Path("test/dir")
        assert config.local_sync_dir == local_dir
        assert config.overwrite_newer is True
        assert config.ignored_extensions == ["pyc", "tmp"]

    def test_sync_config_defaults(self, tmp_path):
        """Test SyncConfig with default values."""
        local_dir = tmp_path / "local"
        local_dir.mkdir()

        config = SyncConfig(
            ubiops_api_token="Token test-token",
            project_name="test-project",
            bucket_name="test-bucket",
            bucket_dir="test/dir",
            local_sync_dir=str(local_dir),
            overwrite_newer=False,
            ignored_extensions=[],
        )

        assert config.ubiops_api_host == "https://api.ubiops.com/v2.1"

    def test_not_empty_validator_rejects_empty_string(self, tmp_path):
        """Test that empty strings are rejected."""
        local_dir = tmp_path / "local"
        local_dir.mkdir()

        with pytest.raises(ValidationError):
            SyncConfig(
                ubiops_api_token="",
                project_name="test-project",
                bucket_name="test-bucket",
                bucket_dir="test/dir",
                local_sync_dir=str(local_dir),
                overwrite_newer=False,
                ignored_extensions=[],
            )

    def test_not_empty_validator_rejects_whitespace(self, tmp_path):
        """Test that whitespace-only strings are rejected."""
        local_dir = tmp_path / "local"
        local_dir.mkdir()

        with pytest.raises(ValidationError):
            SyncConfig(
                ubiops_api_token="   ",
                project_name="test-project",
                bucket_name="test-bucket",
                bucket_dir="test/dir",
                local_sync_dir=str(local_dir),
                overwrite_newer=False,
                ignored_extensions=[],
            )

    def test_ubiops_token_validator_adds_token_prefix(self, tmp_path):
        """Test that token prefix is added if missing."""
        local_dir = tmp_path / "local"
        local_dir.mkdir()

        config = SyncConfig(
            ubiops_api_token="test-token",
            project_name="test-project",
            bucket_name="test-bucket",
            bucket_dir="test/dir",
            local_sync_dir=str(local_dir),
            overwrite_newer=False,
            ignored_extensions=[],
        )

        assert config.ubiops_api_token == "Token test-token"

    def test_ubiops_token_validator_preserves_existing_prefix(self, tmp_path):
        """Test that existing token prefix is preserved."""
        local_dir = tmp_path / "local"
        local_dir.mkdir()

        config = SyncConfig(
            ubiops_api_token="Token test-token",
            project_name="test-project",
            bucket_name="test-bucket",
            bucket_dir="test/dir",
            local_sync_dir=str(local_dir),
            overwrite_newer=False,
            ignored_extensions=[],
        )

        assert config.ubiops_api_token == "Token test-token"

    def test_ubiops_token_validator_strips_whitespace(self, tmp_path):
        """Test that token whitespace is stripped."""
        local_dir = tmp_path / "local"
        local_dir.mkdir()

        config = SyncConfig(
            ubiops_api_token="  Token test-token  ",
            project_name="test-project",
            bucket_name="test-bucket",
            bucket_dir="test/dir",
            local_sync_dir=str(local_dir),
            overwrite_newer=False,
            ignored_extensions=[],
        )

        assert config.ubiops_api_token == "Token test-token"

    def test_to_bool_validator_string_true(self, tmp_path):
        """Test boolean conversion from string 'true'."""
        local_dir = tmp_path / "local"
        local_dir.mkdir()

        config = SyncConfig(
            ubiops_api_token="Token test-token",
            project_name="test-project",
            bucket_name="test-bucket",
            bucket_dir="test/dir",
            local_sync_dir=str(local_dir),
            overwrite_newer="true",
            ignored_extensions=[],
        )

        assert config.overwrite_newer is True

    def test_to_bool_validator_string_false(self, tmp_path):
        """Test boolean conversion from string 'false'."""
        local_dir = tmp_path / "local"
        local_dir.mkdir()

        config = SyncConfig(
            ubiops_api_token="Token test-token",
            project_name="test-project",
            bucket_name="test-bucket",
            bucket_dir="test/dir",
            local_sync_dir=str(local_dir),
            overwrite_newer="false",
            ignored_extensions=[],
        )

        assert config.overwrite_newer is False

    def test_to_bool_validator_string_yes(self, tmp_path):
        """Test boolean conversion from string 'yes'."""
        local_dir = tmp_path / "local"
        local_dir.mkdir()

        config = SyncConfig(
            ubiops_api_token="Token test-token",
            project_name="test-project",
            bucket_name="test-bucket",
            bucket_dir="test/dir",
            local_sync_dir=str(local_dir),
            overwrite_newer="yes",
            ignored_extensions=[],
        )

        assert config.overwrite_newer is True

    def test_to_bool_validator_string_1(self, tmp_path):
        """Test boolean conversion from string '1'."""
        local_dir = tmp_path / "local"
        local_dir.mkdir()

        config = SyncConfig(
            ubiops_api_token="Token test-token",
            project_name="test-project",
            bucket_name="test-bucket",
            bucket_dir="test/dir",
            local_sync_dir=str(local_dir),
            overwrite_newer="1",
            ignored_extensions=[],
        )

        assert config.overwrite_newer is True

    def test_to_bool_validator_preserves_bool(self, tmp_path):
        """Test that boolean values are preserved."""
        local_dir = tmp_path / "local"
        local_dir.mkdir()

        config = SyncConfig(
            ubiops_api_token="Token test-token",
            project_name="test-project",
            bucket_name="test-bucket",
            bucket_dir="test/dir",
            local_sync_dir=str(local_dir),
            overwrite_newer=True,
            ignored_extensions=[],
        )

        assert config.overwrite_newer is True

    def test_is_dir_path_validator_creates_directory(self, tmp_path):
        """Test that directory is created if it doesn't exist."""
        local_dir = tmp_path / "new_dir"

        config = SyncConfig(
            ubiops_api_token="Token test-token",
            project_name="test-project",
            bucket_name="test-bucket",
            bucket_dir="test/dir",
            local_sync_dir=str(local_dir),
            overwrite_newer=False,
            ignored_extensions=[],
        )

        assert local_dir.exists()
        assert local_dir.is_dir()

    def test_is_dir_path_validator_rejects_file(self, tmp_path):
        """Test that file paths are rejected."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")

        # The validator tries to mkdir first, which will raise FileExistsError
        # Then it checks if it's a directory and raises ValidationError
        with pytest.raises((ValidationError, FileExistsError)):
            SyncConfig(
                ubiops_api_token="Token test-token",
                project_name="test-project",
                bucket_name="test-bucket",
                bucket_dir="test/dir",
                local_sync_dir=str(test_file),
                overwrite_newer=False,
                ignored_extensions=[],
            )

    def test_is_dir_path_validator_converts_string_to_path(self, tmp_path):
        """Test that string paths are converted to Path objects."""
        local_dir = tmp_path / "local"
        local_dir.mkdir()

        config = SyncConfig(
            ubiops_api_token="Token test-token",
            project_name="test-project",
            bucket_name="test-bucket",
            bucket_dir="test/dir",
            local_sync_dir=str(local_dir),
            overwrite_newer=False,
            ignored_extensions=[],
        )

        assert isinstance(config.local_sync_dir, Path)

    def test_format_bucket_dir_validator_converts_string(self, tmp_path):
        """Test that bucket_dir string is converted to Path."""
        local_dir = tmp_path / "local"
        local_dir.mkdir()

        config = SyncConfig(
            ubiops_api_token="Token test-token",
            project_name="test-project",
            bucket_name="test-bucket",
            bucket_dir="test/dir",
            local_sync_dir=str(local_dir),
            overwrite_newer=False,
            ignored_extensions=[],
        )

        assert isinstance(config.bucket_dir, Path)
        assert config.bucket_dir == Path("test/dir")

    def test_parse_ignored_extensions_empty_string(self, tmp_path):
        """Test parsing empty string for ignored extensions."""
        local_dir = tmp_path / "local"
        local_dir.mkdir()

        config = SyncConfig(
            ubiops_api_token="Token test-token",
            project_name="test-project",
            bucket_name="test-bucket",
            bucket_dir="test/dir",
            local_sync_dir=str(local_dir),
            overwrite_newer=False,
            ignored_extensions="",
        )

        assert config.ignored_extensions == []

    def test_parse_ignored_extensions_comma_separated(self, tmp_path):
        """Test parsing comma-separated extensions."""
        local_dir = tmp_path / "local"
        local_dir.mkdir()

        config = SyncConfig(
            ubiops_api_token="Token test-token",
            project_name="test-project",
            bucket_name="test-bucket",
            bucket_dir="test/dir",
            local_sync_dir=str(local_dir),
            overwrite_newer=False,
            ignored_extensions="pyc,tmp,log",
        )

        assert config.ignored_extensions == ["pyc", "tmp", "log"]

    def test_parse_ignored_extensions_with_dots(self, tmp_path):
        """Test parsing extensions with dots."""
        local_dir = tmp_path / "local"
        local_dir.mkdir()

        config = SyncConfig(
            ubiops_api_token="Token test-token",
            project_name="test-project",
            bucket_name="test-bucket",
            bucket_dir="test/dir",
            local_sync_dir=str(local_dir),
            overwrite_newer=False,
            ignored_extensions=".pyc,.tmp",
        )

        assert config.ignored_extensions == ["pyc", "tmp"]

    def test_parse_ignored_extensions_case_insensitive(self, tmp_path):
        """Test that extensions are normalized to lowercase."""
        local_dir = tmp_path / "local"
        local_dir.mkdir()

        config = SyncConfig(
            ubiops_api_token="Token test-token",
            project_name="test-project",
            bucket_name="test-bucket",
            bucket_dir="test/dir",
            local_sync_dir=str(local_dir),
            overwrite_newer=False,
            ignored_extensions="PYC,TMP",
        )

        assert config.ignored_extensions == ["pyc", "tmp"]

    def test_parse_ignored_extensions_list(self, tmp_path):
        """Test parsing list of extensions."""
        local_dir = tmp_path / "local"
        local_dir.mkdir()

        config = SyncConfig(
            ubiops_api_token="Token test-token",
            project_name="test-project",
            bucket_name="test-bucket",
            bucket_dir="test/dir",
            local_sync_dir=str(local_dir),
            overwrite_newer=False,
            ignored_extensions=["pyc", "tmp"],
        )

        assert config.ignored_extensions == ["pyc", "tmp"]

    def test_parse_ignored_extensions_with_whitespace(self, tmp_path):
        """Test parsing extensions with whitespace."""
        local_dir = tmp_path / "local"
        local_dir.mkdir()

        config = SyncConfig(
            ubiops_api_token="Token test-token",
            project_name="test-project",
            bucket_name="test-bucket",
            bucket_dir="test/dir",
            local_sync_dir=str(local_dir),
            overwrite_newer=False,
            ignored_extensions=" pyc , tmp , log ",
        )

        assert config.ignored_extensions == ["pyc", "tmp", "log"]

    def test_config_is_frozen(self, tmp_path):
        """Test that config is frozen (immutable)."""
        local_dir = tmp_path / "local"
        local_dir.mkdir()

        config = SyncConfig(
            ubiops_api_token="Token test-token",
            project_name="test-project",
            bucket_name="test-bucket",
            bucket_dir="test/dir",
            local_sync_dir=str(local_dir),
            overwrite_newer=False,
            ignored_extensions=[],
        )

        with pytest.raises(Exception):  # Pydantic validation error
            config.project_name = "new-project"


class TestBuildConfig:
    """Test _build_config function."""

    def test_build_config_from_env(self, tmp_path, monkeypatch):
        """Test building config from environment variables."""
        # Set all environment variables
        local_dir = tmp_path / "local"
        local_dir.mkdir()
        monkeypatch.setenv("UBIOPS_API_HOST", "https://api.test.com")
        monkeypatch.setenv("UBIOPS_API_TOKEN", "test-token")
        monkeypatch.setenv("BUCKET_PROJECT_NAME", "test-project")
        monkeypatch.setenv("BUCKET_NAME", "test-bucket")
        monkeypatch.setenv("BUCKET_DIR", "test/dir")
        monkeypatch.setenv("LOCAL_SYNC_DIR", str(local_dir))
        monkeypatch.setenv("OVERWRITE_NEWER_FILES", "true")
        monkeypatch.setenv("IGNORED_FILE_EXTENSIONS", "pyc,tmp")

        # Clear cache to force rebuild
        _build_config.cache_clear()

        config = _build_config()

        assert config.ubiops_api_host == "https://api.test.com"
        assert config.ubiops_api_token == "Token test-token"
        assert config.project_name == "test-project"
        assert config.bucket_name == "test-bucket"
        assert config.bucket_dir == Path("test/dir")
        assert config.local_sync_dir == local_dir
        assert config.overwrite_newer is True
        assert config.ignored_extensions == ["pyc", "tmp"]

    def test_build_config_missing_env_vars(self, tmp_path, monkeypatch):
        """Test that missing environment variables raise validation error."""
        # Clear all environment variables
        monkeypatch.delenv("UBIOPS_API_HOST", raising=False)
        monkeypatch.delenv("UBIOPS_API_TOKEN", raising=False)
        monkeypatch.delenv("BUCKET_PROJECT_NAME", raising=False)
        monkeypatch.delenv("BUCKET_NAME", raising=False)
        monkeypatch.delenv("BUCKET_DIR", raising=False)
        monkeypatch.delenv("LOCAL_SYNC_DIR", raising=False)
        monkeypatch.delenv("OVERWRITE_NEWER_FILES", raising=False)
        monkeypatch.delenv("IGNORED_FILE_EXTENSIONS", raising=False)

        # Clear cache to force rebuild
        _build_config.cache_clear()

        with pytest.raises(ValidationError):
            _build_config()


class TestBuildApiClient:
    """Test _build_api_client function."""

    @patch("ubiops_file_sync.config.ubiops")
    @patch("ubiops_file_sync.config.config")
    def test_build_api_client(self, mock_config, mock_ubiops):
        """Test building API client."""
        mock_config.ubiops_api_token = "Token test-token"
        mock_config.ubiops_api_host = "https://api.test.com"

        mock_configuration = MagicMock()
        mock_configuration.api_key = {}
        mock_ubiops.Configuration.return_value = mock_configuration
        mock_client = MagicMock()
        mock_ubiops.ApiClient.return_value = mock_client

        # Clear cache to force rebuild
        _build_api_client.cache_clear()

        client = _build_api_client()

        mock_ubiops.Configuration.assert_called_once()
        mock_ubiops.ApiClient.assert_called_once_with(mock_configuration)
        assert mock_configuration.api_key["Authorization"] == "Token test-token"
        assert mock_configuration.host == "https://api.test.com"
        assert client == mock_client


class TestBuildCoreApi:
    """Test _build_core_api function."""

    @patch("ubiops_file_sync.config.ubiops")
    def test_build_core_api(self, mock_ubiops):
        """Test building CoreApi."""
        mock_api_client = MagicMock()
        mock_core_api = MagicMock()
        mock_ubiops.CoreApi.return_value = mock_core_api

        # Clear cache to force rebuild
        _build_core_api.cache_clear()

        core_api = _build_core_api(mock_api_client)

        mock_ubiops.CoreApi.assert_called_once_with(mock_api_client)
        assert core_api == mock_core_api


class TestParseRemoteTime:
    """Test parse_remote_time function."""

    def test_parse_remote_time_with_z(self):
        """Test parsing time string with Z suffix."""
        time_str = "2024-01-15T10:30:00Z"
        timestamp = parse_remote_time(time_str)

        assert isinstance(timestamp, float)
        assert timestamp > 0

    def test_parse_remote_time_without_z(self):
        """Test parsing time string without Z suffix."""
        time_str = "2024-01-15T10:30:00+00:00"
        timestamp = parse_remote_time(time_str)

        assert isinstance(timestamp, float)
        assert timestamp > 0

    def test_parse_remote_time_with_offset(self):
        """Test parsing time string with timezone offset."""
        time_str = "2024-01-15T10:30:00+02:00"
        timestamp = parse_remote_time(time_str)

        assert isinstance(timestamp, float)
        assert timestamp > 0

    def test_parse_remote_time_iso_format(self):
        """Test parsing ISO format time string."""
        time_str = "2024-01-15T10:30:00.123456Z"
        timestamp = parse_remote_time(time_str)

        assert isinstance(timestamp, float)
        assert timestamp > 0

