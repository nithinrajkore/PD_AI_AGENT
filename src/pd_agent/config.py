"""User-facing configuration for pd-agent.

Settings are driven by environment variables prefixed with ``PD_AGENT_`` and
optionally loaded from a ``.env`` file in the working directory. CLI flags
in :mod:`pd_agent.cli` can override individual values at invocation time.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

__all__ = ["PDAgentSettings"]


def _default_openlane2_repo() -> Path:
    return Path.home() / "Documents" / "Projects" / "openlane2"


class PDAgentSettings(BaseSettings):
    """Runtime configuration resolved from environment and ``.env``."""

    model_config = SettingsConfigDict(
        env_prefix="PD_AGENT_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openlane2_repo: Path = Field(
        default_factory=_default_openlane2_repo,
        description=(
            "Path to the local clone of the openlane2 repository, used as the "
            "working directory for `nix-shell` invocations when the `openlane` "
            "binary is not directly on PATH."
        ),
    )

    openlane_bin: str = Field(
        default="openlane",
        description="Name of the OpenLane CLI binary to invoke.",
    )
