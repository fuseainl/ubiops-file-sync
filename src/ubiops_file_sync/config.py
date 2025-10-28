"""Configuration and utility functions for syncing a local folder with a UbiOps bucket."""

from __future__ import annotations

from datetime import datetime
from functools import lru_cache
from os import getenv
from pathlib import Path
from typing import Any, Final

import ubiops  # pyright: ignore[reportMissingTypeStubs]
from pydantic import BaseModel, ConfigDict, field_validator


class SyncConfig(BaseModel):
    """Configuration for syncing a local folder with a UbiOps bucket."""

    model_config = ConfigDict(frozen=True)

    ubiops_api_host: str = "https://api.ubiops.com/v2.1"
    ubiops_api_token: str
    project_name: str
    bucket_name: str
    bucket_dir: str | Path
    local_sync_dir: str | Path
    overwrite_newer: str | bool

    @field_validator("*", mode="before")
    @classmethod
    def not_empty(cls, value: Any) -> Any:  # noqa: ANN401
        """Check that no configuration options have been left empty."""
        if isinstance(value, str) and value.strip() == "":
            msg = "Configuration fields must not be empty strings"
            raise ValueError(msg)
        return value

    @field_validator("ubiops_api_token", mode="before")
    @classmethod
    def is_ubiops_token(cls, value: Any) -> Any:  # noqa: ANN401
        """Format UbiOps token"""
        if isinstance(value, str) and value.strip() != "":
            value = "Token " + value.strip().replace("Token ", "")

        return value

    @field_validator("overwrite_newer", mode="before")
    @classmethod
    def to_bool(cls, value: Any) -> Any:  # noqa: ANN401
        """Attempt to convert string to boolean."""
        if isinstance(value, str):
            return value.lower() in ["true", "1", "t", "y", "yes"]

        return value

    @field_validator("local_sync_dir", mode="before")
    @classmethod
    def is_dir_path(cls, value: Any) -> Any:  # noqa: ANN401
        """Check if path is a directory"""
        if isinstance(value, str):
            value = Path(value)
        if not value.is_dir():
            msg = f"Local path '{value}' is not a directory"
            raise ValueError(msg)

        return value

    @field_validator("bucket_dir", mode="before")
    @classmethod
    def format_bucket_dir(cls, value: Any) -> Any:  # noqa: ANN401
        """Ensure correct format for remote directory"""
        if isinstance(value, str):
            value = Path(value)

        return value


@lru_cache(maxsize=1)
def _build_config() -> SyncConfig:
    return SyncConfig(
        ubiops_api_host=getenv("UBIOPS_API_HOST", ""),
        ubiops_api_token=getenv("UBIOPS_API_TOKEN", ""),
        project_name=getenv("BUCKET_PROJECT_NAME", ""),
        bucket_name=getenv("BUCKET_NAME", ""),
        bucket_dir=getenv("BUCKET_DIR", ""),
        local_sync_dir=getenv("LOCAL_SYNC_DIR", ""),
        overwrite_newer=getenv("OVERWRITE_NEWER_FILES", ""),
    )


config: Final[SyncConfig] = _build_config()


@lru_cache(maxsize=1)
def _build_api_client() -> ubiops.ApiClient:
    """Create a UbiOps API client instance using the given config."""
    configuration = ubiops.Configuration()

    configuration.api_key["Authorization"] = config.ubiops_api_token
    configuration.host = config.ubiops_api_host

    return ubiops.ApiClient(configuration)


api_client: Final[ubiops.ApiClient] = _build_api_client()


@lru_cache(maxsize=1)
def _build_core_api(api_client: ubiops.ApiClient) -> ubiops.CoreApi:
    return ubiops.CoreApi(api_client)


core_api: ubiops.CoreApi = _build_core_api(api_client)


def parse_remote_time(time_str: str) -> float:
    """Parse UbiOps time_created string (UTC in ISO format) to a timestamp (seconds)."""
    # Normalize trailing 'Z' (UTC) to a numeric offset that fromisoformat understands
    s = time_str[:-1] + "+00:00" if time_str.endswith("Z") else time_str
    return datetime.fromisoformat(s).timestamp()
